import subprocess
import sys
import time
import socket
import urllib.request
import urllib.error
from pathlib import Path

import tkinter as tk
from tkinter import messagebox
import webview

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

PORT = 8501
TITLE = "프로젝트 대화 로그방"

NOTIFY_JS = """
(function() {
    let lastCount = -1;
    window.addEventListener('message', function(e) {
        if (!e.data || e.data.type !== 'chatMsgCount') return;
        const count = parseInt(e.data.count) || 0;
        if (lastCount === -1) { lastCount = count; return; }
        if (count > lastCount && !document.hasFocus()) {
            try { window.pywebview.api.on_new_message(); } catch(ex) {}
        }
        lastCount = count;
    });
})();
"""


def flash_taskbar(hwnd):
    FLASHW_ALL = 0x00000003
    FLASHW_TIMERNOFG = 0x0000000C

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_uint),
            ("hwnd",   ctypes.wintypes.HWND),
            ("dwFlags",ctypes.c_uint),
            ("uCount", ctypes.c_uint),
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


class Api:
    def __init__(self):
        self._hwnd = None

    def set_hwnd(self, hwnd):
        self._hwnd = hwnd

    def on_new_message(self):
        if self._hwnd and sys.platform == "win32":
            flash_taskbar(self._hwnd)


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


def start_streamlit(chat_py):
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

    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen(
        cmd,
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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


def main():
    base_dir = get_base_dir()
    chat_py = base_dir / "chat.py"

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

    local_ip = get_local_ip()
    win_title = f"{TITLE}  ─  서버 IP: {local_ip}:{PORT}"

    api = Api()
    win = webview.create_window(
        win_title,
        url=f"http://localhost:{PORT}",
        width=1280,
        height=800,
        min_size=(800, 600),
        js_api=api,
    )

    def on_loaded():
        win.evaluate_js(NOTIFY_JS)

    win.events.loaded += on_loaded

    def on_start():
        if sys.platform == "win32":
            time.sleep(1)
            hwnd = ctypes.windll.user32.FindWindowW(None, win_title)
            if hwnd:
                api.set_hwnd(hwnd)

    webview.start(func=on_start)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    main()
