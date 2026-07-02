import http.server
import json
import subprocess
import sys
import time
import socket
import threading
import urllib.request
import urllib.error
from pathlib import Path

import tkinter as tk
from tkinter import messagebox
import webview

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

PORT       = 8501
COUNT_PORT = 8502
TITLE      = "프로젝트 대화 로그방"


# ── Win32 작업표시줄 깜빡임 ─────────────────────
def flash_taskbar(hwnd):
    FLASHW_ALL       = 0x00000003
    FLASHW_TIMERNOFG = 0x0000000C

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize",    ctypes.c_uint),
            ("hwnd",      ctypes.wintypes.HWND),
            ("dwFlags",   ctypes.c_uint),
            ("uCount",    ctypes.c_uint),
            ("dwTimeout", ctypes.c_uint),
        ]

    fi = FLASHWINFO(
        cbSize=ctypes.sizeof(FLASHWINFO),
        hwnd=hwnd,
        dwFlags=FLASHW_ALL | FLASHW_TIMERNOFG,
        uCount=0,
        dwTimeout=0,
    )
    ctypes.windll.user32.FlashWindowEx(ctypes.byref(fi))


def is_foreground(hwnd):
    return ctypes.windll.user32.GetForegroundWindow() == hwnd


def find_hwnd(title, retries=10):
    for _ in range(retries):
        hwnd = ctypes.windll.user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
        time.sleep(0.5)
    return 0


# ── 메시지 카운트 HTTP 서버 (클라이언트용) ─────
def start_count_server(chat_dir: Path):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                data = json.loads((chat_dir / "chat_messages.json").read_text(encoding="utf-8"))
                count = len([m for m in data if isinstance(m, dict)])
            except Exception:
                count = 0
            body = str(count).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    try:
        srv = http.server.HTTPServer(("0.0.0.0", COUNT_PORT), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    except OSError:
        pass  # 포트 사용 중이면 그냥 skip


# ── 메시지 폴링 → 작업표시줄 깜빡임 ───────────
def watch_and_flash(chat_dir: Path, hwnd_ref: list):
    msg_file = chat_dir / "chat_messages.json"
    last_count = -1
    while True:
        try:
            if msg_file.exists():
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                count = len([m for m in data if isinstance(m, dict)])
            else:
                count = 0
        except Exception:
            count = 0

        if last_count == -1:
            last_count = count
        elif count > last_count:
            last_count = count
            hwnd = hwnd_ref[0]
            if hwnd and not is_foreground(hwnd):
                flash_taskbar(hwnd)
        else:
            last_count = count

        time.sleep(2)


# ── 유틸 ────────────────────────────────────────
def get_base_dir():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def find_streamlit_cmd():
    import shutil
    st = shutil.which("streamlit")
    if st:
        return [st]
    for py in ["python", "python3"]:
        try:
            r = subprocess.run([py, "-m", "streamlit", "--version"],
                               capture_output=True, timeout=5)
            if r.returncode == 0:
                return [py, "-m", "streamlit"]
        except Exception:
            continue
    return None


def start_streamlit(chat_py: Path):
    base_cmd = find_streamlit_cmd()
    if base_cmd is None:
        return None, "Streamlit을 찾을 수 없습니다.\nPython과 Streamlit이 설치되어 있는지 확인하세요."

    cmd = base_cmd + [
        "run", str(chat_py),
        f"--server.port={PORT}",
        "--server.headless=true",
        "--server.address=0.0.0.0",
        "--browser.gatherUsageStats=false",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    proc = subprocess.Popen(
        cmd, creationflags=flags,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=str(chat_py.parent),
    )
    return proc, None


def wait_for_server(port, timeout=30):
    url = f"http://localhost:{port}/_stcore/health"
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


# ── 메인 ────────────────────────────────────────
def main():
    base_dir = get_base_dir()
    chat_py  = base_dir / "chat.py"

    if not chat_py.exists():
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("오류", f"chat.py를 찾을 수 없습니다.\n경로: {chat_py}")
        root.destroy(); return

    proc, err = start_streamlit(chat_py)
    if err:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("오류", err)
        root.destroy(); return

    if not wait_for_server(PORT, 30):
        proc.terminate()
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("오류", "서버 시작 시간 초과 (30초)")
        root.destroy(); return

    local_ip  = get_local_ip()
    win_title = f"{TITLE}  ─  서버 IP: {local_ip}:{PORT}"

    start_count_server(chat_py.parent)

    hwnd_ref = [0]

    win = webview.create_window(
        win_title,
        url=f"http://localhost:{PORT}",
        width=1280,
        height=800,
        min_size=(800, 600),
    )

    def on_start():
        if sys.platform == "win32":
            hwnd_ref[0] = find_hwnd(win_title)
        threading.Thread(
            target=watch_and_flash,
            args=(chat_py.parent, hwnd_ref),
            daemon=True,
        ).start()

    webview.start(func=on_start)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    main()
