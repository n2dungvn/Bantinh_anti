# MA TRẬN KIỂM CHỨNG KỸ THUẬT (VALIDATION_MATRIX.MD)

> **Quy ước trạng thái**:
> - `VALIDATED`: Đã kiểm chứng đầy đủ bằng nghiệm giải tích closed-form, tính bất biến cơ học và bộ test tự động.
> - `PARTIALLY_VALIDATED`: Đã kiểm chứng các ca cơ bản, cần bổ sung benchmark mở rộng.
> - `EXPERIMENTAL`: Phương pháp đang phát triển/thử nghiệm, có gắn cờ cảnh báo rõ ràng.
> - `BLOCKED`: Chưa đủ dữ liệu hoặc không đạt điều kiện kiểm toán.

---

| Module / Cấu kiện | Phương pháp Tính toán / Thuật toán | Analytical Check (Nghiệm Giải tích) | Regression Test Suite | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Gối cầu (TU/CR/SH/FR)** | Ma trận độ cứng đàn hồi thanh 1D tương thích $K_{global} \cdot u = P$ & Ma sát trượt $\mu N$ | Nghiệm giải tích thanh đàn hồi ngàm cứng $\Delta T$, trượt tự do $H=0$, tính đối xứng nhiệt độ | `tests/test_bearings_analytical.py` (4 tests) | `VALIDATED` |
| **Thân cột Biaxial P-Mx-My** | Tích phân thớ sợi đa hướng 3D `FIBER_3D` góc uốn $\theta$ & Bresler Contour | Mặt cắt đối xứng uốn 1 trục, uốn xiên $\theta=45^\circ$, loại trừ ca uốn xiên vượt giới hạn | `tests/test_fiber_biaxial_analytical.py` (3 tests) | `VALIDATED` |
| **Trụ 2 thân (Twin Pier)** | Phân phối đàn hồi khung cổng theo tỷ số độ cứng dầm/cột $k_{rel}$ | Bất biến cân bằng mô men và lực dọc: $\sum N = N_{glob}$, $\sum M_x + \Delta N \cdot s = M_{x,glob}$ | `tests/test_twin_pier_equilibrium.py` (2 tests) | `VALIDATED` |
| **Xà mũ DƯL (PT Cap)** | Mất mát ứng suất TCVN 11823-5 Điều 5.9.5 & 7 Giai đoạn thi công phân rã cơ học | Nghiệm giải tích tổn hao ma sát, tụt neo, co ngắn tuần tự, co ngót theo $H$, từ biến theo $f_{cgp}$, cộng tác dụng ứng suất $P/A \pm Pe/W \mp M/W$ | `tests/test_prestress_analytical.py` (3 tests) | `VALIDATED` |
| **Nhóm cọc (TS_PILE & TS_CAP)** | Giải ma trận độ cứng 6DOF $K \Delta = P$ & Đài tuyệt đối cứng `RIGID_CAP_ANALYTICAL` | Cân bằng lực dọc $\sum P_i = N$, mô men $\sum P_i x_i = M_y$, $\sum P_i y_i = M_x$, chẩn đoán Rank và Condition Number | `tests/test_piles_analytical.py` (3 tests) | `VALIDATED` |
| **Sức chịu tải cọc** | TCVN 11823-10: Cường độ ($\phi R_n$), Đặc biệt ($1.0 R_n$), Sử dụng ($R_n / 2.0$) | Thứ tự kháng tải cơ học: $P_{ser} < P_{ext}$, phân tách rạch ròi hệ số an toàn phục vụ | `tests/test_piles_analytical.py` (1 test) | `VALIDATED` |
| **Hoạt tải HL-93 (Live Load)** | Đường ảnh hưởng đỉnh trụ cho nhịp không đều $L_{s1} \ne L_{s2}$ & Đoàn xe tải $90\%$ | Nghiệm giải tích đường ảnh hưởng tam giác, tích phân tải làn $q_{lan} L / 2$, hệ số làn $m$ | `tests/test_live_load_analytical.py` (3 tests) | `VALIDATED` |
| **Mố cầu (Abutment)** | Áp lực đất tĩnh Coulomb/Rankine, Hoạt tải đắp đất LS, Uốn thuần túy bảo thủ | Cân bằng áp lực đất, moment lật và phản lực bệ móng | `bridge_designer/abutment/` & `tests/test_all.py` | `VALIDATED` |
| **Web UI & API Engine** | FastAPI In-Process TestClient với 5 preset đối chuẩn thực tế | Khởi tạo, parse JSON, giải kết cấu Mố, Trụ đơn RC, Trụ DƯL PT, Trụ 2 thân trong bộ nhớ | `tests/test_ui_smoke.py` (6 tests) | `VALIDATED` |
