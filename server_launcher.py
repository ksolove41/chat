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

PORT = 8501
TITLE = "프로젝트 대화 로그방"


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
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("오류", f"chat.py를 찾을 수 없습니다.\n경로: {chat_py}")
        root.destroy()
        return

    proc, err = start_streamlit(chat_py)
    if err:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("오류", err)
        root.destroy()
        return

    if not wait_for_server(PORT, 30):
        proc.terminate()
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("오류", "서버 시작 시간 초과 (30초)\nStreamlit이 응답하지 않습니다.")
        root.destroy()
        return

    local_ip = get_local_ip()

    webview.create_window(
        f"{TITLE}  ─  서버 IP: {local_ip}:{PORT}",
        url=f"http://localhost:{PORT}",
        width=1280,
        height=800,
        min_size=(800, 600),
    )
    webview.start()

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    main()
