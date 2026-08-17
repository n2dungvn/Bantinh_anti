"""
Module: pier.model
Mô hình dữ liệu và tham số đầu vào cho bài toán tính toán Trụ cầu (Bridge Pier)
theo TCVN 11823-2017.
Hỗ trợ:
- Trụ 1 thân (Single column) hoặc Trụ 2 thân (Twin / Two-column)
- Xà mũ Bê tông Cốt thép thường (RC Pier Cap) hoặc Xà mũ Dự ứng lực (PT Pier Cap - DƯL)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import math
from ..tcvn.bearings import BearingNode
from ..tcvn.prestress import TendonGroup


@dataclass
class PierPileRow:
    """Khai báo một hàng cọc móng trụ"""
    row_index: int             # Số thứ tự hàng (1, 2, 3, 4)
    x: float                   # Tọa độ x so với tim bệ (m) (+ phía nhịp phải, - phía nhịp trái)
    count: int                 # Số lượng cọc trong hàng
    spacing: float             # Khoảng cách giữa các cọc theo phương ngang (m)


@dataclass
class PierModel:
    """Toàn bộ thông số đầu vào cho trụ cầu"""
    # 0. Thông tin dự án
    project_name: str = "Cầu Km19+000"
    pier_name: str = "Trụ T1"

    # Tùy chọn hình thức kết cấu cốt lõi
    pier_column_type: str = "SINGLE"  # "SINGLE" (Trụ 1 thân) hoặc "TWIN" (Trụ 2 thân)
    spacing_twin_columns: float = 4.0 # Khoảng cách tim 2 thân (m, khi pier_column_type == "TWIN")
    cap_type: str = "RC"              # "RC" (Xà mũ cốt thép thường) hoặc "PT" (Xà mũ DƯL)

    # 1. Kết cấu nhịp
    span_L1: float = 38.2      # Chiều dài nhịp TRÁI (m)
    span_L2: float = 38.2      # Chiều dài nhịp PHẢI (m)
    a0: float = 0.35           # K/c đầu dầm đến tim gối (m)
    Ls1: float = 37.5          # Nhịp tính toán trái (m)
    Ls2: float = 37.5          # Nhịp tính toán phải (m)
    width_W: float = 23.75     # Bề rộng toàn cầu (m)
    width_Bxe: float = 22.75   # Bề rộng phần xe chạy (m)
    width_blc: float = 0.5     # Bề rộng lan can một bên (m)
    width_bpl: float = 0.0     # Bề rộng lề bộ hành (m)
    num_lanes: int = 6         # Số làn xe thiết kế
    d_kcn: float = 3.05        # Chiều cao dầm + bản + lan can chắn gió (m)
    h_bearing: float = 0.15    # Chiều cao gối + đá kê (m)
    DC1_left: float = 6706.01  # Phản lực tĩnh tải DC nhịp trái (kN)
    DC1_right: float = 6706.01 # Phản lực tĩnh tải DC nhịp phải (kN)
    DW_left: float = 684.38    # Phản lực tĩnh tải DW nhịp trái (kN)
    DW_right: float = 684.38   # Phản lực tĩnh tải DW nhịp phải (kN)
    e_left: float = -0.90      # Vị trí dọc hàng gối nhịp trái so tim trụ (m, có dấu)
    e_right: float = 0.90      # Vị trí dọc hàng gối nhịp phải so tim trụ (m, có dấu)
    skew_angle: float = 90.0   # Góc chéo cầu (độ, 90 = vuông góc)

    # 2. Kích thước trụ
    shape_type: int = 1        # 0: Chữ nhật; 1: Đầu tròn; 2: Vát góc
    bth1: float = 5.5          # Thân trụ tại đáy: cạnh NGANG cầu (m)
    hth1: float = 1.6          # Thân trụ tại đáy: cạnh DỌC cầu (m)
    cx: float = 0.3            # Cạnh vát chamfer phương ngang (m, cho shape=2)
    cy: float = 0.3            # Cạnh vát chamfer phương dọc (m, cho shape=2)
    is_tapered: int = 1        # Thân đổi tiết diện? 0 = không; 1 = có
    bth2: float = 9.5          # Cạnh ngang tại đỉnh (m)
    hth2: float = 1.6          # Cạnh dọc tại đỉnh (m)
    Hth: float = 8.4           # Chiều cao thân trụ từ đỉnh bệ đến đáy xà mũ (m)
    bmr: float = 7.5           # Bề rộng ngang tại đỉnh mở rộng đầu búa (m)
    hmr: float = 2.84          # Chiều cao đoạn vát mở rộng đầu búa (m)

    # Xà mũ
    hxm: float = 1.73          # Chiều cao xà mũ tại ngàm (m)
    bxm: float = 2.5           # Bề rộng xà mũ dọc cầu (m)
    Lxm: float = 23.55         # Chiều dài toàn bộ xà mũ ngang cầu (m)
    Vxm: float = 70.0          # Thể tích xà mũ kể cả vút (m³)
    num_bearings_per_row: int = 10 # Số gối trên MỖI hàng gối
    bearing_spacing: float = 2.35  # Khoảng cách giữa các gối ngang cầu (m)

    # Bệ trụ
    Bbe: float = 6.0           # Kích thước bệ DỌC cầu (m)
    Cbe: float = 11.4          # Kích thước bệ NGANG cầu (m)
    Hbe: float = 2.0           # Chiều cao bệ trụ (m)

    # 3. Vật liệu
    fc_prime: float = 30.0     # Cường độ f'c (MPa)
    fy: float = 400.0          # Giới hạn chảy thép fy (MPa)
    Es: float = 200000.0       # Mô đun đàn hồi thép (MPa)
    gamma_c: float = 24.5      # Trọng lượng thể tích BTCT (kN/m³)
    K1: float = 1.0            # Hệ số nguồn cốt liệu

    # 4. Nước & Dòng chảy
    hn1: float = 0.0           # MNTN đo từ đáy bệ (m, 0 = không ngập)
    hn2: float = 0.0           # MNCN đo từ đáy bệ (m)
    V_water: float = 0.0       # Vận tốc dòng chảy thiết kế (m/s)
    CD_water: float = 0.70     # Hệ số cản dọc (0.7 đầu tròn; 1.4 vuông)
    CL_water: float = 0.0      # Hệ số cản ngang
    gamma_w: float = 10.0      # Trọng lượng thể tích nước (kN/m³)

    # 5. Hoạt tải
    IM: float = 0.33           # Lực xung kích
    qlan: float = 9.3          # Tải trọng làn (kN/m)
    pPL: float = 3.0           # Tải trọng người đi bộ (kN/m²)
    Vtk: float = 80.0          # Vận tốc thiết kế đường (km/h)
    R_curve: float = 0.0       # Bán kính cong (m, 0 = thẳng)

    # 6. Hệ gối cầu & Ma sát
    friction_mu: float = 0.07  # Hệ số ma sát gối trượt PTFE
    bearing_state_left: str = "FIXED" # 'ELASTIC', 'SLIDE', 'FIXED'
    bearing_state_right: str = "SLIDE"# 'ELASTIC', 'SLIDE', 'FIXED'
    chain_nodes: List[BearingNode] = field(default_factory=list)

    # 7. Gió
    wind_zone: str = "II"      # Vùng gió I..IV
    terrain_type: int = 1      # Địa hình 1..3
    elev_z: float = 15.0       # Cao độ mặt cầu (m)
    VB: float = 45.0           # Vận tốc gió cơ bản (m/s)
    S_factor: float = 1.115    # Hệ số S
    Cd_kcn: float = 1.25       # Hệ số cản KCN
    Cd_pier: float = 0.80      # Hệ số cản thân trụ (0.8 tròn; 1.4 chữ nhật)

    # 8. Động đất
    accel_A: float = 0.1108    # Hệ số gia tốc A
    soil_type: str = "II"      # Loại đất I..IV
    S_seismic: float = 1.2     # Hệ số thực địa Sđđ
    R_pier: float = 3.0        # Hệ số R trụ đơn (Bảng 18: 3.0 cầu thông thường; 2.0 cầu thiết yếu)
    R_self: float = 1.0        # Hệ số R cho khối lượng bản thân

    # 9. Va xe & Va tàu
    has_vehicle_collision: int = 1 # 1 = có nguy cơ va xe
    CT: float = 1800.0         # Lực va xe CT (kN)
    z_CT: float = 3.2          # Cao độ đặt CT trên đáy bệ (m)
    CV: float = 0.0            # Lực va tàu CV (kN)
    z_CV: float = 0.0          # Cao độ đặt CV trên đáy bệ (m)

    # 10. Móng cọc
    pile_diameter: float = 1.2 # Đường kính cọc D (m)
    pile_rows: List[PierPileRow] = field(default_factory=lambda: [
        PierPileRow(row_index=1, x=-1.8, count=4, spacing=3.2),
        PierPileRow(row_index=2, x=1.8, count=4, spacing=3.2)
    ])
    custom_piles: List[Dict[str, Any]] = field(default_factory=list) # Tọa độ từng cọc riêng biệt nếu không cách đều
    pile_capacity_allowable: float = 4500.0 # Sức chịu tải cho phép 1 cọc (kN)

    # 11. Bố trí cốt thép
    # Thân trụ (mặt cắt đáy - đỉnh bệ)
    rebar_diam_stem: float = 32.0
    rebar_spacing_stem: float = 150.0
    cover_stem: float = 100.0
    stirrup_diam_stem: float = 16.0
    stirrup_spacing_stem: float = 150.0

    # Xà mũ RC (Cốt thép thường)
    rebar_diam_cap_top: float = 32.0   # Thép chịu kéo chính lớp trên
    num_bars_cap_top: int = 24         # Số thanh thép trên
    rebar_diam_cap_bot: float = 25.0   # Thép chịu nén đáy xà mũ
    num_bars_cap_bot: int = 12         # Số thanh thép nén đáy
    cover_cap: float = 75.0
    stirrup_diam_cap: float = 16.0
    stirrup_legs_cap: int = 4
    stirrup_spacing_cap: float = 150.0

    # Xà mũ DƯL (PT Pier Cap)
    fpu: float = 1860.0
    kfpj: float = 0.75
    strand_area: float = 140.0
    K_wobble: float = 6.6e-6
    mu_curvature: float = 0.20
    delta_anchor: float = 6.0
    humidity: float = 80.0
    tendon_groups: List[TendonGroup] = field(default_factory=lambda: [
        TendonGroup(name="G1", num_tendons=8, strands_per_tendon=12, strand_area=140.0, eccentricity_mid=1000.0, eccentricity_end=600.0, tension_stage=1),
        TendonGroup(name="G2", num_tendons=6, strands_per_tendon=12, strand_area=140.0, eccentricity_mid=600.0, eccentricity_end=600.0, tension_stage=3)
    ])

    # Bệ trụ
    rebar_diam_footing_bot_x: float = 28.0 # Thép đáy phương X (dọc cầu)
    rebar_spacing_footing_bot_x: float = 120.0
    rebar_diam_footing_bot_y: float = 28.0 # Thép đáy phương Y (ngang cầu)
    rebar_spacing_footing_bot_y: float = 120.0
    rebar_diam_footing_top_x: float = 20.0 # Thép đỉnh bệ (chịu nén)
    rebar_spacing_footing_top_x: float = 150.0
    rebar_diam_footing_top_y: float = 20.0
    rebar_spacing_footing_top_y: float = 150.0
    stirrup_diam_footing: float = 16.0     # Thép đai chống cắt bệ trụ
    stirrup_spacing_footing: float = 200.0
    stirrup_legs_footing: int = 4
    cover_footing: float = 100.0

    @property
    def alpha_rad(self) -> float:
        return math.radians(self.skew_angle)

    @property
    def total_piles(self) -> int:
        return sum(row.count for row in self.pile_rows)
