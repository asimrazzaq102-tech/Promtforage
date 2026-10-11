@echo off
REM Start the PromptForge face swap server on this PC.
REM Keep this window open while you use face swap on the site.
REM
REM Fill in your Gmail + app password so the server can email you access codes:
REM   1. Google Account -> Security -> 2-Step Verification ON
REM   2. Security -> App passwords -> create one for "Mail" -> paste below
set PF_KEY=promptforge123
set FS_GMAIL_USER=youremail@gmail.com
set FS_GMAIL_APP_PASS=xxxx-xxxx-xxxx-xxxx
set FS_OWNER_EMAIL=youremail@gmail.com
uvicorn server:app --host 127.0.0.1 --port 8000
pause
