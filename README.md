# 🌉 PHẦN MỀM TÍNH TOÁN KẾT CẤU MỐ & TRỤ CẦU (TCVN 11823:2017)

Phần mềm kỹ thuật chuyên nghiệp viết bằng Python phục vụ thiết kế, kiểm toán toàn bộ kết cấu **Mố Cầu** và **Trụ Cầu** theo Tiêu chuẩn Thiết kế Cầu đường bộ Việt Nam **TCVN 11823:2017** (tương đương AASHTO LRFD).

Phần mềm được xây dựng dựa trên 2 file mẫu chuẩn kỹ thuật:
- `Ban-tinh-Mo_Template_v20.xlsm`
- `Tinh-toan-Tru_Template_v36_FIBER.xlsm`

---

## 🌟 CÁC TÍNH NĂNG NỔI BẬT

### 1. Module Mố Cầu (Abutment Module)
- **Tải trọng & Tổ hợp**: Tự động tính tĩnh tải $DC_1, DW, DC_2$ (từng bộ phận mố), áp lực đất tĩnh $EH$, hoạt tải đắp $LS$, lực hãm xe $BR$, ma sát gối $FR$, áp lực gió $WS$, gió trên hoạt tải $WL$, động đất $EQ$ và áp lực đất động đất $\Delta E_{AE}$ (Mononobe-Okabe). Sinh đầy đủ tổ hợp Cường độ I-V, Sử dụng I, Đặc biệt I.
- **Phản lực & Móng cọc**: Phân tích phản lực cọc đài cứng 3D/2D ($P_{max}, P_{min}, H_{max}$), kiểm tra sức chịu tải và chống nhổ cọc.
- **Kiểm toán toàn bộ cấu kiện mố**:
  - **Tường thân mố**: Kiểm toán nén uốn ($M_r = \phi M_n$), cắt dầm rộng ($V_r = \phi (V_c + V_s)$), kiểm toán nứt bề mặt theo TTGH Sử dụng I ($f_{ss} \le f_{sa}$), hàm lượng cốt thép tối thiểu.
  - **Tường đỉnh mố (Backwall)**: Kiểm toán uốn và cắt dưới tác dụng của áp lực đất $EH$, hoạt tải $LS$, lực hãm xe $BR$ và va đập xe.
  - **Tường cánh mố (Wing wall)**: Phân tích theo phương pháp dải Hillerborg — ngàm đứng (chịu mô men uốn ngang) và ngàm đáy (chịu mô men đứng).
  - **Bệ mố (Footing)**: Kiểm toán uốn mép trước (Toe) & mép sau (Heel), cắt 1 phương, cắt đâm thủng 2 phương quanh cọc.

### 2. Module Trụ Cầu (Pier Module)
- **Hình thức Thân Trụ**:
  - **Trụ 1 thân đơn (SINGLE)**: Tích phân thớ sợi (*Fiber Section Engine*) cho tiết diện Chữ nhật, Đầu tròn (Round-ended), hoặc Vát 4 góc (Chamfered). Sinh đường cong tương tác $P-M$ 2 phương dọc/ngang ($M_y, M_x$). Kể đến hệ số phóng đại độ mảnh $\delta_b$ cột công xôn.
  - **Trụ 2 thân (TWIN)**: Phân tích phân phối nội lực khung cứng, kiểm toán nén uốn và chịu lực cho từng cột.
- **Hình thức Xà Mũ**:
  - **Xà mũ RC (Cốt thép thường)**: Phân tích cánh công xôn xà mũ dưới tĩnh tải KCN, tự trọng, hoạt tải xe HL-93 nhiều làn; kiểm toán uốn nhiều lớp thép chủ, cắt và chống-giằng dầm cao (*Strut-and-Tie / Corbel* khi $a_v/d \le 1.0$).
  - **Xà mũ DƯL (Prestressed Concrete Cap - PT)**: Tính toán mất mát ứng suất (ma sát, tụt neo, từ biến, co ngót, tự chùng) cho các bó cáp G1..G7; kiểm toán ứng suất kéo/nén giai đoạn truyền và khai thác (Service I & III); kiểm toán sức kháng uốn $M_r = \phi M_n$.
- **Bệ trụ**: Uốn 2 phương theo phản lực cọc, cắt 1 phương và đâm thủng 2 phương.

### 3. Xuất Báo Cáo Chuyên Nghiệp (Multi-format Reporting)
- **File Word (.docx)**: Thuyết minh tính toán hoàn chỉnh có bìa, bảng biểu định dạng xanh navy, công thức, số liệu trung gian và kết luận **ĐẠT / KHÔNG ĐẠT** có màu sắc rõ ràng.
- **Báo cáo HTML tương tác (.html)**: Có nhúng hình vẽ vector SVG mặt cắt, sơ đồ bố trí cọc, và biểu đồ tương tác $P-M$ trực quan, hỗ trợ in ra PDF A4 chỉ với 1 click.
- **Báo cáo PDF (.pdf)**: File PDF hoàn chỉnh sẵn sàng in ấn và đóng tập hồ sơ.

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY

### 1. Khởi chạy Giao diện Web (Khuyến nghị)
Mở PowerShell / Command Prompt tại thư mục dự án và chạy:
```bash
python main.py
```
Trình duyệt web sẽ tự động mở tại địa chỉ: **`http://127.0.0.1:8000`**

### 2. Sử dụng Giao diện Dòng lệnh (CLI)
- **Tính toán Mố Cầu**:
  ```bash
  python main.py --cli --module abutment --input bridge_designer/data/default_abutment.json --format all
  ```
- **Tính toán Trụ Cầu (Xà mũ DƯL)**:
  ```bash
  python main.py --cli --module pier --input bridge_designer/data/default_pier_pt.json --format docx
  ```

### 3. Chạy bộ kiểm thử tự động (Unit Tests)
```bash
python -m unittest tests/test_all.py
```

---

## 📁 CẤU TRÚC THƯ MỤC NGUỒN

```
d:/5.Ban tinh Antigravity/
├── bridge_designer/               # Gói mã nguồn cốt lõi
│   ├── tcvn/                      # Thư viện tiêu chuẩn TCVN 11823:2017
│   │   ├── materials.py           # Bê tông, Cốt thép, Cáp DƯL, Đất, Nước
│   │   ├── loads.py               # Hệ số tải trọng, gió, động đất
│   │   ├── concrete.py            # Uốn, Cắt, Nứt, Độ mảnh, Đâm thủng
│   │   ├── fiber.py               # Tích phân thớ sợi mặt cắt P-M-M
│   │   ├── piles.py               # Phân tích phản lực cọc đài cứng 3D
│   │   ├── bearings.py            # Giải chuỗi gối cầu 1D
│   │   └── prestress.py           # Solver xà mũ DƯL (Prestressed Cap)
│   ├── abutment/                  # Module tính toán Mố Cầu
│   │   ├── model.py               # Model dữ liệu mố
│   │   ├── loads.py               # Tải trọng mố
│   │   ├── combinations.py        # Tổ hợp tải trọng mố
│   │   ├── pile_analysis.py       # Phân tích cọc mố
│   │   ├── checks.py              # Kiểm toán Thân, Đỉnh, Cánh, Bệ mố
│   │   └── solver.py              # Điều phối giải mố
│   ├── pier/                      # Module tính toán Trụ Cầu
│   │   ├── model.py               # Model dữ liệu trụ (1 thân / 2 thân, RC / PT)
│   │   ├── loads.py               # Tải trọng trụ (nước chảy, va xe, lệch tâm)
│   │   ├── combinations.py        # Tổ hợp tải trọng trụ
│   │   ├── pile_analysis.py       # Phân tích cọc trụ
│   │   ├── checks.py              # Kiểm toán Thân, Xà mũ RC/PT, Bệ trụ
│   │   └── solver.py              # Điều phối giải trụ
│   ├── reporting/                 # Bộ máy xuất báo cáo
│   │   ├── docx_reporter.py       # Xuất Microsoft Word .docx
│   │   ├── html_reporter.py       # Xuất HTML tương tác + SVG
│   │   └── pdf_reporter.py        # Xuất PDF A4
│   ├── ui/                        # Web Dashboard & CLI
│   │   ├── app.py                 # FastAPI backend
│   │   ├── templates/index.html   # Web UI frontend (Tailwind + Chart.js)
│   │   └── cli.py                 # CLI runner
│   └── data/                      # Dự án mẫu JSON
│       ├── default_abutment.json  # Mố A1 Km19+000
│       ├── default_pier_rc.json   # Trụ T1 (1 thân, xà mũ RC)
│       ├── default_pier_pt.json   # Trụ T1 (xà mũ DƯL)
│       └── default_pier_twin.json # Trụ 2 thân (Twin columns)
├── output_reports/                # Thư mục chứa các báo cáo đã xuất
├── tests/                         # Bộ kiểm thử tự động
│   └── test_all.py
├── main.py                        # Điểm khởi chạy chính
└── README.md                      # Hướng dẫn sử dụng
```
