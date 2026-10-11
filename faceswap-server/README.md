# PromptForge Face Swap Server

Runs on **your own PC** (NVIDIA GPU). Your PromptForge site sends a video + a face
photo here, the server swaps the face, and sends the video back.

## One-time setup (Windows)

1. Install **Python 3.10 or 3.11** from python.org
   - ✅ Tick **"Add python.exe to PATH"** during install
2. Install **CUDA** for your GPU (needed for `onnxruntime-gpu`):
   - Easiest: install the NVIDIA CUDA Toolkit 12.x from nvidia.com
   - Or skip — the server falls back to CPU (much slower)
3. Double-click **`setup.bat`** — installs everything + downloads the face-swap
   model (~550 MB). First server start also downloads the face detector (~300 MB).
4. (Optional but recommended) Change the API key:
   - Edit `start.bat` → `set PF_KEY=something-secret`
   - Use the same key in the PromptForge site's Face Swap section

## Every time you want to use face swap

1. Double-click **`start.bat`** — server runs at `http://127.0.0.1:8000`
   (keep the window open)
2. Expose it to the internet with **Cloudflare Tunnel** (free):
   - Install `cloudflared` from cloudflare.com
   - Run: `cloudflared tunnel --url http://127.0.0.1:8000`
   - Copy the `https://....trycloudflare.com` URL it prints
3. On the PromptForge site → **Face Swap** section → paste that URL + your API key
4. Upload video + face photo → **Swap** → download the result

> The `trycloudflare.com` URL changes every time you restart the tunnel.
> For a permanent URL, create a free Cloudflare account and set up a named tunnel.

## Access control — email codes (no shareable password)

There is **no fixed password** — so nobody can forward it:

1. Visitor taps **📩 Request access code** on the site
2. Your server emails a **6-digit code to YOUR email** (valid 10 min, one-time use)
3. You read the email and share the code (e.g. WhatsApp) only with people you trust
4. They enter it → unlocked on their device for **30 days**

To enable emailing, edit `start.bat` with your Gmail + an **app password**:
`Google Account → Security → 2-Step Verification ON → App passwords → Mail`.
`PF_KEY` remains as your personal master key (owner only, never share it).

- `POST /swap` with multipart `video` (mp4) + `face` (jpg/png) and header
  `X-API-Key: <your key>` → returns the swapped mp4 (original audio kept)
- Swaps the **largest face** in each frame (InsightFace `buffalo_l` detection +
  `inswapper_128` model)
- `GET /health` → `{"ok": true}` when the server is up

## Notes

- First run downloads models — needs internet
- A 10-second clip takes ~1–3 minutes on an RTX 3060
- Keep videos short (under 30s) for reasonable wait times
- This runs fully on your PC — no video ever goes to a third-party server
