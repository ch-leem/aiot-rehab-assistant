@echo off
setlocal
title WebRTC Signaling Server Auto-Restart

:loop
py -3.14 webrtc_signaling_server.py
timeout /t 1 >nul
goto loop
