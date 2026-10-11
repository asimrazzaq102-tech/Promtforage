"""
PromptForge Face Swap Server — runs on your own PC (NVIDIA GPU).
Uses InsightFace (buffalo_l) for face detection + inswapper_128.onnx for swapping.

Run:  uvicorn server:app --host 127.0.0.1 --port 8000
Then expose with Cloudflare Tunnel and paste the public URL into PromptForge.
"""
import os
import uuid
import shutil
import subprocess
import smtplib
import secrets
import time
from email.mime.text import MIMEText

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import imageio_ffmpeg

API_KEY = os.environ.get("PF_KEY", "promptforge123")  # master key (owner only)
# Email settings for one-time access codes (all stay on YOUR pc, never in the repo)
GMAIL_USER = os.environ.get("FS_GMAIL_USER", "")       # your gmail address
GMAIL_PASS = os.environ.get("FS_GMAIL_APP_PASS", "")   # gmail "app password"
OWNER_EMAIL = os.environ.get("FS_OWNER_EMAIL", GMAIL_USER)  # where codes are sent

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE, "models", "inswapper_128.onnx")
WORK_ROOT = os.path.join(BASE, "work")
os.makedirs(WORK_ROOT, exist_ok=True)

CODE_TTL = 10 * 60      # access codes valid 10 minutes, single use
TOKEN_TTL = 30 * 86400  # approved devices stay unlocked 30 days
_codes = {}    # code -> expiry timestamp
_tokens = {}   # token -> expiry timestamp
_last_req = 0  # simple rate limit for code requests

app = FastAPI(title="PromptForge FaceSwap")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # the static site calls from github.io
    allow_methods=["*"],
    allow_headers=["*"],
)

_analyzer = None
_swapper = None


def load_models():
    global _analyzer, _swapper
    if _analyzer is not None:
        return
    print("Loading face detection model (buffalo_l)...")
    from insightface.app import FaceAnalysis
    _analyzer = FaceAnalysis(name="buffalo_l")
    # ctx_id=0 -> GPU, ctx_id=-1 -> CPU
    try:
        _analyzer.prepare(ctx_id=0, det_size=(640, 640))
        print("Detector on GPU.")
    except Exception as e:
        print("GPU detector failed, using CPU:", e)
        _analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    print("Loading face swap model...")
    from insightface.model_zoo import get_model
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(
            f"Swap model not found at {MODEL_PATH}. "
            "Download inswapper_128.onnx into the models/ folder first."
        )
    try:
        _swapper = get_model(MODEL_PATH, providers=["CUDAExecutionProvider"])
        print("Swapper on GPU.")
    except Exception as e:
        print("GPU swapper failed, using CPU:", e)
        _swapper = get_model(MODEL_PATH, providers=["CPUExecutionProvider"])


def biggest_face(faces):
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))


@app.get("/health")
def health():
    return {"ok": True, "gpu_model": os.path.exists(MODEL_PATH)}


@app.get("/verify")
def verify(key: str = Header(None, alias="X-API-Key")):
    if key != API_KEY and not _token_ok(key):
        raise HTTPException(status_code=401, detail="wrong password")
    return {"ok": True}


def _token_ok(tok):
    if not tok or tok not in _tokens:
        return False
    if _tokens[tok] < time.time():
        del _tokens[tok]
        return False
    return True


def _send_code_email(code):
    if not GMAIL_USER or not GMAIL_PASS:
        raise RuntimeError("Email not configured: set FS_GMAIL_USER and FS_GMAIL_APP_PASS")
    msg = MIMEText(
        f"Someone requested Face Swap access on your PromptForge server.\n\n"
        f"Access code: {code}\n\n"
        f"This code is valid for 10 minutes and can be used once. "
        f"Only share it with someone you trust."
    )
    msg["Subject"] = f"PromptForge Face Swap access code: {code}"
    msg["From"] = GMAIL_USER
    msg["To"] = OWNER_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_PASS)
        s.send_message(msg)


@app.post("/request-code")
def request_code():
    global _last_req
    now = time.time()
    if now - _last_req < 60:
        raise HTTPException(status_code=429, detail="wait a minute before requesting again")
    _last_req = now
    code = f"{secrets.randbelow(900000) + 100000}"  # 6 digits
    _codes[code] = now + CODE_TTL
    try:
        _send_code_email(code)
    except Exception as e:
        _codes.pop(code, None)
        raise HTTPException(status_code=500, detail=f"could not send email: {e}"[:200])
    return {"ok": True, "msg": "Code sent to the owner's email. Ask him for it."}


@app.post("/verify-code")
def verify_code(payload: dict):
    code = str(payload.get("code", "")).strip()
    now = time.time()
    # purge expired
    for c in [c for c, exp in _codes.items() if exp < now]:
        _codes.pop(c, None)
    if code not in _codes:
        raise HTTPException(status_code=401, detail="wrong or expired code")
    _codes.pop(code, None)  # single use
    token = secrets.token_hex(16)
    _tokens[token] = now + TOKEN_TTL
    return {"ok": True, "token": token}


@app.post("/swap")
async def swap(
    background: BackgroundTasks,
    video: UploadFile = File(...),
    face: UploadFile = File(...),
    key: str = Header(None, alias="X-API-Key"),
):
    if key != API_KEY and not _token_ok(key):
        raise HTTPException(status_code=401, detail="not authorized")
    load_models()

    uid = uuid.uuid4().hex
    work = os.path.join(WORK_ROOT, uid)
    os.makedirs(work)
    try:
        vpath = os.path.join(work, "in.mp4")
        fpath = os.path.join(work, "face.jpg")
        with open(vpath, "wb") as f:
            shutil.copyfileobj(video.file, f)
        with open(fpath, "wb") as f:
            shutil.copyfileobj(face.file, f)

        # --- source face ---
        simg = cv2.imread(fpath)
        if simg is None:
            raise HTTPException(status_code=400, detail="could not read face photo")
        sfaces = _analyzer.get(simg)
        if not sfaces:
            raise HTTPException(status_code=400, detail="no face found in photo")
        sface = biggest_face(sfaces)

        # --- process video frame by frame ---
        cap = cv2.VideoCapture(vpath)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="could not read video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        print(f"Processing {n_frames} frames ({w}x{h} @ {fps:.1f}fps)...")

        swapped_path = os.path.join(work, "swapped.mp4")
        vw = cv2.VideoWriter(
            swapped_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
        )
        done = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            faces = _analyzer.get(frame)
            if faces:
                tface = biggest_face(faces)
                try:
                    frame = _swapper.get(frame, tface, sface, paste_back=True)
                except Exception as e:
                    print("swap failed on a frame:", e)
            vw.write(frame)
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{n_frames} frames")
        cap.release()
        vw.release()

        # --- mux original audio back ---
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        final_path = os.path.join(work, "final.mp4")
        cmd = [
            ffmpeg, "-y",
            "-i", swapped_path,
            "-i", vpath,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-c:a", "aac",
            "-map", "0:v:0", "-map", "1:a:0?",
            "-shortest",
            final_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print("Done ->", final_path)
        background.add_task(shutil.rmtree, work, True)  # auto-delete temp files
        return FileResponse(final_path, media_type="video/mp4", filename="faceswap.mp4")
    except HTTPException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e)[:300])
