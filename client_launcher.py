import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

import tkinter as tk
from tkinter import simpledialog, messagebox
import pywebview

PORT = 8501
TITLE = "프로젝트 대화 로그방"


def get_config_path():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent / "chat_config.json"
    return Path(__file__).parent / "chat_config.json"


def load_server_ip():
    path = get_config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("server_ip", "")
        except Exception:
            pass
    return ""


def save_server_ip(ip):
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"server_ip": ip}, f, ensure_ascii=False, indent=2)


def ask_server_ip(current=""):
    root = tk.Tk()
    root.withdraw()
    ip = simpledialog.askstring(
        "서버 접속",
        "서버 IP 주소를 입력하세요\n(예: 192.168.1.100)",
        initialvalue=current,
        parent=root,
    )
    root.destroy()
    return (ip or "").strip()


def check_server(ip, port, timeout=5):
    try:
        url = f"http://{ip}:{port}/_stcore/health"
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def main():
    server_ip = load_server_ip()

    if not server_ip:
        server_ip = ask_server_ip()
        if not server_ip:
            return

    if not check_server(server_ip, PORT):
        root = tk.Tk()
        root.withdraw()
        retry = messagebox.askyesno(
            "연결 실패",
            f"서버에 접속할 수 없습니다.\n{server_ip}:{PORT}\n\nIP 주소를 다시 입력하시겠습니까?",
        )
        root.destroy()
        if not retry:
            return
        server_ip = ask_server_ip(server_ip)
        if not server_ip:
            return

    save_server_ip(server_ip)

    pywebview.create_window(
        TITLE,
        url=f"http://{server_ip}:{PORT}",
        width=1280,
        height=800,
        min_size=(800, 600),
    )
    pywebview.start()


if __name__ == "__main__":
    main()
