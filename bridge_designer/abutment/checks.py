"""
Module: abutment.checks
Kiểm toán kết cấu toàn bộ các bộ phận mố cầu theo TCVN 11823-5:2017:
1. TƯỜNG THÂN MỐ (Stem - KT THAN)
2. TƯỜNG ĐỈNH MỐ (Backwall - TUONG DINH)
3. TƯỜNG CÁNH MỐ (Wing Walls - TUONG CANH - Phương pháp dải Hillerborg)
4. BỆ MỐ (Footing - KT BE)
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from .model import AbutmentModel
from .loads import AbutmentLoadsSummary
from .combinations import CombinationResult
from .pile_analysis import AbutmentPileAnalysisSummary
from ..tcvn.materials import Concrete, Rebar, Soil
from ..tcvn.concrete import (
    check_flexure_rectangular,
    check_min_reinforcement,
    check_crack_control,
    check_shear_beam,
    check_punching_shear_two_way,
    FlexureCheckResult,
    MinReinforcementCheckResult,
    CrackControlResult,
    ShearCheckResult
)


@dataclass
class StemCheckSummary:
    """Kết quả kiểm toán Tường thân mố"""
    b: float                   # Bề rộng tiết diện (mm)
    h: float                   # Chiều cao tiết diện (mm)
    Mu_max: float              # Mô men lớn nhất ULS (kN.m)
    Pu_at_Mu_max: float        # Lực nén đồng thời (kN)
    Vu_max: float              # Lực cắt lớn nhất ULS (kN)
    Ms_max: float              # Mô men lớn nhất SLS (kN.m)
    flexure_check: FlexureCheckResult
    min_rebar_check: MinReinforcementCheckResult
    crack_check: CrackControlResult
    shear_check: ShearCheckResult
    rebar_ratio: float         # Hàm lượng cốt thép (%)
    rebar_ratio_passed: bool
    overall_passed: bool


@dataclass
class BackwallCheckSummary:
    """Kết quả kiểm toán Tường đỉnh mố"""
    b: float                   # Bề rộng tính toán (mm)
    h: float                   # Chiều cao tiết diện (mm)
    Mu: float                  # Mô men uốn chân tường đỉnh (kN.m)
    Vu: float                  # Lực cắt chân tường đỉnh (kN)
    Ms: float                  # Mô men TTGH Sử dụng (kN.m)
    flexure_check: FlexureCheckResult
    min_rebar_check: MinReinforcementCheckResult
    crack_check: CrackControlResult
    shear_check: ShearCheckResult
    overall_passed: bool


@dataclass
class WingWallCheckSummary:
    """Kết quả kiểm toán Tường cánh mố (Phương pháp dải Hillerborg)"""
    Htc: float                 # Chiều cao tường cánh (m)
    w_top: float               # Chiều dài đỉnh tường (m)
    w_bot: float               # Chiều dài đáy tường (m)
    # Ngàm đứng (Thép ngang)
    Mu_vert_fix: float         # Mô men ngàm đứng (kN.m/m)
    Vu_vert_fix: float         # Lực cắt ngàm đứng (kN/m)
    Ms_vert_fix: float         # Mô men SLS ngàm đứng (kN.m/m)
    flexure_vert_fix: FlexureCheckResult
    crack_vert_fix: CrackControlResult
    shear_vert_fix: ShearCheckResult
    # Ngàm đáy (Thép đứng)
    Mu_bot_fix: float          # Mô men ngàm đáy (kN.m/m)
    Vu_bot_fix: float          # Lực cắt ngàm đáy (kN/m)
    Ms_bot_fix: float          # Mô men SLS ngàm đáy (kN.m/m)
    flexure_bot_fix: FlexureCheckResult
    crack_bot_fix: CrackControlResult
    shear_bot_fix: ShearCheckResult
    overall_passed: bool


@dataclass
class FootingCheckSummary:
    """Kết quả kiểm toán Bệ mố"""
    # Mép trước thân mố (Toe)
    Mu_front: float            # Mô men mép trước (kN.m)
    Vu_front: float            # Lực cắt mép trước (kN)
    Ms_front: float            # Mô men SLS mép trước (kN.m)
    flexure_front: FlexureCheckResult
    crack_front: CrackControlResult
    shear_front: ShearCheckResult
    # Mép sau thân mố (Heel)
    Mu_rear: float             # Mô men mép sau (kN.m)
    Vu_rear: float             # Lực cắt mép sau (kN)
    Ms_rear: float             # Mô men SLS mép sau (kN.m)
    flexure_rear: FlexureCheckResult
    crack_rear: CrackControlResult
    shear_rear: ShearCheckResult
    # Cắt đâm thủng 2 phương
    punching_passed: bool
    Vr_punching: float
    Vu_punching: float
    overall_passed: bool


@dataclass
class AbutmentVerificationSummary:
    """Tổng kết kiểm toán toàn bộ mố cầu"""
    stem: StemCheckSummary
    backwall: BackwallCheckSummary
    wing_wall: WingWallCheckSummary
    footing: FootingCheckSummary
    all_passed: bool


def check_abutment_stem(
    model: AbutmentModel,
    stem_combinations: List[CombinationResult],
    concrete: Concrete,
    rebar: Rebar
) -> StemCheckSummary:
    """
    1. KIỂM TOÁN TƯỜNG THÂN MỐ (Mặt cắt đỉnh bệ)
    """
    sin_a = math.sin(model.alpha_rad)
    b_stem = (model.C1 / sin_a) * 1000.0  # mm
    h_stem = model.B3 * 1000.0            # mm

    # Tìm bao mô men lớn nhất và lực cắt lớn nhất ở ULS và SLS
    Mu_max = 0.0
    Pu_at_Mu = 0.0
    Vu_max = 0.0
    Ms_max = 0.0

    for comb in stem_combinations:
        if comb.limit_state_group == "STRENGTH":
            if abs(comb.My) > Mu_max:
                Mu_max = abs(comb.My)
                Pu_at_Mu = comb.N
            if abs(comb.Hx) > Vu_max:
                Vu_max = abs(comb.Hx)
        elif comb.limit_state_group == "SERVICE":
            if abs(comb.My) > Ms_max:
                Ms_max = abs(comb.My)

    # Diện tích cốt thép thân mố:
    # Mặt sau (tiếp xúc đất đắp): chịu KÉO do áp lực đất đẩy tới -> Thép chịu kéo chính As
    A_bar_tension = math.pi * (model.rebar_diam_stem_rear ** 2) / 4.0
    num_bars = int(b_stem / model.rebar_spacing_stem_rear) + 1
    As_total = num_bars * A_bar_tension
    
    # Mặt trước (hướng ra nhịp): chịu NÉN -> Thép chịu nén As'
    A_bar_prime = math.pi * (model.rebar_diam_stem_front ** 2) / 4.0
    num_bars_front = int(b_stem / model.rebar_spacing_stem_front) + 1
    As_prime_total = num_bars_front * A_bar_prime

    # Sức kháng uốn (xét cốt thép chịu nén)
    flexure_res = check_flexure_rectangular(
        b=b_stem, h=h_stem, dc=model.cover_stem, As=As_total,
        Mu=Mu_max, concrete=concrete, rebar=rebar,
        As_prime=As_prime_total, dc_prime=model.cover_stem
    )

    # Cốt thép tối thiểu
    min_rebar_res = check_min_reinforcement(
        b=b_stem, h=h_stem, Mr=flexure_res.Mr, Mu=Mu_max, concrete=concrete
    )

    # Nứt (kiểm tra thớ chịu kéo mặt sau)
    crack_res = check_crack_control(
        b=b_stem, h=h_stem, dc=model.cover_stem, As=As_total,
        s_rebar=model.rebar_spacing_stem_rear, Ms=Ms_max, concrete=concrete, rebar=rebar
    )

    # Cắt (xét diện tích đai)
    A_stirrup_bar = math.pi * (model.stirrup_diam_stem ** 2) / 4.0
    Av_total = model.stirrup_legs_stem * A_stirrup_bar
    shear_res = check_shear_beam(
        b=b_stem, h=h_stem, d=h_stem - model.cover_stem,
        a_whitney=flexure_res.a, Av=Av_total, s_stirrup=model.stirrup_spacing_stem,
        Vu=Vu_max, Nu=Pu_at_Mu, concrete=concrete, rebar=rebar
    )

    # Hàm lượng cốt thép tường thân mố (TCVN 11823-5 Điều 5.10.8: rho_min = 0.15%)
    d = h_stem - model.cover_stem
    rho = (As_total / (b_stem * d)) * 100.0
    rho_min = 0.15 # % cho tường/bản chịu uốn
    rho_pass = (rho >= rho_min) and (rho <= 4.0)

    overall = flexure_res.passed and min_rebar_res.passed and crack_res.passed and shear_res.passed and rho_pass

    return StemCheckSummary(
        b=b_stem, h=h_stem, Mu_max=Mu_max, Pu_at_Mu_max=Pu_at_Mu,
        Vu_max=Vu_max, Ms_max=Ms_max, flexure_check=flexure_res,
        min_rebar_check=min_rebar_res, crack_check=crack_res,
        shear_check=shear_res, rebar_ratio=rho, rebar_ratio_passed=rho_pass,
        overall_passed=overall
    )


def check_abutment_backwall(
    model: AbutmentModel,
    concrete: Concrete,
    rebar: Rebar
) -> BackwallCheckSummary:
    """
    2. KIỂM TOÁN TƯỜNG ĐỈNH MỐ (Mặt cắt chân tường đỉnh)
    """
    sin_a = math.sin(model.alpha_rad)
    b = (model.C1 / sin_a) * 1000.0        # mm
    h = (model.B7 * sin_a) * 1000.0        # mm
    H7 = model.H7                          # m

    soil = Soil(gamma_s=model.gamma_s, phi=model.phi, delta=0.0, beta=0.0)
    Ka = soil.Ka
    heq = 1.2 # Bảng 22

    # Lực áp lực đất và hoạt tải đắp tác dụng lên chiều cao H7
    b_m = model.C1 / sin_a
    EH = 0.5 * model.gamma_s * (H7 ** 2) * Ka * b_m # kN
    LS = Ka * heq * model.gamma_s * H7 * b_m         # kN

    # Nội lực tại chân tường đỉnh
    Mu = 1.50 * EH * (H7 / 3.0) + 1.75 * LS * (H7 / 2.0)
    Vu = 1.50 * EH + 1.75 * LS
    Ms = 1.00 * EH * (H7 / 3.0) + 1.00 * LS * (H7 / 2.0)

    # Thép tường đỉnh
    A_bar = math.pi * (model.rebar_diam_backwall ** 2) / 4.0
    num_bars = int(b / model.rebar_spacing_backwall) + 1
    As_total = num_bars * A_bar

    flexure_res = check_flexure_rectangular(
        b=b, h=h, dc=model.cover_backwall, As=As_total,
        Mu=Mu, concrete=concrete, rebar=rebar
    )
    min_rebar_res = check_min_reinforcement(
        b=b, h=h, Mr=flexure_res.Mr, Mu=Mu, concrete=concrete
    )
    crack_res = check_crack_control(
        b=b, h=h, dc=model.cover_backwall, As=As_total,
        s_rebar=model.rebar_spacing_backwall, Ms=Ms, concrete=concrete, rebar=rebar
    )
    shear_res = check_shear_beam(
        b=b, h=h, d=h - model.cover_backwall, a_whitney=flexure_res.a,
        Av=0.0, s_stirrup=0.0, Vu=Vu, Nu=0.0, concrete=concrete, rebar=rebar
    )

    overall = flexure_res.passed and min_rebar_res.passed and crack_res.passed and shear_res.passed

    return BackwallCheckSummary(
        b=b, h=h, Mu=Mu, Vu=Vu, Ms=Ms, flexure_check=flexure_res,
        min_rebar_check=min_rebar_res, crack_check=crack_res,
        shear_check=shear_res, overall_passed=overall
    )


def check_abutment_wing_walls(
    model: AbutmentModel,
    concrete: Concrete,
    rebar: Rebar
) -> WingWallCheckSummary:
    """
    3. KIỂM TOÁN TƯỜNG CÁNH MỐ (Phương pháp dải Hillerborg)
    Bản ngàm 2 cạnh kề: ngàm đứng vào thân + ngàm đáy vào bệ
    """
    Htc = model.H2 + model.H3 + model.H4
    w_top = model.B2 + model.B5
    w_bot = model.B2
    soil = Soil(gamma_s=model.gamma_s, phi=model.phi, delta=0.0, beta=0.0)
    Ka = soil.Ka
    heq = 0.6 if Htc >= 6.0 else 0.9

    # Chia 8 dải theo chiều cao (z đo từ đỉnh xuống)
    num_strips = 8
    dz = Htc / num_strips

    max_mx_u = 0.0
    max_vx_u = 0.0
    max_msx = 0.0

    sum_Mbot_u = 0.0
    sum_Vbot_u = 0.0
    sum_Mbot_s = 0.0

    for i in range(num_strips):
        z_mid = (i + 0.5) * dz
        Lz = max(0.1, Htc - z_mid)

        # Chiều dài tường cánh tại cao độ z_mid
        if z_mid <= model.H4:
            Lx = w_top
        elif z_mid <= model.H4 + model.H3:
            ratio = (z_mid - model.H4) / model.H3
            Lx = w_top - ratio * (w_top - w_bot)
        else:
            Lx = w_bot

        # Hệ số độ cứng dải Hillerborg alpha = Lz^4 / (Lx^4 + Lz^4)
        alpha = (Lz ** 4) / (Lx ** 4 + Lz ** 4)

        p_EH = model.gamma_s * z_mid * Ka
        p_LS = Ka * heq * model.gamma_s

        # Dải ngang (Ngàm đứng vào thân - thép ngang)
        mx_u = alpha * (1.50 * p_EH + 1.75 * p_LS) * (Lx ** 2) / 2.0
        msx = alpha * (1.00 * p_EH + 1.00 * p_LS) * (Lx ** 2) / 2.0
        vx_u = alpha * (1.50 * p_EH + 1.75 * p_LS) * Lx

        max_mx_u = max(max_mx_u, mx_u)
        max_vx_u = max(max_vx_u, vx_u)
        max_msx = max(max_msx, msx)

        # Dải đứng (Ngàm đáy vào bệ - tích phân toàn bộ chiều cao)
        sum_Mbot_u += (1.0 - alpha) * (1.50 * p_EH + 1.75 * p_LS) * Lz * dz
        sum_Mbot_s += (1.0 - alpha) * (1.00 * p_EH + 1.00 * p_LS) * Lz * dz
        sum_Vbot_u += (1.0 - alpha) * (1.50 * p_EH + 1.75 * p_LS) * dz

    # Chiều dày tường cánh C3 (mm) và dải tính toán 1m (1000 mm)
    h_wing = model.C3 * 1000.0
    b_strip = 1000.0

    # 1. TIẾT DIỆN NGÀM ĐỨNG VÀO THÂN MỐ (Cốt thép ngang)
    A_bar_h = math.pi * (model.rebar_diam_wing_horiz ** 2) / 4.0
    As_horiz = (b_strip / model.rebar_spacing_wing_horiz) * A_bar_h
    A_stirrup_w = math.pi * (model.stirrup_diam_wing ** 2) / 4.0
    Av_wing = 2.0 * A_stirrup_w

    flex_vert = check_flexure_rectangular(
        b=b_strip, h=h_wing, dc=model.cover_wing, As=As_horiz,
        Mu=max_mx_u, concrete=concrete, rebar=rebar
    )
    crack_vert = check_crack_control(
        b=b_strip, h=h_wing, dc=model.cover_wing, As=As_horiz,
        s_rebar=model.rebar_spacing_wing_horiz, Ms=max_msx, concrete=concrete, rebar=rebar
    )
    shear_vert = check_shear_beam(
        b=b_strip, h=h_wing, d=h_wing - model.cover_wing, a_whitney=flex_vert.a,
        Av=Av_wing, s_stirrup=model.stirrup_spacing_wing, Vu=max_vx_u, Nu=0.0, concrete=concrete, rebar=rebar
    )

    # 2. TIẾT DIỆN NGÀM ĐÁY VÀO BỆ MỐ (Cốt thép đứng)
    A_bar_v = math.pi * (model.rebar_diam_wing_vert ** 2) / 4.0
    As_vert = (b_strip / model.rebar_spacing_wing_vert) * A_bar_v

    flex_bot = check_flexure_rectangular(
        b=b_strip, h=h_wing, dc=model.cover_wing, As=As_vert,
        Mu=sum_Mbot_u, concrete=concrete, rebar=rebar
    )
    crack_bot = check_crack_control(
        b=b_strip, h=h_wing, dc=model.cover_wing, As=As_vert,
        s_rebar=model.rebar_spacing_wing_vert, Ms=sum_Mbot_s, concrete=concrete, rebar=rebar
    )
    shear_bot = check_shear_beam(
        b=b_strip, h=h_wing, d=h_wing - model.cover_wing, a_whitney=flex_bot.a,
        Av=Av_wing, s_stirrup=model.stirrup_spacing_wing, Vu=sum_Vbot_u, Nu=0.0, concrete=concrete, rebar=rebar
    )

    overall = flex_vert.passed and crack_vert.passed and shear_vert.passed and flex_bot.passed and crack_bot.passed and shear_bot.passed

    return WingWallCheckSummary(
        Htc=Htc, w_top=w_top, w_bot=w_bot,
        Mu_vert_fix=max_mx_u, Vu_vert_fix=max_vx_u, Ms_vert_fix=max_msx,
        flexure_vert_fix=flex_vert, crack_vert_fix=crack_vert, shear_vert_fix=shear_vert,
        Mu_bot_fix=sum_Mbot_u, Vu_bot_fix=sum_Vbot_u, Ms_bot_fix=sum_Mbot_s,
        flexure_bot_fix=flex_bot, crack_bot_fix=crack_bot, shear_bot_fix=shear_bot,
        overall_passed=overall
    )


def check_abutment_footing(
    model: AbutmentModel,
    piles_summary: AbutmentPileAnalysisSummary,
    concrete: Concrete,
    rebar: Rebar
) -> FootingCheckSummary:
    """
    4. KIỂM TOÁN BỆ MỐ (Tại mép trước và mép sau thân mố)
    """
    # Mép trước thân mố: x_mep_truoc = B1/2 - B4
    x_front_face = model.B1 / 2.0 - model.B4
    # Mép sau thân mố: x_mep_sau = B1/2 - B4 - B3
    x_rear_face = model.B1 / 2.0 - model.B4 - model.B3

    # Chiều rộng bệ C1 (mm), Chiều cao bệ H1 (mm)
    b_footing = model.C1 * 1000.0
    h_footing = model.H1 * 1000.0

    # Tính mô men uốn và lực cắt lớn nhất tại mép trước và mép sau từ phản lực cọc
    Mu_front_max = 0.0
    Vu_front_max = 0.0
    Ms_front_max = 0.0

    Mu_rear_max = 0.0
    Vu_rear_max = 0.0
    Ms_rear_max = 0.0

    for res in piles_summary.reactions_all:
        # Tổng phản lực và mô men của các cọc nằm ngoài mép trước (x > x_front_face)
        v_f = 0.0
        m_f = 0.0
        # Tổng phản lực và mô men của các cọc nằm ngoài mép sau (x < x_rear_face)
        v_r = 0.0
        m_r = 0.0

        for p in piles_summary.piles:
            p_f_val = res.pile_forces.get(p.id, 0.0)
            p_force = p_f_val.N if hasattr(p_f_val, 'N') else float(p_f_val)
            if p.x > x_front_face:
                v_f += p_force
                m_f += p_force * (p.x - x_front_face)
            elif p.x < x_rear_face:
                v_r += p_force
                m_r += p_force * (x_rear_face - p.x)

        if "CĐ" in res.comb_name or "CD" in res.comb_name or "ĐB" in res.comb_name or "DB" in res.comb_name:
            Mu_front_max = max(Mu_front_max, abs(m_f))
            Vu_front_max = max(Vu_front_max, abs(v_f))
            Mu_rear_max = max(Mu_rear_max, abs(m_r))
            Vu_rear_max = max(Vu_rear_max, abs(v_r))
        elif "SD" in res.comb_name:
            Ms_front_max = max(Ms_front_max, abs(m_f))
            Ms_rear_max = max(Ms_rear_max, abs(m_r))

    # Cốt thép đỉnh bệ (cốt thép chịu nén)
    A_bar_top = math.pi * (model.rebar_diam_footing_top ** 2) / 4.0
    As_top = (b_footing / model.rebar_spacing_footing_top) * A_bar_top
    A_stirrup_f = math.pi * (model.stirrup_diam_footing ** 2) / 4.0
    Av_footing = model.stirrup_legs_footing * A_stirrup_f

    # Cốt thép đáy mép trước
    A_bar_ff = math.pi * (model.rebar_diam_footing_bot_front ** 2) / 4.0
    As_front = (b_footing / model.rebar_spacing_footing_bot_front) * A_bar_ff

    flex_front = check_flexure_rectangular(
        b=b_footing, h=h_footing, dc=model.cover_footing, As=As_front,
        Mu=Mu_front_max, concrete=concrete, rebar=rebar,
        As_prime=As_top, dc_prime=model.cover_footing
    )
    crack_front = check_crack_control(
        b=b_footing, h=h_footing, dc=model.cover_footing, As=As_front,
        s_rebar=model.rebar_spacing_footing_bot_front, Ms=Ms_front_max, concrete=concrete, rebar=rebar
    )
    shear_front = check_shear_beam(
        b=b_footing, h=h_footing, d=h_footing - model.cover_footing,
        a_whitney=flex_front.a, Av=Av_footing, s_stirrup=model.stirrup_spacing_footing, Vu=Vu_front_max, Nu=0.0,
        concrete=concrete, rebar=rebar
    )

    # Cốt thép đáy mép sau
    A_bar_rf = math.pi * (model.rebar_diam_footing_bot_rear ** 2) / 4.0
    As_rear = (b_footing / model.rebar_spacing_footing_bot_rear) * A_bar_rf

    flex_rear = check_flexure_rectangular(
        b=b_footing, h=h_footing, dc=model.cover_footing, As=As_rear,
        Mu=Mu_rear_max, concrete=concrete, rebar=rebar,
        As_prime=As_top, dc_prime=model.cover_footing
    )
    crack_rear = check_crack_control(
        b=b_footing, h=h_footing, dc=model.cover_footing, As=As_rear,
        s_rebar=model.rebar_spacing_footing_bot_rear, Ms=Ms_rear_max, concrete=concrete, rebar=rebar
    )
    shear_rear = check_shear_beam(
        b=b_footing, h=h_footing, d=h_footing - model.cover_footing,
        a_whitney=flex_rear.a, Av=Av_footing, s_stirrup=model.stirrup_spacing_footing, Vu=Vu_rear_max, Nu=0.0,
        concrete=concrete, rebar=rebar
    )

    # Kiểm toán đâm thủng 2 phương quanh cọc bất lợi nhất
    d_eff = h_footing - model.cover_footing
    D_pile_mm = model.pile_diameter * 1000.0
    b0_punch = math.pi * (D_pile_mm + d_eff)
    pass_punch, Vr_punch, Vu_punch = check_punching_shear_two_way(
        d=d_eff, b0=b0_punch, Vu=piles_summary.P_max_strength, concrete=concrete
    )

    overall = flex_front.passed and crack_front.passed and shear_front.passed and flex_rear.passed and crack_rear.passed and shear_rear.passed and pass_punch

    return FootingCheckSummary(
        Mu_front=Mu_front_max, Vu_front=Vu_front_max, Ms_front=Ms_front_max,
        flexure_front=flex_front, crack_front=crack_front, shear_front=shear_front,
        Mu_rear=Mu_rear_max, Vu_rear=Vu_rear_max, Ms_rear=Ms_rear_max,
        flexure_rear=flex_rear, crack_rear=crack_rear, shear_rear=shear_rear,
        punching_passed=pass_punch, Vr_punching=Vr_punch, Vu_punching=Vu_punch,
        overall_passed=overall
    )


def verify_entire_abutment(
    model: AbutmentModel,
    loads_summary: AbutmentLoadsSummary,
    stem_combinations: List[CombinationResult],
    piles_summary: AbutmentPileAnalysisSummary
) -> AbutmentVerificationSummary:
    """
    Thực hiện kiểm toán toàn bộ 4 cấu kiện của Mố
    """
    concrete = Concrete(fc_prime=model.fc_prime, gamma_c=model.gamma_c, K1=model.K1)
    rebar = Rebar(fy=model.fy, Es=model.Es)

    stem_res = check_abutment_stem(model, stem_combinations, concrete, rebar)
    backwall_res = check_abutment_backwall(model, concrete, rebar)
    wing_res = check_abutment_wing_walls(model, concrete, rebar)
    footing_res = check_abutment_footing(model, piles_summary, concrete, rebar)

    all_pass = stem_res.overall_passed and backwall_res.overall_passed and wing_res.overall_passed and footing_res.overall_passed and piles_summary.passed_capacity

    return AbutmentVerificationSummary(
        stem=stem_res,
        backwall=backwall_res,
        wing_wall=wing_res,
        footing=footing_res,
        all_passed=all_pass
    )
