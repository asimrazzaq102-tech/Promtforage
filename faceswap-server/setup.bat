@echo off
REM ============================================================
REM  PromptForge Face Swap — one-time setup (Windows, NVIDIA GPU)
REM  Run this file by double-clicking it.
REM ============================================================
echo.
echo  [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo  ERROR: Python not found. Install Python 3.10 or 3.11 from python.org
  echo  IMPORTANT: tick "Add python.exe to PATH" during install, then re-run this.
  pause
  exit /b 1
)

echo.
echo  [2/4] Installing packages (takes a few minutes)...
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" insightface onnxruntime-gpu opencv-python-headless imageio-ffmpeg python-multipart

echo.
echo  [3/4] Downloading face-swap model (~550 MB, one time)...
if not exist models mkdir models
if not exist models\inswapper_128.onnx (
  curl -L -o models\inswapper_128.onnx https://github.com/facefusion/facefusion-assets/releases/download/models/inswapper_128.onnx
) else (
  echo  Model already downloaded, skipping.
)

echo.
echo  [4/4] Done!
echo.
echo  To START the server, double-click  start.bat
echo  (First run also downloads the face detector ~300 MB automatically.)
echo.
pause
