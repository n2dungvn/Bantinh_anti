"""
Module: tcvn.loads
Các quy định về Tải trọng và Tổ hợp Tải trọng theo TCVN 11823-3:2017.
Bao gồm:
- Hệ số tải trọng và tổ hợp tải trọng (Bảng 3 & Bảng 4)
- Hoạt tải xe HL-93, tải trọng làn, người đi bộ, lực xung kích IM, hệ số làn m
- Lực hãm xe BR, lực ly tâm CE
- Áp lực đất tĩnh EH, hoạt tải đắp đất LS, áp lực đất động Mononobe-Okabe ΔEAE
- Tải trọng gió WS, WL, Pv (Bảng 13 & 14)
- Tải trọng động đất EQ
- Tải trọng dòng chảy WA, lực đẩy nổi WB
- Lực va xe CT (1800 kN) và va tàu CV
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


# Hệ số làn xe m (TCVN 11823-3 Bảng 7)
MULTI_LANE_FACTORS = {
    1: 1.20,
    2: 1.00,
    3: 0.85,
}

def get_multi_lane_factor(num_lanes: int) -> float:
    """Lấy hệ số làn m theo số làn xe thiết kế chất tải"""
    if num_lanes <= 0:
        return 0.0
    if num_lanes in MULTI_LANE_FACTORS:
        return MULTI_LANE_FACTORS[num_lanes]
    return 0.65  # >= 4 làn xe: 0.65


# Bảng tra tốc độ gió cơ bản VB (m/s) theo Vùng gió (TCVN 11823-3 Bảng 13)
WIND_VB_MAP = {
    "I": 38.0,
    "II": 45.0,
    "III": 53.0,
    "IV": 59.0
}

# Bảng tra hệ số điều chỉnh S theo dạng địa hình và cao độ z (TCVN 11823-3 Bảng 14)
# Cao độ (m): 10, 15, 20, 30, 40, 50
WIND_S_TABLE = {
    1: [(10, 1.00), (15, 1.115), (20, 1.20), (30, 1.32), (40, 1.40), (50, 1.46)], # Địa hình 1: Lộ thiên, mặt nước
    2: [(10, 1.00), (15, 1.09), (20, 1.15), (30, 1.25), (40, 1.32), (50, 1.38)],  # Địa hình 2: Đồi núi, rừng, nhà <=10m
    3: [(10, 0.80), (15, 0.90), (20, 0.98), (30, 1.10), (40, 1.18), (50, 1.25)],  # Địa hình 3: Khu vực nhiều nhà cao tầng
}

def get_wind_s_factor(terrain: int, z: float) -> float:
    """Nội suy tuyến tính hệ số S từ Bảng 14"""
    if terrain not in WIND_S_TABLE:
        terrain = 2
    points = WIND_S_TABLE[terrain]
    # Chặn biên cao độ 10m .. 50m
    if z <= points[0][0]:
        return points[0][1]
    if z >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        z0, s0 = points[i]
        z1, s1 = points[i+1]
        if z0 <= z <= z1:
            return s0 + (s1 - s0) * (z - z0) / (z1 - z0)
    return 1.0


# Bảng tra hệ số thực địa động đất S_dd (TCVN 11823-3 Bảng 17)
SEISMIC_SITE_FACTORS = {
    "I": 1.0,   # Đá hoặc đất chặt
    "II": 1.2,  # Đất cát chặt, đất dính cứng
    "III": 1.5, # Đất cát chặt vừa, đất dính dẻo cứng
    "IV": 2.0   # Đất yếu, than bùn, sét mềm
}

# Hệ số điều chỉnh đáp ứng R (TCVN 11823-3 Bảng 18)
# Thân mố: 1.5; Trụ đơn: 3.0 (cầu thông thường) / 2.0 (cầu thiết yếu); Khối lượng bản thân: 1.0


@dataclass
class LoadCombinationFactors:
    """Hệ số tải trọng cho một tổ hợp cụ thể (TCVN 11823-3 Bảng 3 & Bảng 4)"""
    name: str
    gamma_DC_max: float = 1.25
    gamma_DC_min: float = 0.90
    gamma_DW_max: float = 1.50
    gamma_DW_min: float = 0.65
    gamma_EV_max: float = 1.35
    gamma_EV_min: float = 1.00
    gamma_EH_max: float = 1.50
    gamma_EH_min: float = 0.90
    gamma_LL: float = 1.75
    gamma_LS: float = 1.75
    gamma_WA: float = 1.00
    gamma_WS: float = 0.00
    gamma_WL: float = 0.00
    gamma_FR: float = 1.00
    gamma_TU: float = 0.00
    gamma_CR_SH: float = 1.00
    gamma_EQ: float = 0.00
    gamma_CT: float = 0.00
    gamma_CV: float = 0.00


def get_standard_load_combinations() -> Dict[str, LoadCombinationFactors]:
    """
    Trả về danh mục các tổ hợp tải trọng chuẩn theo TCVN 11823-3
    - Cường độ I: Hoạt tải chính xe cộ
    - Cường độ II: Xe đặc biệt / quá tải
    - Cường độ III: Gió bão thiết kế (V_design), không hoạt tải
    - Cường độ IV: Tỷ số tĩnh tải rất lớn
    - Cường độ V: Gió vừa phải (V = 25 m/s) + Hoạt tải
    - Sử dụng I: Điều kiện khai thác tiêu chuẩn, nứt, võng (V_wind = 25 m/s)
    - Sử dụng II: Kiểm soát ứng suất bản bê tông & liên hợp
    - Sử dụng III: Kiểm toán nứt cho bê tông DƯL (kéo)
    - Sử dụng IV: Kiểm toán ứng suất cột/mố nền móng
    - Đặc biệt I: Động đất EQ
    - Đặc biệt II: Va xe CT / Va tàu CV
    - Mỏi I: Tổ hợp mỏi
    """
    combs = {
        # CƯỜNG ĐỘ
        "CD_I": LoadCombinationFactors(
            name="Cường độ I",
            gamma_DC_max=1.25, gamma_DC_min=0.90,
            gamma_DW_max=1.50, gamma_DW_min=0.65,
            gamma_EV_max=1.35, gamma_EV_min=1.00,
            gamma_EH_max=1.50, gamma_EH_min=0.90,
            gamma_LL=1.75, gamma_LS=1.75,
            gamma_WA=1.00, gamma_WS=0.00, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=0.50, gamma_CR_SH=1.00,
            gamma_EQ=0.00, gamma_CT=0.00, gamma_CV=0.00
        ),
        "CD_II": LoadCombinationFactors(
            name="Cường độ II",
            gamma_DC_max=1.25, gamma_DC_min=0.90,
            gamma_DW_max=1.50, gamma_DW_min=0.65,
            gamma_EV_max=1.35, gamma_EV_min=1.00,
            gamma_EH_max=1.50, gamma_EH_min=0.90,
            gamma_LL=1.35, gamma_LS=1.35,
            gamma_WA=1.00, gamma_WS=0.00, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=0.50, gamma_CR_SH=1.00
        ),
        "CD_III": LoadCombinationFactors(
            name="Cường độ III",
            gamma_DC_max=1.25, gamma_DC_min=0.90,
            gamma_DW_max=1.50, gamma_DW_min=0.65,
            gamma_EV_max=1.35, gamma_EV_min=1.00,
            gamma_EH_max=1.50, gamma_EH_min=0.90,
            gamma_LL=0.00, gamma_LS=0.00,
            gamma_WA=1.00, gamma_WS=1.40, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=0.50, gamma_CR_SH=1.00
        ),
        "CD_IV": LoadCombinationFactors(
            name="Cường độ IV",
            gamma_DC_max=1.50, gamma_DC_min=0.90,
            gamma_DW_max=1.50, gamma_DW_min=0.65,
            gamma_EV_max=1.35, gamma_EV_min=1.00,
            gamma_EH_max=1.50, gamma_EH_min=0.90,
            gamma_LL=0.00, gamma_LS=0.00,
            gamma_WA=1.00, gamma_WS=0.00, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=0.50, gamma_CR_SH=1.00
        ),
        "CD_V": LoadCombinationFactors(
            name="Cường độ V",
            gamma_DC_max=1.25, gamma_DC_min=0.90,
            gamma_DW_max=1.50, gamma_DW_min=0.65,
            gamma_EV_max=1.35, gamma_EV_min=1.00,
            gamma_EH_max=1.50, gamma_EH_min=0.90,
            gamma_LL=1.35, gamma_LS=1.35,
            gamma_WA=1.00, gamma_WS=0.40, gamma_WL=1.00,
            gamma_FR=1.00, gamma_TU=0.50, gamma_CR_SH=1.00
        ),
        # SỬ DỤNG
        "SD_I": LoadCombinationFactors(
            name="Sử dụng I",
            gamma_DC_max=1.00, gamma_DC_min=1.00,
            gamma_DW_max=1.00, gamma_DW_min=1.00,
            gamma_EV_max=1.00, gamma_EV_min=1.00,
            gamma_EH_max=1.00, gamma_EH_min=1.00,
            gamma_LL=1.00, gamma_LS=1.00,
            gamma_WA=1.00, gamma_WS=0.30, gamma_WL=1.00,
            gamma_FR=1.00, gamma_TU=1.00, gamma_CR_SH=1.00
        ),
        "SD_II": LoadCombinationFactors(
            name="Sử dụng II",
            gamma_DC_max=1.00, gamma_DC_min=1.00,
            gamma_DW_max=1.00, gamma_DW_min=1.00,
            gamma_EV_max=1.00, gamma_EV_min=1.00,
            gamma_EH_max=1.00, gamma_EH_min=1.00,
            gamma_LL=1.30, gamma_LS=1.30,
            gamma_WA=1.00, gamma_WS=0.00, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=1.00, gamma_CR_SH=1.00
        ),
        "SD_III": LoadCombinationFactors(
            name="Sử dụng III",
            gamma_DC_max=1.00, gamma_DC_min=1.00,
            gamma_DW_max=1.00, gamma_DW_min=1.00,
            gamma_EV_max=1.00, gamma_EV_min=1.00,
            gamma_EH_max=1.00, gamma_EH_min=1.00,
            gamma_LL=0.80, gamma_LS=0.80,
            gamma_WA=1.00, gamma_WS=0.00, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=1.00, gamma_CR_SH=1.00
        ),
        "SD_IV": LoadCombinationFactors(
            name="Sử dụng IV",
            gamma_DC_max=1.00, gamma_DC_min=1.00,
            gamma_DW_max=1.00, gamma_DW_min=1.00,
            gamma_EV_max=1.00, gamma_EV_min=1.00,
            gamma_EH_max=1.00, gamma_EH_min=1.00,
            gamma_LL=0.00, gamma_LS=0.00,
            gamma_WA=1.00, gamma_WS=0.70, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=1.00, gamma_CR_SH=1.00
        ),
        # ĐẶC BIỆT
        "DB_I": LoadCombinationFactors(
            name="Đặc biệt I (Động đất)",
            gamma_DC_max=1.25, gamma_DC_min=0.90,
            gamma_DW_max=1.50, gamma_DW_min=0.65,
            gamma_EV_max=1.35, gamma_EV_min=1.00,
            gamma_EH_max=1.50, gamma_EH_min=0.90,
            gamma_LL=0.50, gamma_LS=0.00, # gamma_EQ cho LL thường lấy 0.5
            gamma_WA=1.00, gamma_WS=0.00, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=0.00, gamma_CR_SH=1.00,
            gamma_EQ=1.00
        ),
        "DB_II": LoadCombinationFactors(
            name="Đặc biệt II (Va chạm)",
            gamma_DC_max=1.25, gamma_DC_min=0.90,
            gamma_DW_max=1.50, gamma_DW_min=0.65,
            gamma_EV_max=1.35, gamma_EV_min=1.00,
            gamma_EH_max=1.50, gamma_EH_min=0.90,
            gamma_LL=0.50, gamma_LS=0.00,
            gamma_WA=1.00, gamma_WS=0.00, gamma_WL=0.00,
            gamma_FR=1.00, gamma_TU=0.00, gamma_CR_SH=1.00,
            gamma_CT=1.00, gamma_CV=1.00
        ),
        # MỎI
        "MOI_I": LoadCombinationFactors(
            name="Mỏi I",
            gamma_DC_max=0.00, gamma_DC_min=0.00,
            gamma_DW_max=0.00, gamma_DW_min=0.00,
            gamma_EV_max=0.00, gamma_EV_min=0.00,
            gamma_EH_max=0.00, gamma_EH_min=0.00,
            gamma_LL=1.50, gamma_LS=0.00,
            gamma_WA=0.00, gamma_WS=0.00, gamma_WL=0.00,
            gamma_FR=0.00, gamma_TU=0.00, gamma_CR_SH=0.00
        )
    }
    return combs


# Bảng cấp sông và thông số tàu thiết kế mặc định (TCVN 11823-3 Điều 3.14)
RIVER_CLASS_DEFAULTS = {
    "Cấp I": {"dwt": 3000.0, "v_ship": 3.5, "v_water": 1.8},
    "Cấp II": {"dwt": 2000.0, "v_ship": 3.2, "v_water": 1.6},
    "Cấp III": {"dwt": 1000.0, "v_ship": 3.0, "v_water": 1.5},
    "Cấp IV": {"dwt": 500.0, "v_ship": 2.5, "v_water": 1.2},
    "Cấp V": {"dwt": 300.0, "v_ship": 2.0, "v_water": 1.0},
    "Cấp VI": {"dwt": 100.0, "v_ship": 1.8, "v_water": 0.8},
}

def calculate_vessel_collision_force(
    river_class: str = "Cấp III",
    ship_dwt: float = 1000.0,
    ship_velocity: float = 3.0,
    water_velocity: float = 1.5
) -> Tuple[float, float, str]:
    """
    Tính toán lực va xô tàu thủy PS vào trụ cầu theo TCVN 11823-3 Điều 3.14.5.1
    Công thức: PS = 1.09 * 10^3 * V * sqrt(DWT)
    Trong đó:
      - V: Tổng vận tốc va chạm = V_ship + V_water (m/s)
      - DWT: Trọng tải tàu thiết kế (tấn)
      - PS: Lực va chạm tương đương tĩnh (kN)
    """
    dwt = ship_dwt if ship_dwt > 0 else 1000.0
    v_total = max(0.5, ship_velocity + water_velocity)
    # Lực va chạm chuẩn TCVN
    Ps_kN = 1.09 * 1.0e3 * v_total * math.sqrt(dwt)
    # Động năng va chạm KE = 0.5 * M * V^2 (kJ) với M = 1.05 * DWT * 1000 kg
    M_kg = 1.05 * dwt * 1000.0
    KE_kJ = 0.5 * M_kg * (v_total ** 2) / 1000.0
    formula_str = f"PS = 1.09×10³ × ({v_total:.2f} m/s) × √({dwt:.0f} T) = {Ps_kN:.1f} kN"
    return Ps_kN, KE_kJ, formula_str


def calculate_pedestrian_load(
    width_bpl: float,
    span_L: float,
    p_PL: float = 3.0,
    skew_angle_deg: float = 90.0
) -> float:
    """
    Tính tải trọng người đi bộ PL truyền xuống gối mố/trụ (kN)
    PL = p_PL * width_bpl * (span_L / 2)
    """
    if width_bpl <= 0:
        return 0.0
    alpha_rad = math.radians(skew_angle_deg)
    # Phản lực KCN truyền xuống mố/trụ
    return p_PL * width_bpl * (span_L / 2.0)

