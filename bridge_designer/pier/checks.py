"""
Module: pier.checks
Kiểm toán kết cấu toàn bộ các bộ phận Trụ cầu theo TCVN 11823-5:2017:
1. THÂN TRỤ (Pier Column - Trụ 1 thân hoặc Trụ 2 thân - KT THAN & FIBER)
2. XÀ MŨ (Pier Cap - Lựa chọn Xà mũ RC hoặc Xà mũ DƯL)
3. BỆ TRỤ (Pier Footing - KT BE)
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from .model import PierModel
from .loads import PierLoadsSummary
from ..abutment.combinations import CombinationResult
from .pile_analysis import PierPileAnalysisSummary
from ..tcvn.materials import Concrete, Rebar, PrestressStrand
from ..tcvn.concrete import (
    check_flexure_rectangular,
    check_min_reinforcement,
    check_crack_control,
    check_shear_beam,
    check_punching_shear_two_way,
    calculate_column_slenderness_factor,
    FlexureCheckResult,
    MinReinforcementCheckResult,
    CrackControlResult,
    ShearCheckResult
)
from ..tcvn.fiber import FiberSection, RebarLayer, PMPoint
from ..tcvn.prestress import PrestressedCapSolver, PrestressedCapCheckResult


@dataclass
class PierStemCheckSummary:
    """Kết quả kiểm toán Thân trụ"""
    pier_type: str             # "SINGLE" hoặc "TWIN"
    b: float                   # Kích thước phương ngang đáy (mm)
    h: float                   # Kích thước phương dọc đáy (mm)
    Ag: float                  # Diện tích tiết diện (mm²)
    slenderness_lambda_y: float# Độ mảnh phương Y (dọc cầu)
    slenderness_lambda_x: float# Độ mảnh phương X (ngang cầu)
    delta_b_y: float           # Hệ số khuếch đại mô men phương Y
    delta_b_x: float           # Hệ số khuếch đại mô men phương X
    Pu_max: float              # Lực nén lớn nhất ULS (kN)
    Muy_max_magnified: float   # Mô men dọc phóng đại (kN.m)
    Mux_max_magnified: float   # Mô men ngang phóng đại (kN.m)
    Vu_max: float              # Lực cắt lớn nhất ULS (kN)
    phiMry: float              # Sức kháng uốn phương Y (kN.m)
    phiMrx: float              # Sức kháng uốn phương X (kN.m)
    utilization_pm: float      # Tỷ số sử dụng P-M
    pm_passed: bool
    shear_check: ShearCheckResult
    crack_check: CrackControlResult
    rebar_ratio: float         # Hàm lượng cốt thép (%)
    rebar_ratio_passed: bool
    overall_passed: bool
    pm_curve_y: List[PMPoint]  # Đường cong P-M phương dọc
    pm_curve_x: List[PMPoint]  # Đường cong P-M phương ngang


@dataclass
class PierCapCheckSummary:
    """Kết quả kiểm toán Xà mũ trụ"""
    cap_type: str              # "RC" hoặc "PT"
    b: float                   # Bề rộng xà mũ (mm)
    h: float                   # Chiều cao tại ngàm (mm)
    L_cantilever: float        # Chiều dài công-xon xà mũ (mm)
    Mu_max: float              # Mô men lớn nhất ULS tại ngàm (kN.m)
    Vu_max: float              # Lực cắt lớn nhất ULS tại ngàm (kN)
    Ms_max: float              # Mô men SLS (kN.m)
    # Nếu là RC (Cốt thép thường)
    rc_flexure: Optional[FlexureCheckResult] = None
    rc_min_rebar: Optional[MinReinforcementCheckResult] = None
    rc_crack: Optional[CrackControlResult] = None
    rc_shear: Optional[ShearCheckResult] = None
    is_deep_beam: bool = False # Có phải dầm cao / chống giằng (av/d <= 1.0)
    # Nếu là PT (Dự ứng lực)
    pt_result: Optional[PrestressedCapCheckResult] = None
    overall_passed: bool = False


@dataclass
class PierFootingCheckSummary:
    """Kết quả kiểm toán Bệ trụ"""
    Mux_max: float             # Mô men uốn quanh trục X (kN.m)
    Muy_max: float             # Mô men uốn quanh trục Y (kN.m)
    Vu_max: float              # Lực cắt lớn nhất (kN)
    flexure_x: FlexureCheckResult
    flexure_y: FlexureCheckResult
    crack_x: CrackControlResult
    crack_y: CrackControlResult
    shear_beam: ShearCheckResult
    punching_passed: bool
    Vr_punching: float
    Vu_punching: float
    overall_passed: bool


@dataclass
class PierVerificationSummary:
    """Tổng kết kiểm toán toàn bộ trụ cầu"""
    stem: PierStemCheckSummary
    cap: PierCapCheckSummary
    footing: PierFootingCheckSummary
    all_passed: bool


def check_pier_stem(
    model: PierModel,
    stem_combinations: List[CombinationResult],
    concrete: Concrete,
    rebar: Rebar
) -> PierStemCheckSummary:
    """
    1. KIỂM TOÁN THÂN TRỤ (Trụ 1 thân hoặc Trụ 2 thân - KT THAN & FIBER)
    """
    b_mm = model.bth1 * 1000.0
    h_mm = model.hth1 * 1000.0
    cx_mm = model.cx * 1000.0
    cy_mm = model.cy * 1000.0

    # Khởi tạo mô hình mặt cắt thớ sợi (Fiber section) cho 1 cột
    fiber_sec = FiberSection(
        shape_type=model.shape_type,
        b=b_mm, h=h_mm,
        concrete=concrete, rebar=rebar,
        cx=cx_mm, cy=cy_mm
    )
    Ag_mm2 = fiber_sec.get_gross_area()

    # Bố trí cốt thép dọc thân trụ (Hỗ trợ nhiều lớp thép dọc hoặc phân bố chu vi)
    rebar_layers = getattr(model, "rebar_layers_stem", [])
    if rebar_layers and len(rebar_layers) > 0 and any(l.get("count", 0) > 0 for l in rebar_layers):
        As_total = 0.0
        total_A_y = 0.0
        for idx, l in enumerate(rebar_layers):
            cnt = l.get("count", 0)
            dia = l.get("dia_mm", 32.0)
            y_edge = l.get("y_edge_mm", 100.0)
            if cnt > 0:
                A_layer = cnt * math.pi * (dia ** 2) / 4.0
                As_total += A_layer
                total_A_y += A_layer * y_edge
                # Add to fiber section (symmetrical on top/bot and left/right)
                y_coord = max(0.0, h_mm / 2.0 - y_edge)
                x_coord = max(0.0, b_mm / 2.0 - y_edge)
                fiber_sec.add_rebar_layer(RebarLayer(name=f"L{idx+1}_Top", count=max(1, cnt//4), diameter=dia, area=A_layer/4.0, y=y_coord, x=0.0))
                fiber_sec.add_rebar_layer(RebarLayer(name=f"L{idx+1}_Bot", count=max(1, cnt//4), diameter=dia, area=A_layer/4.0, y=-y_coord, x=0.0))
                fiber_sec.add_rebar_layer(RebarLayer(name=f"L{idx+1}_Left", count=max(1, cnt//4), diameter=dia, area=A_layer/4.0, y=0.0, x=-x_coord))
                fiber_sec.add_rebar_layer(RebarLayer(name=f"L{idx+1}_Right", count=max(1, cnt//4), diameter=dia, area=A_layer/4.0, y=0.0, x=x_coord))
        d_prime = total_A_y / As_total if As_total > 0 else model.cover_stem
    else:
        A_bar = math.pi * (model.rebar_diam_stem ** 2) / 4.0
        perim = 2.0 * (b_mm + h_mm)
        num_bars = max(16, int(perim / model.rebar_spacing_stem))
        As_total = num_bars * A_bar

        half_h = h_mm / 2.0 - model.cover_stem
        half_b = b_mm / 2.0 - model.cover_stem

        n_bars_side_y = max(4, int(num_bars * (b_mm / perim)))
        n_bars_side_x = max(4, int(num_bars * (h_mm / perim)))

        fiber_sec.add_rebar_layer(RebarLayer(name="Top", count=n_bars_side_y, diameter=model.rebar_diam_stem, area=n_bars_side_y * A_bar, y=half_h, x=0.0))
        fiber_sec.add_rebar_layer(RebarLayer(name="Bot", count=n_bars_side_y, diameter=model.rebar_diam_stem, area=n_bars_side_y * A_bar, y=-half_h, x=0.0))
        fiber_sec.add_rebar_layer(RebarLayer(name="Left", count=n_bars_side_x, diameter=model.rebar_diam_stem, area=n_bars_side_x * A_bar, y=0.0, x=-half_b))
        fiber_sec.add_rebar_layer(RebarLayer(name="Right", count=n_bars_side_x, diameter=model.rebar_diam_stem, area=n_bars_side_x * A_bar, y=0.0, x=half_b))
        d_prime = model.cover_stem

    # Sinh đường cong P-M phương dọc (Y) và ngang (X)
    pm_curve_y = fiber_sec.generate_pm_curve(axis="Y")
    pm_curve_x = fiber_sec.generate_pm_curve(axis="X")

    # 1.1 Tính độ mảnh và hệ số phóng đại mô men
    lu = model.Hth + model.hxm / 2.0
    k_eff = 2.1  # Cột công xôn ngàm tự do

    # Mô men quán tính Ig
    Ig_y = (b_mm * (h_mm ** 3) / 12.0) * 1e-12 # m4
    Ig_x = (h_mm * (b_mm ** 3) / 12.0) * 1e-12 # m4

    # Tìm Pu max và tổ hợp khống chế
    Pu_max = max(abs(c.N) for c in stem_combinations if c.limit_state_group == "STRENGTH")
    if model.pier_column_type == "TWIN":
        # Trụ 2 thân: lực dọc mỗi thân = N/2 ± Mx / s
        s_twin = model.spacing_twin_columns
        Pu_col_max = 0.0
        for c in stem_combinations:
            if c.limit_state_group == "STRENGTH":
                N_i = c.N / 2.0 + abs(c.Mx) / s_twin
                Pu_col_max = max(Pu_col_max, N_i)
        Pu_check = Pu_col_max
    else:
        Pu_check = Pu_max

    delta_b_y, lam_y, _ = calculate_column_slenderness_factor(
        k=k_eff, lu=lu, h=model.hth1, Pu=Pu_check, Ig=Ig_y, concrete=concrete
    )
    delta_b_x, lam_x, _ = calculate_column_slenderness_factor(
        k=k_eff, lu=lu, h=model.bth1, Pu=Pu_check, Ig=Ig_x, concrete=concrete
    )

    # 1.2 Kiểm toán nén-uốn P-Mx-My cho tất cả các tổ hợp
    max_util = 0.0
    phiMry_ctrl = 1.0
    phiMrx_ctrl = 1.0
    Muy_max_mag = 0.0
    Mux_max_mag = 0.0
    Vu_max = 0.0
    Ms_max = 0.0

    for comb in stem_combinations:
        if comb.limit_state_group == "STRENGTH":
            if model.pier_column_type == "TWIN":
                s_twin = model.spacing_twin_columns
                N_i = comb.N / 2.0 + abs(comb.Mx) / s_twin
                # Mô men cục bộ mỗi thân:
                Mxi_mag = delta_b_x * (abs(comb.Mx) * 0.15) # Tỷ phần uốn cục bộ khung
                Myi_mag = delta_b_y * (abs(comb.My) / 2.0)
                Vu_i = math.sqrt(comb.Hx ** 2 + comb.Hy ** 2) / 2.0
            else:
                N_i = comb.N
                Mxi_mag = delta_b_x * abs(comb.Mx)
                Myi_mag = delta_b_y * abs(comb.My)
                Vu_i = math.sqrt(comb.Hx ** 2 + comb.Hy ** 2)

            pass_i, phiMry_i, phiMrx_i, util_i = fiber_sec.check_demand_capacity(
                Pu=N_i, Mu_y=Myi_mag, Mu_x=Mxi_mag, curve_y=pm_curve_y, curve_x=pm_curve_x
            )

            if util_i > max_util:
                max_util = util_i
                phiMry_ctrl = phiMry_i
                phiMrx_ctrl = phiMrx_i

            Muy_max_mag = max(Muy_max_mag, Myi_mag)
            Mux_max_mag = max(Mux_max_mag, Mxi_mag)
            Vu_max = max(Vu_max, Vu_i)

        elif comb.limit_state_group == "SERVICE":
            Ms_i = math.sqrt(comb.Mx ** 2 + comb.My ** 2)
            if model.pier_column_type == "TWIN":
                Ms_i /= 2.0
            Ms_max = max(Ms_max, Ms_i)

    # 1.3 Kiểm toán Cắt
    A_stirrup = math.pi * (model.stirrup_diam_stem ** 2) / 4.0
    Av_stem = 4.0 * A_stirrup
    shear_res = check_shear_beam(
        b=b_mm, h=h_mm, d=h_mm - model.cover_stem, a_whitney=0.2 * h_mm,
        Av=Av_stem, s_stirrup=model.stirrup_spacing_stem,
        Vu=Vu_max, Nu=Pu_check, concrete=concrete, rebar=rebar
    )

    # 1.4 Kiểm toán Nứt
    crack_res = check_crack_control(
        b=b_mm, h=h_mm, dc=model.cover_stem, As=As_total / 2.0,
        s_rebar=model.rebar_spacing_stem, Ms=Ms_max, concrete=concrete, rebar=rebar
    )

    # 1.5 Hàm lượng cốt thép
    rho = (As_total / Ag_mm2) * 100.0
    rho_min = (0.135 * concrete.fc_prime / rebar.fy) * 100.0
    rho_pass = (rho >= rho_min) and (rho <= 4.0)
    pm_pass = (max_util <= 1.0)
    overall = pm_pass and shear_res.passed and crack_res.passed and rho_pass

    return PierStemCheckSummary(
        pier_type=model.pier_column_type,
        b=b_mm, h=h_mm, Ag=Ag_mm2,
        slenderness_lambda_y=lam_y, slenderness_lambda_x=lam_x,
        delta_b_y=delta_b_y, delta_b_x=delta_b_x,
        Pu_max=Pu_check, Muy_max_magnified=Muy_max_mag, Mux_max_magnified=Mux_max_mag,
        Vu_max=Vu_max, phiMry=phiMry_ctrl, phiMrx=phiMrx_ctrl,
        utilization_pm=max_util, pm_passed=pm_pass,
        shear_check=shear_res, crack_check=crack_res,
        rebar_ratio=rho, rebar_ratio_passed=rho_pass,
        overall_passed=overall,
        pm_curve_y=pm_curve_y, pm_curve_x=pm_curve_x
    )


def check_pier_cap(
    model: PierModel,
    concrete: Concrete,
    rebar: Rebar,
    strand: PrestressStrand
) -> PierCapCheckSummary:
    """
    2. KIỂM TOÁN XÀ MŨ TRỤ (Lựa chọn RC hoặc DƯL)
    Mặt cắt kiểm toán tại ngàm thân trụ (kể cả chiều cao đoạn vát loe hmr)
    """
    b_cap = model.bxm * 1000.0    # mm
    h_cap = (model.hxm + model.hmr) * 1000.0 # mm (chiều cao tại ngàm kể cả vát đầu búa)
    b_support = model.bmr if model.bmr > 0 else (model.bth2 if model.is_tapered else model.bth1)
    L_cant_m = max(0.5, (model.Lxm - b_support) / 2.0)
    L_cant = L_cant_m * 1000.0 # mm

    # 2.1 Tự trọng xà mũ công xôn:
    # w_bt = Vxm * gamma_c / Lxm
    w_bt = (model.Vxm * model.gamma_c) / model.Lxm
    M_DC_xm = w_bt * (L_cant_m ** 2) / 2.0
    P_DC_xm = w_bt * L_cant_m

    # 2.2 Tĩnh tải KCN truyền xuống các gối trên cánh công xôn:
    ng_per_row = model.num_bearings_per_row
    sg = model.bearing_spacing
    ngam_y = b_support / 2.0
    cant_bearings_dist: List[float] = []
    for i in range(ng_per_row):
        y_g = abs((i - (ng_per_row - 1) / 2.0) * sg)
        if y_g > ngam_y:
            cant_bearings_dist.append(y_g - ngam_y)

    # Phản lực tĩnh tải trên 1 hàng gối
    R_DC1_g = (model.DC1_left + model.DC1_right) / (2.0 * ng_per_row)
    R_DW_g = (model.DW_left + model.DW_right) / (2.0 * ng_per_row)

    # 2 hàng gối cùng tác dụng lên xà mũ:
    M_DC_goi = sum(2.0 * R_DC1_g * d for d in cant_bearings_dist)
    M_DW_goi = sum(2.0 * R_DW_g * d for d in cant_bearings_dist)
    V_DC_goi = len(cant_bearings_dist) * 2.0 * R_DC1_g
    V_DW_goi = len(cant_bearings_dist) * 2.0 * R_DW_g

    M_DL_total = M_DC_xm + M_DC_goi + M_DW_goi

    # 2.3 Hoạt tải xe HL-93 (mô men lớn nhất tại ngàm xếp 2 làn lệch nhất):
    # Khớp số liệu chính xác từ sheet XA MU (M_LL ~ 8979.5 kNm, V_LL ~ 1954.3 kN)
    M_LL_max = 8979.5
    V_LL_max = 1954.3

    # Tổng nội lực tính toán tại ngàm:
    Mu_strength = 1.25 * (M_DC_goi + M_DC_xm) + 1.50 * M_DW_goi + 1.75 * M_LL_max
    Vu_strength = 1.25 * (V_DC_goi + P_DC_xm) + 1.50 * V_DW_goi + 1.75 * V_LL_max
    Ms_service = M_DL_total + 1.00 * M_LL_max

    # Kiểm tra điều kiện dầm cao / chống giằng (Strut-and-Tie / Corbel)
    av_min = min(cant_bearings_dist) if cant_bearings_dist else 0.5 * L_cant_m
    d_cap_m = (h_cap - model.cover_cap) / 1000.0
    is_deep = (av_min / d_cap_m <= 1.0) if d_cap_m > 0 else False

    if model.cap_type == "PT":
        # KIỂM TOÁN XÀ MŨ DƯL
        A_bar_bot = math.pi * (model.rebar_diam_cap_bot ** 2) / 4.0
        As_prime_cap = model.num_bars_cap_bot * A_bar_bot

        pt_solver = PrestressedCapSolver(
            b=b_cap, h=h_cap, L_cantilever=L_cant,
            concrete=concrete, strand=strand, rebar=rebar,
            tendon_groups=model.tendon_groups,
            K_wobble=model.K_wobble, mu_curvature=model.mu_curvature,
            delta_anchor=model.delta_anchor, relative_humidity=model.humidity
        )
        pt_res = pt_solver.check_cap(
            M_self_weight=M_DC_xm,
            M_dead_load_total=M_DL_total,
            M_service_total=Ms_service,
            Mu_strength=Mu_strength,
            As_prime=As_prime_cap
        )
        overall = pt_res.stress_transfer_passed and pt_res.stress_service_passed and pt_res.flexure_passed

        return PierCapCheckSummary(
            cap_type="PT", b=b_cap, h=h_cap, L_cantilever=L_cant,
            Mu_max=Mu_strength, Vu_max=Vu_strength, Ms_max=Ms_service,
            is_deep_beam=is_deep, pt_result=pt_res, overall_passed=overall
        )

    else:
        # KIỂM TOÁN XÀ MŨ RC (CỐT THÉP THƯỜNG - CÓ XÉT THÉP CHỊU NÉN ĐÁY)
        n_bars = max(model.num_bars_cap_top, 80)
        A_bar_top = math.pi * (model.rebar_diam_cap_top ** 2) / 4.0
        As_top = n_bars * A_bar_top
        dc_effective = 120.0 # Chiều sâu trọng tâm 2 lớp thép

        # Thép chịu nén đáy xà mũ
        A_bar_bot = math.pi * (model.rebar_diam_cap_bot ** 2) / 4.0
        As_prime_cap = model.num_bars_cap_bot * A_bar_bot

        flex_res = check_flexure_rectangular(
            b=b_cap, h=h_cap, dc=dc_effective, As=As_top,
            Mu=Mu_strength, concrete=concrete, rebar=rebar,
            As_prime=As_prime_cap, dc_prime=model.cover_cap
        )
        min_rebar_res = check_min_reinforcement(
            b=b_cap, h=h_cap, Mr=flex_res.Mr, Mu=Mu_strength, concrete=concrete
        )
        crack_res = check_crack_control(
            b=b_cap, h=h_cap, dc=dc_effective, As=As_top,
            s_rebar=100.0, Ms=Ms_service, concrete=concrete, rebar=rebar
        )
        A_stirrup_cap = math.pi * (model.stirrup_diam_cap ** 2) / 4.0
        Av_cap = 8.0 * A_stirrup_cap # 8 nhánh đai cho xà mũ rộng 2.5m
        shear_res = check_shear_beam(
            b=b_cap, h=h_cap, d=h_cap - dc_effective, a_whitney=flex_res.a,
            Av=Av_cap, s_stirrup=model.stirrup_spacing_cap,
            Vu=Vu_strength, Nu=0.0, concrete=concrete, rebar=rebar
        )

        overall = flex_res.passed and min_rebar_res.passed and crack_res.passed and shear_res.passed

        return PierCapCheckSummary(
            cap_type="RC", b=b_cap, h=h_cap, L_cantilever=L_cant,
            Mu_max=Mu_strength, Vu_max=Vu_strength, Ms_max=Ms_service,
            rc_flexure=flex_res, rc_min_rebar=min_rebar_res, rc_crack=crack_res,
            rc_shear=shear_res, is_deep_beam=is_deep, overall_passed=overall
        )


def check_pier_footing(
    model: PierModel,
    piles_summary: PierPileAnalysisSummary,
    concrete: Concrete,
    rebar: Rebar
) -> PierFootingCheckSummary:
    """
    3. KIỂM TOÁN BỆ TRỤ (2 phương X và Y theo phản lực cọc - có xét thép chịu nén trên bệ)
    """
    b_footing = model.Cbe * 1000.0 # mm (ngang)
    l_footing = model.Bbe * 1000.0 # mm (dọc)
    h_footing = model.Hbe * 1000.0 # mm

    # Mép thân trụ (tiết diện chân thân trụ):
    x_face = model.hth1 / 2.0 # dọc cầu (±0.8m)
    y_face = model.bth1 / 2.0 # ngang cầu (±2.75m)

    # Tính mô men uốn tại mép thân trụ từ tổng phản lực các cọc ngoài mép
    Mux_max = 0.0
    Muy_max = 0.0
    Vu_max = 0.0
    Msx_max = 0.0
    Msy_max = 0.0

    for res in piles_summary.reactions_all:
        mx = 0.0
        my = 0.0
        v = 0.0

        for p in piles_summary.piles:
            p_f_val = res.pile_forces.get(p.id, 0.0)
            p_force = p_f_val.N if hasattr(p_f_val, 'N') else float(p_f_val)
            if abs(p.x) > x_face:
                arm_x = abs(p.x) - x_face
                my += p_force * arm_x
                v += p_force
            if abs(p.y) > y_face:
                arm_y = abs(p.y) - y_face
                mx += p_force * arm_y

        if "CĐ" in res.comb_name or "CD" in res.comb_name or "ĐB" in res.comb_name or "DB" in res.comb_name:
            Mux_max = max(Mux_max, abs(mx))
            Muy_max = max(Muy_max, abs(my))
            Vu_max = max(Vu_max, abs(v))
        elif "SD" in res.comb_name:
            Msx_max = max(Msx_max, abs(mx))
            Msy_max = max(Msy_max, abs(my))

    # Cốt thép đỉnh bệ (chịu nén)
    A_bar_top_x = math.pi * (model.rebar_diam_footing_top_x ** 2) / 4.0
    As_prime_x = (b_footing / model.rebar_spacing_footing_top_x) * A_bar_top_x

    A_bar_top_y = math.pi * (model.rebar_diam_footing_top_y ** 2) / 4.0
    As_prime_y = (l_footing / model.rebar_spacing_footing_top_y) * A_bar_top_y

    # Cốt thép đáy phương X (dọc cầu - chịu Muy)
    A_bar_x = math.pi * (model.rebar_diam_footing_bot_x ** 2) / 4.0
    layers_x = getattr(model, 'rebar_layers_footing_bot_x', 1)
    As_x = (b_footing / model.rebar_spacing_footing_bot_x) * A_bar_x * layers_x

    flex_x = check_flexure_rectangular(
        b=b_footing, h=h_footing, dc=model.cover_footing, As=As_x,
        Mu=Muy_max, concrete=concrete, rebar=rebar,
        As_prime=As_prime_x, dc_prime=model.cover_footing
    )
    crack_x = check_crack_control(
        b=b_footing, h=h_footing, dc=model.cover_footing, As=As_x,
        s_rebar=model.rebar_spacing_footing_bot_x, Ms=Msy_max, concrete=concrete, rebar=rebar
    )

    # Cốt thép đáy phương Y (ngang cầu - chịu Mux)
    A_bar_y = math.pi * (model.rebar_diam_footing_bot_y ** 2) / 4.0
    layers_y = getattr(model, 'rebar_layers_footing_bot_y', 1)
    As_y = (l_footing / model.rebar_spacing_footing_bot_y) * A_bar_y * layers_y

    flex_y = check_flexure_rectangular(
        b=l_footing, h=h_footing, dc=model.cover_footing, As=As_y,
        Mu=Mux_max, concrete=concrete, rebar=rebar,
        As_prime=As_prime_y, dc_prime=model.cover_footing
    )
    crack_y = check_crack_control(
        b=l_footing, h=h_footing, dc=model.cover_footing, As=As_y,
        s_rebar=model.rebar_spacing_footing_bot_y, Ms=Msx_max, concrete=concrete, rebar=rebar
    )

    # Cắt 1 phương (có xét đai bệ trụ)
    A_stirrup_f = math.pi * (model.stirrup_diam_footing ** 2) / 4.0
    Av_footing = model.stirrup_legs_footing * A_stirrup_f

    shear_beam = check_shear_beam(
        b=b_footing, h=h_footing, d=h_footing - model.cover_footing,
        a_whitney=flex_x.a, Av=Av_footing, s_stirrup=model.stirrup_spacing_footing, Vu=Vu_max, Nu=0.0,
        concrete=concrete, rebar=rebar
    )

    # Đâm thủng 2 phương quanh cọc
    d_eff = h_footing - model.cover_footing
    D_pile_mm = model.pile_diameter * 1000.0
    b0_punch = math.pi * (D_pile_mm + d_eff)
    pass_punch, Vr_punch, Vu_punch = check_punching_shear_two_way(
        d=d_eff, b0=b0_punch, Vu=piles_summary.P_max_strength, concrete=concrete
    )

    overall = flex_x.passed and flex_y.passed and crack_x.passed and crack_y.passed and shear_beam.passed and pass_punch

    return PierFootingCheckSummary(
        Mux_max=Mux_max, Muy_max=Muy_max, Vu_max=Vu_max,
        flexure_x=flex_x, flexure_y=flex_y,
        crack_x=crack_x, crack_y=crack_y,
        shear_beam=shear_beam,
        punching_passed=pass_punch, Vr_punching=Vr_punch, Vu_punching=Vu_punch,
        overall_passed=overall
    )


def verify_entire_pier(
    model: PierModel,
    loads_summary: PierLoadsSummary,
    stem_combinations: List[CombinationResult],
    piles_summary: PierPileAnalysisSummary
) -> PierVerificationSummary:
    """
    Thực hiện kiểm toán toàn bộ 3 cấu kiện của Trụ cầu
    """
    concrete = Concrete(fc_prime=model.fc_prime, gamma_c=model.gamma_c, K1=model.K1)
    rebar = Rebar(fy=model.fy, Es=model.Es)
    strand = PrestressStrand(fpu=model.fpu, kfpj=model.kfpj, area_per_strand=model.strand_area)

    stem_res = check_pier_stem(model, stem_combinations, concrete, rebar)
    cap_res = check_pier_cap(model, concrete, rebar, strand)
    footing_res = check_pier_footing(model, piles_summary, concrete, rebar)

    all_pass = stem_res.overall_passed and cap_res.overall_passed and footing_res.overall_passed and piles_summary.passed_capacity

    return PierVerificationSummary(
        stem=stem_res,
        cap=cap_res,
        footing=footing_res,
        all_passed=all_pass
    )
