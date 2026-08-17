"""
Entry point khởi chạy Phần mềm Tính toán Mố & Trụ Cầu TCVN 11823-2017
"""
import sys
import uvicorn
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8000")

def run_server():
    print("=" * 65)
    print("🌉 KHỞI CHẠY PHẦN MỀM TÍNH TOÁN MỐ & TRỤ CẦU (TCVN 11823-2017)")
    print("=" * 65)
    print("• Giao diện Web: http://127.0.0.1:8000")
    print("• Nhấn Ctrl + C trong cửa sổ này để dừng máy chủ.")
    print("=" * 65)

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("bridge_designer.ui.app:app", host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--cli", "-c", "--module", "-m"]:
        from bridge_designer.ui.cli import main
        main()
    else:
        run_server()
