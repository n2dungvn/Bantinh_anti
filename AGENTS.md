# HƯỚNG DẪN QUY TRÌNH LÀM VIỆC DÀNH CHO AI AGENT (AGENTS.MD)

> **Dự án**: Phần mềm Tính toán Mố & Trụ Cầu TCVN 11823:2017 (`n2dungvn/Bantinh_anti`)  
> **Áp dụng cho**: Tất cả các AI Coding Agents (Antigravity, Gemini, Claude, Cursor, Copilot, etc.)

---

## 🔍 PHÂN LOẠI NGUYÊN NHÂN SỰ CỐ (ROOT CAUSE CLASSIFICATION)

- **CONFIRMED**:
  - `python main.py` chạy máy chủ tương tác Uvicorn foreground và tự động mở trình duyệt hệ thống.
  - Lệnh này là tiến trình blocking vô thời hạn, không tự exit, không phù hợp làm lệnh verification cho AI agent.
- **LIKELY**:
  - Chạy tiến trình foreground vô thời hạn hoặc duy trì background server kéo dài khiến công cụ / lớp điều phối (orchestration layer) kích hoạt timeout và hủy bỏ lượt chạy (dẫn đến trạng thái `cancelled`).
- **UNKNOWN**:
  - Cơ chế nội bộ cụ thể mà giao diện Antigravity IDE chuyển đổi trạng thái process termination thành nhãn hiển thị `"user cancel"` (do nằm ngoài phạm vi mã nguồn mở của workspace).

---

## 🚫 1. CÁC LỆNH BỊ CẤM TRONG QUY TRÌNH VERIFICATION

1. **TUYỆT ĐỐI KHÔNG CHẠY `python main.py` TRONG FOREGROUND ĐỂ VERIFY CODE**:
   - `main.py` là trình khởi chạy tương tác (*interactive launcher*) dành riêng cho người dùng cuối.
   - Khi chạy, `main.py` gọi `uvicorn.run(...)` (tiến trình blocking vô thời hạn, không tự thoát) và tự động mở trình duyệt qua `webbrowser.open(...)`.
   - Nếu AI Agent chạy `python main.py`, tiến trình sẽ bị treo và không trả về Exit code.

2. **KHÔNG CHẠY BẤT KỲ DEV SERVER / TIẾN TRÌNH VÔ THỜI HẠN NÀO**:
   - Không chạy `uvicorn bridge_designer.ui.app:app ...` foreground trong tool terminal.
   - Không để lại các tiến trình background server mồ côi (*orphan background tasks*) sau khi kết thúc lượt làm việc.

3. **KHÔNG MỞ TRÌNH DUYỆT TỰ ĐỘNG**:
   - Các lệnh kiểm thử tự động không được kích hoạt mở cửa sổ trình duyệt trên màn hình người dùng.

---

## ✅ 2. CANONICAL VERIFICATION COMMANDS (LỆNH KIỂM THỬ CHUẨN HÓA)

Mọi bước verify code của AI Agent phải dùng các lệnh **in-process, hữu hạn, tự thoát, không sinh side-effect và trả về Exit Code 0 rõ ràng**:

### 🔹 A. Kiểm tra nhanh toàn bộ Web UI & FastAPI Endpoints (Smoke Test):
```bash
python -m unittest tests/test_ui_smoke.py
```
*(Hoặc dùng `pytest`: `python -m pytest tests/test_ui_smoke.py -q`)*  
- Kiểm tra toàn bộ UI template, nạp 5 preset JSON đối chuẩn, gọi API tính toán Mố & Trụ (RC, PT, Twin) trong **< 3 giây** hoàn toàn trong bộ nhớ (*in-process*) qua `TestClient`, không chiếm dụng cổng mạng, không mở browser và không làm bẩn thư mục `output_reports/`.

### 🔹 B. Kiểm tra tính toán kỹ thuật cốt lõi (Core Solvers & TCVN Checks):
```bash
python -m unittest tests/test_all.py
```
- Kiểm tra vật liệu, tải trọng, uốn/cắt/nứt TCVN 11823, tích phân thớ sợi P-M Fiber, solver móng cọc TS_PILE, xà mũ DƯL, và bộ máy xuất báo cáo Word/HTML/PDF trong **< 1 giây**.

### 🔹 C. Kiểm thử chạy dòng lệnh độc lập (CLI Mode):
Nếu muốn kiểm tra xuất file báo cáo thực tế ra đĩa:
```bash
python main.py --cli --module abutment --input bridge_designer/data/default_abutment.json --format html
python main.py --cli --module pier --input bridge_designer/data/default_pier_pt.json --format html
```
- Lệnh này chạy độc lập, tự động hoàn thành và thoát với mã `0`.

---

## 🛡️ 3. QUY TẮC AN TOÀN KHI THỰC THI

1. **Mọi command dùng để verify phải**:
   - Có thời gian thực thi hữu hạn (thường dưới 10 giây).
   - Tự động thoát (*expected exit code*).
   - Không chờ phím bấm tương tác hoặc yêu cầu nhấn `Ctrl + C` để kết thúc.
2. **Quy tắc xử lý máy chủ thật** (nếu bắt buộc phải dùng):
   - Khởi động background, lưu PID.
   - Thực hiện health check với timeout xác định.
   - **Luôn luôn terminate tiến trình đó trước khi trả lời người dùng**.
3. **Khi hoàn thành nhiệm vụ**:
   - AI Agent trả lời kết quả tổng hợp cho người dùng và kết thúc lượt, không duy trì tiến trình chạy nền không cần thiết.
4. **Bảo toàn Logic Kỹ thuật**:
   - Không chỉnh sửa các công thức, thuật toán giải kết cấu, tiêu chuẩn TCVN 11823, hoặc số liệu kỹ thuật chỉ để vượt qua bài test.
