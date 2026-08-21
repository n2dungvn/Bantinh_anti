"""
Entry point khởi chạy Phần mềm Tính toán Mố & Trụ Cầu TCVN 11823-2017
"""
import sys
import uvicorn
import webbrowser
import threading
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import socket

def find_available_port(preferred_ports=(8000, 8080, 5000, 8501, 8888, 9000, 3000)) -> int:
    for port in preferred_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def run_server(port: int = None):
    if port is None:
        port = find_available_port()

    print("=" * 65)
    print("🌉 KHỞI CHẠY PHẦN MỀM TÍNH TOÁN MỐ & TRỤ CẦU (TCVN 11823-2017)")
    print("=" * 65)
    print(f"• Giao diện Web: http://127.0.0.1:{port}")
    print("• Nhấn Ctrl + C trong cửa sổ này để dừng máy chủ.")
    print("=" * 65)

    def open_browser():
        time.sleep(1.2)
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("bridge_designer.ui.app:app", host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--cli", "-c", "--module", "-m"]:
        from bridge_designer.ui.cli import main
        main()
    else:
        run_server()
