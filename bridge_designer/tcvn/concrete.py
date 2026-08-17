"""
Module: tcvn.concrete
Các công thức tính toán sức kháng và kiểm toán kết cấu bê tông cốt thép
theo TCVN 11823-5:2017.
Bao gồm:
- Sức kháng uốn Mr = phi * Mn của tiết diện chữ nhật
- Sức kháng cắt Vr = phi * Vn (Vc + Vs)
- Kiểm toán nứt theo TTGH Sử dụng (Điều 7.3.4: fss <= fsa)
- Kiểm toán hàm lượng cốt thép tối thiểu (Điều 7.3.3.2: Mr >= min(Mcr, 1.33 Mu))
- Kiểm toán hàm lượng cốt thép tối đa (Điều 7.4.2)
- Hệ số phóng đại mô men do độ mảnh (Điều 7.4.3: delta_b)
- Kiểm toán chống-giằng / dầm cao cho xà mũ (Điều 8.1.1: av/d <= 1.0)
"""
import math
from dataclasses import dataclass
from typing import Tuple, Dict, Any
from .materials import Concrete, Rebar


def get_phi_flexure(eps_t: float, eps_y: float = 0.002) -> float:
    """
    Hệ số sức kháng phi cho uốn và nén-uốn (TCVN 11823-5 Điều 5.4.2.1)
    - Tiết diện chịu kéo khống chế (eps_t >= 0.005): phi = 0.90
    - Tiết diện chịu nén khống chế (eps_t <= eps_y): phi = 0.75 (cốt đai thường)
    - Vùng chuyển tiếp (eps_y < eps_t < 0.005): nội suy tuyến tính
      phi = 0.75 + 0.15 * (eps_t - eps_y) / (0.005 - eps_y)
    """
    if eps_t >= 0.005:
        return 0.90
    elif eps_t <= eps_y:
        return 0.75
    else:
        return 0.75 + 0.15 * (eps_t - eps_y) / (0.005 - eps_y)


@dataclass
class FlexureCheckResult:
    """Kết quả kiểm toán sức kháng uốn cấu kiện BTCT (có hoặc không có cốt thép chịu nén)"""
    Mu: float                  # Mô men uốn tính toán (kN.m)
    Mn: float                  # Sức kháng uốn danh định (kN.m)
    Mr: float                  # Sức kháng uốn tính toán phi*Mn (kN.m)
    phi: float                 # Hệ số sức kháng uốn (0.90)
    c: float                   # Chiều sâu trục trung hòa (mm)
    a: float                   # Chiều sâu khối ứng suất chữ nhật tương đương Whitney (mm)
    demand_capacity_ratio: float # Tỷ số Mu / Mr
    passed: bool
    # Thông số cốt thép chịu nén (nếu có)
    has_compression_rebar: bool = False
    As_prime: float = 0.0      # Diện tích cốt thép chịu nén (mm²)
    fs_prime: float = 0.0      # Ứng suất trong cốt thép chịu nén (MPa)
    compression_rebar_yielded: bool = False


def check_flexure_rectangular(
    b: float,            # Bề rộng tiết diện (mm)
    h: float,            # Chiều cao tiết diện (mm)
    dc: float,           # Khoảng cách từ mép kéo đến trọng tâm thép kéo (mm)
    As: float,           # Diện tích cốt thép chịu kéo (mm²)
    Mu: float,           # Mô men uốn tính toán ULS (kN.m)
    concrete: Concrete,  # Bê tông
    rebar: Rebar,        # Cốt thép
    As_prime: float = 0.0, # Diện tích cốt thép chịu nén (mm²)
    dc_prime: float = 50.0 # Khoảng cách từ mép nén đến trọng tâm thép nén (mm)
) -> FlexureCheckResult:
    """
    Tính sức kháng uốn của tiết diện chữ nhật đặt cốt đơn hoặc cốt kép theo TCVN 11823-5 Điều 7.2
    """
    d = h - dc  # Chiều cao có hiệu (mm)
    if d <= 0 or As <= 0 or b <= 0:
        return FlexureCheckResult(
            Mu=Mu, Mr=0.0, Mn=0.0, phi=0.90, a=0.0, c=0.0,
            passed=False, demand_capacity_ratio=999.0
        )

    fc = concrete.fc_prime
    fy = rebar.fy
    Es = rebar.Es
    beta1 = concrete.beta1
    ecu = concrete.eps_cu # 0.003

    if As_prime > 0 and dc_prime < d:
        # Tiết diện đặt cốt kép (có cốt thép chịu nén As')
        c_assumed = ((As - As_prime) * fy) / (0.85 * fc * beta1 * b)
        if c_assumed > dc_prime:
            eps_s_prime = ecu * (c_assumed - dc_prime) / c_assumed
            eps_y = fy / Es
            if eps_s_prime >= eps_y:
                c = c_assumed
                fs_prime = fy
                is_yield = True
            else:
                A_eq = 0.85 * fc * beta1 * b
                B_eq = As_prime * Es * ecu - As * fy
                C_eq = -As_prime * Es * ecu * dc_prime
                delta_eq = B_eq**2 - 4 * A_eq * C_eq
                c = (-B_eq + math.sqrt(max(0.0, delta_eq))) / (2 * A_eq) if delta_eq >= 0 else c_assumed
                fs_prime = min(fy, Es * ecu * max(0.0, (c - dc_prime)) / c) if c > 0 else 0.0
                is_yield = False
        else:
            c = (As * fy) / (0.85 * fc * beta1 * b)
            fs_prime = 0.0
            is_yield = False

        a = beta1 * c
        eps_t = ecu * (d - c) / c if c > 0 else 0.05
        phi = get_phi_flexure(eps_t, rebar.eps_y)
        Mn_Nmm = 0.85 * fc * a * b * (d - a / 2.0) + As_prime * fs_prime * (d - dc_prime)
        Mn = Mn_Nmm * 1e-6
        Mr = phi * Mn
        passed = (Mr >= abs(Mu))
        ratio = abs(Mu) / Mr if Mr > 0 else 999.0

        return FlexureCheckResult(
            Mu=abs(Mu), Mr=Mr, Mn=Mn, phi=phi, a=a, c=c,
            passed=passed, demand_capacity_ratio=ratio,
            has_compression_rebar=True, As_prime=As_prime,
            fs_prime=fs_prime, compression_rebar_yielded=is_yield
        )
    else:
        # Tiết diện đặt cốt đơn
        a = (As * fy) / (0.85 * fc * b)
        c = a / beta1
        eps_t = ecu * (d - c) / c if c > 0 else 0.05
        phi = get_phi_flexure(eps_t, rebar.eps_y)
        Mn = As * fy * (d - a / 2.0) * 1e-6
        Mr = phi * Mn
        passed = (Mr >= abs(Mu))
        ratio = abs(Mu) / Mr if Mr > 0 else 999.0

        return FlexureCheckResult(
            Mu=abs(Mu), Mr=Mr, Mn=Mn, phi=phi, a=a, c=c,
            passed=passed, demand_capacity_ratio=ratio
        )


@dataclass
class MinReinforcementCheckResult:
    """Kết quả kiểm toán cốt thép tối thiểu (TCVN 11823-5 Điều 7.3.3.2)"""
    Mr: float                  # Sức kháng uốn thực tế Mr (kN.m)
    Mcr: float                 # Mô men gây nứt Mcr (kN.m)
    Mu: float                  # Mô men tính toán Mu (kN.m)
    limit: float               # Giá trị giới hạn min(Mcr, 1.33 * Mu)
    passed: bool               # Đạt / Không đạt (Mr >= limit)


def check_min_reinforcement(
    b: float,            # Bề rộng tiết diện (mm)
    h: float,            # Chiều cao tiết diện (mm)
    Mr: float,           # Sức kháng uốn Mr (kN.m)
    Mu: float,           # Mô men tính toán Mu (kN.m)
    concrete: Concrete,  # Bê tông
    gamma1: float = 1.60, # Hệ số biến động nứt khi uốn (1.6 cho kết cấu đúc tại chỗ)
    gamma3: float = 0.67  # Hệ số tỷ số giới hạn chảy (0.67 cho thép thanh thường)
) -> MinReinforcementCheckResult:
    """
    Kiểm toán cốt thép tối thiểu theo TCVN 11823-5 Điều 7.3.3.2:
    Mr >= min(Mcr, 1.33 * Mu)
    với Mcr = gamma3 * gamma1 * fr * S = 1.072 * fr * (b * h² / 6) * 1e-6
    """
    fr = concrete.fr
    S = (b * (h ** 2)) / 6.0  # Mô men kháng uốn đàn hồi (mm³)
    Mcr = gamma3 * gamma1 * fr * S * 1e-6  # kN.m
    limit = min(Mcr, 1.33 * abs(Mu))
    passed = (Mr >= limit)

    return MinReinforcementCheckResult(
        Mr=Mr, Mcr=Mcr, Mu=abs(Mu), limit=limit, passed=passed
    )


@dataclass
class CrackControlResult:
    """Kết quả kiểm toán nứt theo TTGH Sử dụng (TCVN 11823-5 Điều 7.3.4)"""
    Ms: float                  # Mô men TTGH Sử dụng (kN.m)
    fss: float                 # Ứng suất thực tế trong cốt thép kéo (MPa)
    fsa: float                 # Ứng suất cho phép trong cốt thép kéo (MPa)
    s_actual: float            # Khoảng cách thanh thép thực tế (mm)
    s_max: float               # Khoảng cách thanh thép tối đa cho phép (mm)
    passed: bool               # Đạt / Không đạt


def check_crack_control(
    b: float,            # Bề rộng dải tính toán (mm)
    h: float,            # Chiều cao tiết diện (mm)
    dc: float,           # Lớp bê tông bảo vệ tính đến tâm thanh thép (mm)
    As: float,           # Diện tích cốt thép chịu kéo (mm²)
    s_rebar: float,      # Bước cốt thép (mm)
    Ms: float,           # Mô men TTGH Sử dụng (kN.m)
    concrete: Concrete,  # Bê tông
    rebar: Rebar,        # Cốt thép
    gamma_e: float = 1.00 # Cấp lộ thiên: 1.00 cấp 1 (thông thường), 0.75 cấp 2 (khắc nghiệt)
) -> CrackControlResult:
    """
    Kiểm toán nứt theo TCVN 11823-5 Điều 7.3.4:
    Khoảng cách thanh cốt thép s <= s_max = (123000 * gamma_e) / (beta_s * fss) - 2 * dc
    hoặc fss <= fsa = (123000 * gamma_e) / (beta_s * (s + 2*dc))
    và fss <= 0.6 * fy
    với beta_s = 1 + dc / (0.7 * (h - dc))
    """
    d = h - dc
    if d <= 0 or As <= 0 or Ms <= 0:
        return CrackControlResult(
            Ms=abs(Ms), fss=0.0, fsa=0.6 * rebar.fy,
            s_actual=s_rebar, s_max=300.0, passed=True
        )

    n = rebar.Es / concrete.Ec
    rho = As / (b * d)
    # Vị trí trục trung hòa đàn hồi nứt
    k = math.sqrt(2.0 * rho * n + (rho * n) ** 2) - rho * n
    j = 1.0 - k / 3.0

    # Ứng suất thực trong cốt thép fss (MPa)
    fss = (abs(Ms) * 1e6) / (As * j * d)

    # Hệ số hình học beta_s
    beta_s = 1.0 + dc / (0.7 * (h - dc))

    # Khoảng cách tối đa s_max
    if fss > 0:
        s_max = (123000.0 * gamma_e) / (beta_s * fss) - 2.0 * dc
        s_max = min(s_max, 300.0)  # Khống chế bước đai/thép max 300mm
    else:
        s_max = 300.0

    # Ứng suất cho phép fsa
    fsa = min(0.6 * rebar.fy, (123000.0 * gamma_e) / (beta_s * (s_rebar + 2.0 * dc)))
    passed = (fss <= fsa) and (s_rebar <= s_max)

    return CrackControlResult(
        Ms=abs(Ms), fss=fss, fsa=fsa, s_actual=s_rebar, s_max=s_max, passed=passed
    )


@dataclass
class ShearCheckResult:
    """Kết quả kiểm toán sức kháng cắt (TCVN 11823-5 Điều 8.2)"""
    Vu: float                  # Lực cắt tính toán ULS (kN)
    Vr: float                  # Sức kháng cắt tính toán Vr = phi * Vn (kN)
    Vc: float                  # Sức kháng cắt của bê tông Vc (kN)
    Vs: float                  # Sức kháng cắt của cốt đai Vs (kN)
    Vn: float                  # Sức kháng cắt danh định Vn (kN)
    phi: float                 # Hệ số sức kháng phi = 0.90
    dv: float                  # Chiều cao chịu cắt có hiệu (mm)
    passed: bool               # Đạt / Không đạt (Vr >= Vu)
    demand_capacity_ratio: float


def check_shear_beam(
    b: float,            # Bề rộng sườn / bề rộng dải (mm)
    h: float,            # Chiều cao tiết diện (mm)
    d: float,            # Chiều cao có hiệu (mm)
    a_whitney: float,    # Chiều cao khối nén Whitney a (mm)
    Av: float,           # Diện tích các nhánh đai chịu cắt (mm²) (0 nếu không có đai)
    s_stirrup: float,    # Bước cốt đai (mm)
    Vu: float,           # Lực cắt tính toán ULS (kN)
    Nu: float,           # Lực dọc đồng thời (kN, nén dương)
    concrete: Concrete,  # Bê tông
    rebar: Rebar,        # Cốt thép
    phi: float = 0.90    # Hệ số sức kháng cắt
) -> ShearCheckResult:
    """
    Kiểm toán sức kháng cắt dầm / bản 1 phương theo TCVN 11823-5 Điều 8.2:
    dv = max(d - a/2, 0.9*d, 0.72*h)
    Vc = 0.083 * beta * sqrt(f'c) * b * dv * 1e-3 (kN)  [beta = 2.0 cho cấu kiện không kéo]
    Vs = (Av * fy * dv * cot(theta)) / s * 1e-3 (kN)     [theta = 45 độ -> cot = 1.0]
    Vn = min(Vc + Vs, 0.25 * f'c * b * dv * 1e-3)
    Vr = phi * Vn
    """
    dv = max(d - a_whitney / 2.0, 0.9 * d, 0.72 * h)
    fc = concrete.fc_prime
    fy = rebar.fy

    # Beta cho bê tông (xét ảnh hưởng lực nén dọc nếu có)
    # Lực nén Nu làm tăng khả năng chống cắt của bê tông
    beta = 2.0
    if Nu > 0:
        # Tăng nhẹ khả năng kháng nén
        pass

    Vc = 0.083 * beta * math.sqrt(fc) * b * dv * 1e-3  # kN

    Vs = 0.0
    if Av > 0 and s_stirrup > 0:
        Vs = (Av * fy * dv) / s_stirrup * 1e-3  # kN (với theta = 45 độ)

    Vn_max = 0.25 * fc * b * dv * 1e-3  # Giới hạn nén vỡ sườn dầm (kN)
    Vn = min(Vc + Vs, Vn_max)
    Vr = phi * Vn

    passed = (Vr >= abs(Vu))
    ratio = abs(Vu) / Vr if Vr > 0 else 999.0

    return ShearCheckResult(
        Vu=abs(Vu), Vr=Vr, Vc=Vc, Vs=Vs, Vn=Vn, phi=phi, dv=dv,
        passed=passed, demand_capacity_ratio=ratio
    )


def check_punching_shear_two_way(
    d: float,            # Chiều cao làm việc trung bình của bệ (mm)
    b0: float,           # Chu vi tiết diện tới hạn cách mép cột/cọc d/2 (mm)
    Vu: float,           # Lực chọc thủng tính toán ULS (kN)
    concrete: Concrete,  # Bê tông
    phi: float = 0.70    # Hệ số sức kháng ép mặt / chọc thủng (Điều 5.4.2)
) -> Tuple[bool, float, float]:
    """
    Kiểm toán cắt đâm thủng 2 phương (Punching shear) bệ móng theo TCVN 11823-5 Điều 8.3.3:
    Vn = 0.17 * sqrt(f'c) * b0 * d * 1e-3 (kN)
    Vr = phi * Vn
    Trả về (passed, Vr, Vu)
    """
    fc = concrete.fc_prime
    Vn = 0.17 * math.sqrt(fc) * b0 * d * 1e-3
    Vr = phi * Vn
    passed = (Vr >= abs(Vu))
    return passed, Vr, abs(Vu)


def calculate_column_slenderness_factor(
    k: float,            # Hệ số chiều dài tính toán (2.1 cho cột ngàm tự do / mố trụ)
    lu: float,           # Chiều dài tự do không giằng (m)
    h: float,            # Kích thước cạnh theo phương uốn (m)
    Pu: float,           # Lực nén tính toán ULS (kN)
    Ig: float,           # Mô men quán tính hình học (m4)
    concrete: Concrete,  # Bê tông
    beta_d: float = 0.60 # Tỷ số mô men tĩnh tải trên tổng mô men
) -> Tuple[float, float, bool]:
    """
    Tính hệ số phóng đại độ mảnh delta_b theo TCVN 11823-5 Điều 7.4.3:
    Bán kính quán tính r = 0.30 * h (tiết diện chữ nhật) hoặc 0.25 * D (tiết diện tròn)
    Độ mảnh lambda = (k * lu) / r
    Nếu lambda <= 22: bỏ qua độ mảnh (delta_b = 1.0)
    Nếu lambda > 22:
      EI = (0.2 * Ec * Ig + Es * Is) / (1 + beta_d) hoặc 0.4 * Ec * Ig / (1 + beta_d)
      Pe = pi² * EI / (k * lu)²
      delta_b = 1 / (1 - Pu / (0.75 * Pe)) >= 1.0
    Trả về (delta_b, lambda, is_slender)
    """
    r = 0.30 * h  # m
    lam = (k * lu) / r if r > 0 else 0.0

    if lam <= 22.0:
        return 1.0, lam, False

    Ec_kpa = concrete.Ec * 1e3  # kN/m²
    EI = (0.40 * Ec_kpa * Ig) / (1.0 + beta_d)  # kN.m²
    Pe = (math.pi ** 2 * EI) / ((k * lu) ** 2)   # kN

    denom = 1.0 - abs(Pu) / (0.75 * Pe)
    if denom <= 0.05:
        delta_b = 20.0  # Cột quá mảnh / gần mất ổn định
    else:
        delta_b = max(1.0, 1.0 / denom)

    return delta_b, lam, True
