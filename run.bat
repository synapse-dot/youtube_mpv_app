@echo off
setlocal

where conda >nul 2>nul
if %errorlevel%==0 (
  call conda env list | findstr /I "youtube_mpv" >nul
  if errorlevel 1 (
    call conda create -y -n youtube_mpv python=3.11
  )
  call conda activate youtube_mpv
  python -m pip install -r requirements.txt
  python main.py
  goto :eof
)

if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python main.py
