import sys
import json
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path

import tkinter as tk
from tkinter import simpledialog, messagebox
import webview

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

DEFAULT_PORT = 8501
COUNT_PORT   = 8502
TITLE        = "프로젝트 대화 로그방"


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


# ── 서버 카운트 폴링 → 작업표시줄 깜빡임 ───────
def get_remote_count(ip):
    try:
        resp = urllib.request.urlopen(f"http://{ip}:{COUNT_PORT}/", timeout=2)
        return int(resp.read().decode().strip())
    except Exception:
        return -1


def watch_and_flash(server_ip: str, hwnd_ref: list):
    last_count = -1
    while True:
        count = get_remote_count(server_ip)

        if last_count == -1:
            last_count = count
        elif count != -1 and count > last_count:
            last_count = count
            hwnd = hwnd_ref[0]
            if hwnd and not is_foreground(hwnd):
                flash_taskbar(hwnd)
        elif count != -1:
            last_count = count

        time.sleep(2)


# ── 설정 파일 ────────────────────────────────────
def get_config_path():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent / "chat_config.json"
    return Path(__file__).parent / "chat_config.json"


def load_config():
    path = get_config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(ip, port):
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"server_ip": ip, "server_port": port}, f, ensure_ascii=False, indent=2)


# ── 주소 입력 ────────────────────────────────────
def ask_server_address(current=""):
    root = tk.Tk()
    root.withdraw()
    addr = simpledialog.askstring(
        "서버 접속",
        "서버 주소를 입력하세요\n(예: 192.168.1.100:8501)",
        initialvalue=current or f":{DEFAULT_PORT}",
        parent=root,
    )
    root.destroy()
    return (addr or "").strip()


def parse_address(addr):
    if ":" in addr:
        parts = addr.rsplit(":", 1)
        ip = parts[0].strip()
        try:
            port = int(parts[1].strip())
        except ValueError:
            port = DEFAULT_PORT
    else:
        ip = addr.strip()
        port = DEFAULT_PORT
    return ip, port


def check_server(ip, port, timeout=5):
    try:
        urllib.request.urlopen(f"http://{ip}:{port}/_stcore/health", timeout=timeout)
        return True
    except Exception:
        return False


# ── 메인 ────────────────────────────────────────
def main():
    cfg         = load_config()
    server_ip   = cfg.get("server_ip", "")
    server_port = cfg.get("server_port", DEFAULT_PORT)

    if not server_ip:
        addr = ask_server_address()
        if not addr:
            return
        server_ip, server_port = parse_address(addr)

    if not check_server(server_ip, server_port):
        root = tk.Tk(); root.withdraw()
        retry = messagebox.askyesno(
            "연결 실패",
            f"서버에 접속할 수 없습니다.\n{server_ip}:{server_port}\n\n주소를 다시 입력하시겠습니까?",
        )
        root.destroy()
        if not retry:
            return
        addr = ask_server_address(f"{server_ip}:{server_port}")
        if not addr:
            return
        server_ip, server_port = parse_address(addr)

    save_config(server_ip, server_port)

    hwnd_ref = [0]

    win = webview.create_window(
        TITLE,
        url=f"http://{server_ip}:{server_port}",
        width=1280,
        height=800,
        min_size=(800, 600),
    )

    def on_start():
        if sys.platform == "win32":
            hwnd_ref[0] = find_hwnd(TITLE)
        threading.Thread(
            target=watch_and_flash,
            args=(server_ip, hwnd_ref),
            daemon=True,
        ).start()

    webview.start(func=on_start)


if __name__ == "__main__":
    main()
