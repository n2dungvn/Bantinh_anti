"""
Module: abutment.model
Mô hình dữ liệu và tham số đầu vào cho bài toán tính toán mố cầu (Bridge Abutment)
theo TCVN 11823-2017.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import math


@dataclass
class AbutmentPileRow:
    """Khai báo một hàng cọc móng mố"""
    row_index: int             # Số thứ tự hàng (1, 2, 3, 4)
    x: float                   # Tọa độ x so với tim bệ (m) (+ phía nhịp, - phía lưng mố)
    count: int                 # Số lượng cọc trong hàng
    spacing: float             # Khoảng cách giữa các cọc theo phương ngang (m)


@dataclass
class AbutmentModel:
    """Toàn bộ thông số đầu vào cho mố cầu"""
    # 0. Thông tin dự án
    project_name: str = "Cầu Km19+000"
    abutment_name: str = "Mố A1"

    # 1. Kết cấu nhịp và mặt cầu
    span_L: float = 38.2       # Chiều dài nhịp (m)
    a0: float = 0.35           # Khoảng cách từ đầu dầm đến tim gối (m)
    Ls: float = 37.5           # Chiều dài nhịp tính toán (m)
    width_W: float = 23.75     # Bề rộng toàn cầu (m)
    width_Bxe: float = 22.75   # Bề rộng phần xe chạy (m)
    width_blc: float = 0.5     # Bề rộng lan can một bên (m)
    width_bpl: float = 0.0     # Bề rộng lề bộ hành tổng (m)
    num_lanes: int = 6         # Số làn xe thiết kế
    num_girders: int = 10      # Số dầm chủ
    h_girder: float = 1.75     # Chiều cao dầm chủ (m)
    t_deck: float = 0.20       # Chiều dày bản mặt cầu (m)
    h_barrier: float = 1.10    # Chiều cao lan can (m)
    h_bearing: float = 0.15    # Chiều cao gối + đá kê (m)
    DC_kcn: float = 6725.63    # Phản lực tĩnh tải DC của KCN lên mố (kN)
    DW_kcn: float = 684.38     # Phản lực tĩnh tải DW lên mố (kN)

    # 2. Kích thước mố định hình
    B1: float = 6.0            # Chiều rộng bệ mố dọc cầu (m)
    B2: float = 2.7            # Chiều dài tường cánh phần dưới (m)
    B3: float = 1.3            # Chiều dày tường thân (m)
    B4: float = 2.0            # K/c tường thân đến mép bệ phía nhịp (m)
    B5: float = 2.8            # Chiều dài tường cánh phần đuôi (m)
    B7: float = 0.5            # Chiều dày tường đỉnh (m)
    B8: float = 0.457          # K/c tim gối đến mép trong tường đỉnh (m)
    B9: float = 0.3            # Kích thước mấu đỡ bản quá độ (m)
    B11: float = 0.5           # Chiều rộng ụ chống xô dọc cầu (m)
    B12: float = 0.0           # Bề rộng đất đắp trước mố (m)
    H1: float = 1.8            # Chiều cao bệ mố (m)
    H2: float = 4.23           # Chiều cao tường cánh đoạn dưới (m)
    H3: float = 2.80           # Chiều cao tường cánh đoạn giữa (m)
    H4: float = 1.50           # Chiều cao tường cánh đoạn trên (m)
    H6: float = 6.304          # Chiều cao tường thân (m)
    H7: float = 1.264          # Chiều cao tường đỉnh (m)
    H8: float = 0.5            # Chiều cao tường tai (m)
    H12: float = 0.0           # Chiều cao đất đắp trước mố (m)
    C1: float = 23.55          # Chiều rộng bệ mố ngang cầu (m)
    C3: float = 0.5            # Chiều dày tường cánh (m)
    C4: float = 0.15           # Chiều dày tường tai (m)
    C6: float = 0.8            # Chiều rộng ụ chống xô ngang cầu (m)
    ntc: int = 2               # Số tường cánh (cái)
    ntt: int = 2               # Số tường tai (cái)
    skew_angle: float = 70.0   # Góc chéo của mố so với tim cầu (độ, 90 = vuông góc)

    # 3. Vật liệu
    fc_prime: float = 30.0     # Cường độ bê tông f'c (MPa)
    fy: float = 400.0          # Giới hạn chảy thép fy (MPa)
    Es: float = 200000.0       # Mô đun đàn hồi thép (MPa)
    gamma_c: float = 24.5      # Trọng lượng thể tích BTCT (kN/m³)
    K1: float = 1.0            # Hệ số nguồn cốt liệu

    # 4. Đất đắp & Nước
    gamma_s: float = 19.25     # Trọng lượng thể tích đất đắp (kN/m³)
    phi: float = 30.0          # Góc nội ma sát hữu hiệu đất đắp (độ)
    delta: float = 0.0         # Góc ma sát đất - tường (độ)
    beta: float = 0.0          # Góc dốc mặt đất đắp (độ)
    gamma_w: float = 10.0      # Trọng lượng thể tích nước (kN/m³)

    # 5. Hoạt tải
    IM: float = 0.33           # Lực xung kích
    qlan: float = 9.3          # Tải trọng làn (kN/m)
    pPL: float = 3.0           # Tải trọng người đi bộ (kN/m²)
    Vtk: float = 80.0          # Vận tốc thiết kế (km/h)
    R_curve: float = 0.0       # Bán kính cong (m, 0 = thẳng)

    # 6. Gối cầu
    bearing_type: int = 0      # 0 = di động; 1 = cố định
    friction_mu: float = 0.07  # Hệ số ma sát gối trượt
    h_cx: float = 0.38         # Chiều cao ụ chống xô (m)
    num_cx: int = 5            # Số ụ chống xô

    # 7. Gió
    wind_zone: str = "II"      # Vùng gió I, II, III, IV
    terrain_type: int = 1      # Địa hình 1, 2, 3
    elev_z: float = 15.0       # Cao độ mặt cầu (m)
    VB: float = 45.0           # Vận tốc gió cơ bản (m/s)
    S_factor: float = 1.09     # Hệ số điều chỉnh địa hình S
    Cd_kcn: float = 1.25       # Hệ số cản KCN
    Cx_sub: float = 1.17       # Hệ số cản thân/tường mố

    # 8. Động đất
    accel_A: float = 0.1108    # Hệ số gia tốc động đất A
    soil_type: str = "II"      # Loại đất nền I, II, III, IV
    S_seismic: float = 1.2     # Hệ số thực địa Sđđ
    R_super: float = 1.5       # Hệ số R cho KCN truyền xuống
    R_sub: float = 1.0         # Hệ số R cho khối lượng bản thân mố
    kh_seismic: float = 0.1108 # Hệ số động đất ngang kh dùng cho Mononobe-Okabe

    # 9. Móng cọc
    pile_diameter: float = 1.2 # Đường kính cọc D (m)
    pile_rows: List[AbutmentPileRow] = field(default_factory=lambda: [
        AbutmentPileRow(row_index=1, x=-1.8, count=5, spacing=5.33),
        AbutmentPileRow(row_index=2, x=1.8, count=6, spacing=4.27)
    ])
    custom_piles: List[Dict[str, Any]] = field(default_factory=list) # Tọa độ từng cọc riêng biệt nếu không cách đều
    pile_capacity_allowable: float = 3500.0 # Sức chịu tải cho phép 1 cọc (kN)

    # 10. Bố trí cốt thép chi tiết từng cấu kiện
    # Thân mố
    rebar_diam_stem_rear: float = 25.0         # Thép dọc chịu kéo chính (Mặt sau - Phía đất đắp)
    rebar_spacing_stem_rear: float = 150.0     # Bước thép chịu kéo mặt sau (mm)
    rebar_diam_stem_front: float = 20.0        # Thép dọc chịu nén / cấu tạo (Mặt trước - Phía nhịp)
    rebar_spacing_stem_front: float = 150.0    # Bước thép mặt trước (mm)
    rebar_diam_stem: float = 25.0              # Alias cho tương thích
    rebar_spacing_stem: float = 150.0
    cover_stem: float = 75.0
    stirrup_diam_stem: float = 14.0
    stirrup_spacing_stem: float = 200.0
    stirrup_legs_stem: int = 4

    # Tường đỉnh (Tách riêng biệt)
    rebar_diam_backwall: float = 16.0          # Thép chịu uốn mặt sau (mặt tiếp xúc đất)
    rebar_spacing_backwall: float = 150.0
    rebar_diam_backwall_front: float = 14.0    # Thép cấu tạo mặt trước
    rebar_spacing_backwall_front: float = 150.0
    stirrup_diam_backwall: float = 12.0        # Thép đai tường đỉnh
    stirrup_spacing_backwall: float = 200.0
    stirrup_legs_backwall: int = 2
    cover_backwall: float = 75.0

    # Tường cánh (Tách riêng biệt theo Hillerborg & Hình học thực)
    rebar_diam_wing_horiz: float = 20.0        # Thép ngang ngàm đứng (lớp trong chịu kéo)
    rebar_spacing_wing_horiz: float = 150.0
    rebar_diam_wing_horiz_outer: float = 14.0  # Thép ngang mặt ngoài (cấu tạo)
    rebar_spacing_wing_horiz_outer: float = 150.0
    rebar_diam_wing_vert: float = 20.0         # Thép đứng ngàm đáy (lớp trong chịu kéo)
    rebar_spacing_wing_vert: float = 150.0
    rebar_diam_wing_vert_outer: float = 14.0   # Thép đứng mặt ngoài (cấu tạo)
    rebar_spacing_wing_vert_outer: float = 150.0
    stirrup_diam_wing: float = 12.0            # Thép đai/đai móc tường cánh
    stirrup_spacing_wing: float = 200.0
    cover_wing: float = 75.0

    # Bệ mố
    rebar_diam_footing_bot_x: float = 28.0     # Thép đáy phương dọc cầu (Lớp dưới chịu uốn chính - Mũi & Gót)
    rebar_spacing_footing_bot_x: float = 120.0 # Bước thép đáy dọc cầu (mm)
    rebar_diam_footing_top_x: float = 20.0     # Thép đỉnh phương dọc cầu (Lớp trên / Thép nén gót)
    rebar_spacing_footing_top_x: float = 150.0 # Bước thép đỉnh dọc cầu (mm)
    rebar_diam_footing_bot_y: float = 20.0     # Thép đáy phương ngang cầu (Phân bố lớp dưới)
    rebar_spacing_footing_bot_y: float = 150.0
    rebar_diam_footing_top_y: float = 20.0     # Thép đỉnh phương ngang cầu (Phân bố lớp trên)
    rebar_spacing_footing_top_y: float = 150.0
    rebar_diam_footing_bot_front: float = 28.0 # Alias
    rebar_spacing_footing_bot_front: float = 120.0
    rebar_diam_footing_bot_rear: float = 28.0  # Alias
    rebar_spacing_footing_bot_rear: float = 120.0
    rebar_diam_footing_top: float = 20.0       # Alias
    rebar_spacing_footing_top: float = 150.0
    stirrup_diam_footing: float = 16.0         # Thép đai chống cắt bệ mố
    stirrup_spacing_footing: float = 200.0
    stirrup_legs_footing: int = 4
    cover_footing: float = 100.0

    @property
    def alpha_rad(self) -> float:
        return math.radians(self.skew_angle)

    @property
    def Beff(self) -> float:
        """Bề rộng chịu áp lực đất hữu hiệu (m)"""
        # Beff = (C1 - ntc * C3) / sin(alpha)
        sin_a = math.sin(self.alpha_rad)
        return (self.C1 - self.ntc * self.C3) / sin_a if sin_a > 0 else self.C1

    @property
    def Hdb(self) -> float:
        """Chiều cao đất đắp tính đến ĐÁY BỆ (m)"""
        return self.H1 + self.H6 + self.H7

    @property
    def Htb(self) -> float:
        """Chiều cao đất đắp tính đến ĐỈNH BỆ (m)"""
        return self.H6 + self.H7

    @property
    def total_piles(self) -> int:
        return sum(row.count for row in self.pile_rows)
