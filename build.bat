@echo off
chcp 65001 > nul
echo.
echo  ============================================
echo   채팅 앱 빌드 (server.exe / client.exe)
echo  ============================================
echo.

where pyinstaller > nul 2>&1
if %errorlevel% neq 0 (
    echo  [오류] PyInstaller가 설치되어 있지 않습니다.
    echo  아래 명령어를 먼저 실행하세요:
    echo    pip install pyinstaller pywebview
    echo.
    pause
    exit /b 1
)

echo  [1/2] server.exe 빌드 중...
pyinstaller --onefile --noconsole ^
  --name server ^
  --collect-all pywebview ^
  --hidden-import tkinter ^
  --hidden-import tkinter.messagebox ^
  server_launcher.py
if %errorlevel% neq 0 goto error

echo.
echo  [2/2] client.exe 빌드 중...
pyinstaller --onefile --noconsole ^
  --name client ^
  --collect-all pywebview ^
  --hidden-import tkinter ^
  --hidden-import tkinter.simpledialog ^
  --hidden-import tkinter.messagebox ^
  client_launcher.py
if %errorlevel% neq 0 goto error

echo.
echo  ============================================
echo   빌드 완료!
echo.
echo   [서버 배포 파일]  dist\ 폴더에서
echo     server.exe  +  chat.py  를 함께 배포
echo.
echo   [클라이언트 배포 파일]
echo     client.exe  단독 배포 (Python 불필요)
echo  ============================================
echo.
pause
exit /b 0

:error
echo.
echo  [오류] 빌드 실패. 위 오류 메시지를 확인하세요.
echo.
pause
exit /b 1
