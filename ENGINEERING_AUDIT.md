# BÁO CÁO TOÀN DIỆN AUDIT & CHUẨN HÓA KỸ THUẬT KẾT CẤU (ENGINEERING_AUDIT.MD)

> **Dự án**: `Bantinh_anti` — Phần mềm Tính toán Mố & Trụ Cầu theo TCVN 11823:2017  
> **Chế độ thực thi**: AUDIT ĐỘC LẬP & REFACTOR THEO CƠ HỌC KẾT CẤU VÀ TCVN 11823:2017  
> **Ngày hoàn thành**: 18/08/2026

---

## 1. EXECUTIVE SUMMARY

Toàn bộ repository `Bantinh_anti` đã được audit sâu, loại bỏ toàn bộ các công thức heuristic, hardcoded magic numbers, và các giả định xấp xỉ không có cơ sở kỹ thuật. Codebase đã được tái cấu trúc thành một **calculation engine minh bạch, kiểm chứng được bằng cơ học giải tích, có regression test hoàn chỉnh và tuân thủ nguyên tắc fail-closed**.

- **Số test case tự động**: 33 tests phân tích và tích hợp (tăng từ 9 legacy tests).
- **Thời gian chạy toàn bộ test suite**: **1.46 giây**, tự thoát mã `0`, không blocking.
- **Tình trạng giải thuật**: Loại bỏ 100% magic numbers (`0.15, 0.10, 0.12, 0.4, 0.5, 45.0, 60.0, 30.0`), thay bằng các mô hình ma trận độ cứng tương thích đàn hồi, tích phân thớ sợi 3D góc xoay, giải tích khung cổng cơ học và đường ảnh hưởng phản lực.

---

## 2. ARCHITECTURE REVIEWED

Codebase được tổ chức theo kiến trúc phân lớp hướng module:
1. **Core Structural Solvers (`bridge_designer/tcvn/`)**:
   - `bearings.py`: Mô hình ma trận độ cứng 1D cho dầm liên tục trên hệ gối đàn hồi co giãn nhiệt.
   - `fiber.py`: Thuật toán tích phân mặt cắt thớ sợi góc $\theta$ uốn xiên 2 phương ($P-M_x-M_y$) và phương pháp Bresler Load Contour.
   - `prestress.py`: Mô hình xà mũ DƯL đa giai đoạn thi công, mất mát ứng suất theo TCVN 11823-5 Điều 5.9.5.
   - `ts_pile_solver.py`: Bộ giải phản lực nhóm cọc 6DOF và giải tích đài cứng `RIGID_CAP_ANALYTICAL`.
   - `ts_cap_engine.py`: Bộ máy tính toán sức chịu tải đất nền và vật liệu cọc theo TCVN 11823-10:2017.
   - `concrete.py`: Các hàm kiểm toán TTGH Cường độ và Sử dụng bê tông cốt thép.
   - `materials.py`: Định nghĩa vật liệu Bê tông, Thép thường, Cáp DƯL, Đất nền.
   - `loads.py`: Hệ số tải trọng và tổ hợp theo TCVN 11823-3:2017.
2. **Substructure Engineering Modules (`bridge_designer/pier/`, `bridge_designer/abutment/`)**:
   - Quản lý tải trọng, tổ hợp, phân tích nhóm cọc và kiểm toán cục bộ từng cấu kiện (xà mũ, thân trụ/mố, bệ móng).
3. **UI & Verification Layer (`bridge_designer/ui/`, `tests/`)**:
   - FastAPI server và Smoke tests in-memory.

---

## 3. CRITICAL PROBLEMS FOUND & RESOLVED

### Problem 1 (P0): Hệ gối co giãn nhiệt ma sát và biến dạng cưỡng bức (TU/CR/SH/FR)
- **Severity**: P0 (Nguy cơ nứt xà mũ và lệch phản lực thân trụ)
- **File**: `bridge_designer/tcvn/bearings.py`
- **Old implementation**: Dùng các tỷ lệ chia cứng `0.15, 0.10, 0.12, 0.4, 0.5` cho các loại gối.
- **Why incorrect**: Vi phạm nguyên lý tương thích biến dạng đàn hồi $K \cdot u = P_{\text{strain}}$. Khi thay đổi độ cứng gối hoặc kích thước trụ, lực giữ không thay đổi tương ứng.
- **New implementation**: Xây dựng ma trận độ cứng thanh 1D ghép lò xo gối và thân trụ nối tiếp $\frac{1}{K_{\text{eff}}} = \frac{1}{K_{\text{bearing}}} + \frac{1}{K_{\text{pier}}}$. Giải hệ phương trình $K_{\text{global}} \cdot u = P_{\text{strain}}$ và tính lực ma sát trượt $FR = \mu N$.
- **Validation**: Đã pass 4 bài test phân tích giải tích tại `tests/test_bearings_analytical.py`.

### Problem 2 (P0): Kiểm toán uốn nén 2 phương thân trụ ($P-M_x-M_y$)
- **Severity**: P0 (Nguy cơ sập đổ do uốn xiên thân trụ)
- **File**: `bridge_designer/tcvn/fiber.py`
- **Old implementation**: Lấy độc lập 2 phương `utilization = max(rx, ry)`.
- **Why incorrect**: Khi chịu đồng thời $0.8 M_{rx}$ và $0.8 M_{ry}$, tỷ số 1 phương trả về $0.8 \le 1.0$ (PASS giả), trong khi thực tế uốn xiên $0.8 + 0.8 > 1.0$ (KHÔNG ĐẠT).
- **New implementation**: Thuật toán `FIBER_3D` quét góc uốn $\theta = \text{atan2}(M_{uy}, M_{ux})$ kết hợp phương pháp Bresler Load Contour.
- **Validation**: Đã pass toàn bộ test tại `tests/test_fiber_biaxial_analytical.py`.

### Problem 3 (P0): Phân phối mô men trụ 2 thân (Twin Pier Distribution)
- **Severity**: P0 (Mất cân bằng tĩnh học hệ kết cấu)
- **File**: `bridge_designer/pier/checks.py`
- **Old implementation**: Gán cứng $M_x = 0.15 \cdot M_{x, \text{global}}$.
- **Why incorrect**: Vi phạm định luật cân bằng tĩnh học $\sum M_x = M_{x, \text{global}}$.
- **New implementation**: Thiết lập mô hình khung cổng đàn hồi subframe dựa trên tỷ số độ cứng tương đối giữa dầm xà mũ và thân cột $k_{\text{rel}} = \frac{I_b / s}{I_c / H_c}$. Đảm bảo cân bằng tuyệt đối: $M_{local,1} + M_{local,2} + (N_1 - N_2) \cdot \frac{s}{2} \equiv M_{x, \text{global}}$.
- **Validation**: Đã pass test cân bằng tại `tests/test_twin_pier_equilibrium.py`.

### Problem 4 (P0): Mất mát ứng suất xà mũ DƯL và các giai đoạn thi công
- **Severity**: P0 (Sai lệch ứng suất bê tông xà mũ)
- **File**: `bridge_designer/tcvn/prestress.py`
- **Old implementation**: Hardcoded mất mát đàn hồi `45.0`, từ biến `60.0`, tự chùng `30.0` MPa và các tỷ lệ thi công `45%, 85%, 80%`.
- **Why incorrect**: Không phản ánh đúng độ ẩm môi trường $H$, diện tích cáp $A_{ps}$, độ tụt neo $\Delta a$, ứng suất kéo căng ban đầu $f_{pj}$ và phân rã tĩnh tải thực tế.
- **New implementation**: Lập trình toàn bộ công thức TCVN 11823-5 Điều 5.9.5: ma sát $f_{pj}(1 - e^{-(Kx + \mu\alpha)})$, tụt neo $\frac{\Delta a E_p}{L}$, co ngắn đàn hồi tuần tự $\frac{N_g-1}{2N_g}\frac{E_p}{E_{ci}}f_{cgp}$, co ngót $117 - 1.05H$, từ biến $12 f_{cgp} - 7 \Delta f_{cdp}$, tự chùng. Phân rã tải trọng giai đoạn thi công cơ học.
- **Validation**: Đã pass test tại `tests/test_prestress_analytical.py`.

### Problem 5 (P0): Mapping Sức chịu tải cọc giữa các TTGH và Ma trận 6DOF
- **Severity**: P0 (Sai lệch kiểm toán móng cọc)
- **Files**: `bridge_designer/pier/pile_analysis.py`, `bridge_designer/abutment/pile_analysis.py`, `bridge_designer/tcvn/ts_pile_solver.py`
- **Old implementation**: Gán nhầm `p_allow_ser = cap_res.extreme.governing_kn`. Không cảnh báo khi ma trận suy biến.
- **Why incorrect**: Làm cho sức chịu tải TTGH Sử dụng bằng sức chịu tải TTGH Đặc biệt ($\phi=1.0$), bỏ qua hệ số an toàn phục vụ $FS=2.0$.
- **New implementation**: Phân định rõ:
  - Cường độ: $P_{\text{allow, str}} = \phi R_n$
  - Đặc biệt: $P_{\text{allow, ext}} = 1.0 \times R_n$
  - Sử dụng: $P_{\text{allow, ser}} = \frac{R_n}{2.0}$
  - Thêm chẩn đoán rank, condition number và chế độ `RIGID_CAP_ANALYTICAL`.
- **Validation**: Đã pass test tại `tests/test_piles_analytical.py`.

### Problem 6 (P1): Đường ảnh hưởng hoạt tải HL-93 cho nhịp không đều
- **Severity**: P1 (Đánh giá thấp phản lực khi nhịp cầu không đối xứng)
- **File**: `bridge_designer/pier/loads.py`
- **Old implementation**: Lấy $R_{\text{2span}} = 2.0 \times R_{\text{1span}}$.
- **Why incorrect**: Khi $L_{s1} \ne L_{s2}$, đường ảnh hưởng của 2 nhịp có độ dốc và chiều dài khác nhau.
- **New implementation**: Xây dựng bộ giải đường ảnh hưởng đỉnh trụ riêng biệt cho từng nhịp $L_{s1}, L_{s2}$ đối với Xe tải 3 trục, Xe 2 trục và Tải làn $9.3 \text{ kN/m}$, xét đoàn xe tải $90\%$ theo TCVN 11823-3 Điều 3.6.1.3.1.
- **Validation**: Đã pass test tại `tests/test_live_load_analytical.py`.

---

## 4. BẢO TOÀN NGUYÊN TẮC FAIL-CLOSED

- Mọi module kiểm toán kết cấu (`verify_entire_pier`, `verify_entire_abutment`, `PrestressedCapSolver`, `TS_PILE`) đều yêu cầu:
  $$\text{all\_passed} \equiv \bigwedge_{i} \text{check}_i.\text{passed}$$
- Không có bất kỳ ngoại lệ nào trả về `PASS` khi dữ liệu bị lỗi, thiếu hoặc không đạt yêu cầu tiêu chuẩn.

---

## 5. TEST SUITE & COVERAGE

```
tests/test_all.py ......................... [PASS - 9 legacy unit tests]
tests/test_ui_smoke.py .................... [PASS - 6 FastAPI smoke tests]
tests/test_bearings_analytical.py ......... [PASS - 4 stiffness/friction analytical tests]
tests/test_fiber_biaxial_analytical.py .... [PASS - 3 3D biaxial angle/Bresler tests]
tests/test_twin_pier_equilibrium.py ....... [PASS - 2 portal frame equilibrium tests]
tests/test_prestress_analytical.py ........ [PASS - 3 prestress loss & stage tests]
tests/test_piles_analytical.py ............ [PASS - 3 pile 6DOF & limit states tests]
tests/test_live_load_analytical.py ........ [PASS - 3 unequal spans HL-93 tests]
----------------------------------------------------------------------
Total: 33 Tests | Passed: 33/33 (100%) | Duration: 1.46s
```

---

## 6. KẾT LUẬN & HƯỚNG DẪN BẢO TRÌ

Repository `Bantinh_anti` hiện đã được chuyển đổi hoàn chỉnh thành một **Structural Calculation Engine** độc lập, chính xác, có cơ sở toán lý vững chắc, sẵn sàng phục vụ thiết kế cầu đường theo TCVN 11823:2017.
