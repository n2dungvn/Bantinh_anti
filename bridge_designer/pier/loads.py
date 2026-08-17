"""
Module: pier.loads
Tính toán chi tiết các tải trọng tiêu chuẩn tác dụng lên Trụ cầu:
- Tĩnh tải KCN (DC1, DW) nhịp trái và nhịp phải kèm độ lệch tâm
- Tĩnh tải bản thân trụ (DC2: Xà mũ, Thân trụ, Bệ trụ) và Đẩy nổi (WB)
- Hoạt tải xe cộ HL-93 (chất 2 nhịp cho Nmax và 1 nhịp cho My max), lực hãm BR, ly tâm CE
- Tải trọng gió WS, WL, Pv
- Tải trọng dòng chảy WA
- Tải trọng động đất EQ
- Tải trọng va xe CT (1800 kN) và va tàu CV
- Lực dọc cầu do biến dạng cưỡng bức qua hệ gối (TU, CR, SH, FR)
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple
from .model import PierModel
from ..tcvn.loads import get_multi_lane_factor, get_wind_s_factor
from ..tcvn.bearings import BearingChainSolver, BearingNode, BearingForcesResult
from ..abutment.loads import LoadVector


@dataclass
class PierLoadsSummary:
    """Tổng hợp tải trọng tiêu chuẩn tại 3 mặt cắt: Chân xà mũ, Đỉnh bệ, Đáy bệ"""
    loads_cap_base: Dict[str, LoadVector]   # Tại chân xà mũ / đỉnh thân
    loads_stem_base: Dict[str, LoadVector]  # Tại đỉnh bệ / đáy thân (mặt cắt kiểm nén uốn)
    loads_footing_base: Dict[str, LoadVector] # Tại đáy bệ (mặt cắt kiểm cọc)
    bearing_forces: BearingForcesResult
    DC2_cap: float
    DC2_stem: float
    DC2_footing: float
    WB_total: float
    WA_total: float


def calculate_pier_loads(model: PierModel) -> PierLoadsSummary:
    """
    Tính toàn bộ tải trọng tiêu chuẩn cho trụ cầu
    """
    gc = model.gamma_c
    gw = model.gamma_w

    # 1. TĨNH TẢI KẾT CẤU NHỊP (DC1, DW)
    DC1_total = model.DC1_left + model.DC1_right
    DW_total = model.DW_left + model.DW_right

    # Mô men do lệch tâm hàng gối: My = R_left * e_left + R_right * e_right
    My_DC1 = model.DC1_left * model.e_left + model.DC1_right * model.e_right
    My_DW = model.DW_left * model.e_left + model.DW_right * model.e_right

    # 2. TĨNH TẢI BẢN THÂN TRỤ (DC2)
    # 2.1 Xà mũ
    V_xm = model.Vxm
    DC2_cap = V_xm * gc

    # 2.2 Thân trụ
    # Tính diện tích đáy và đỉnh
    if model.shape_type == 0:  # Chữ nhật
        Ag_bot = model.bth1 * model.hth1
        Ag_top = (model.bth2 * model.hth2) if model.is_tapered else Ag_bot
    elif model.shape_type == 1:  # Đầu tròn
        R_bot = model.hth1 / 2.0
        Ag_bot = max(0.0, model.bth1 - 2.0 * R_bot) * model.hth1 + math.pi * (R_bot ** 2)
        R_top = model.hth2 / 2.0
        Ag_top = (max(0.0, model.bth2 - 2.0 * R_top) * model.hth2 + math.pi * (R_top ** 2)) if model.is_tapered else Ag_bot
    else:  # Vát góc
        Ag_bot = model.bth1 * model.hth1 - 2.0 * model.cx * model.cy
        Ag_top = (model.bth2 * model.hth2 - 2.0 * model.cx * model.cy) if model.is_tapered else Ag_bot

    # Nếu có 2 thân (TWIN)
    if model.pier_column_type == "TWIN":
        Ag_bot *= 2.0
        Ag_top *= 2.0

    # Thể tích thân trụ: V = Hth * (Ag_bot + Ag_top) / 2
    V_stem = model.Hth * (Ag_bot + Ag_top) / 2.0
    DC2_stem = V_stem * gc

    # 2.3 Bệ trụ
    V_footing = model.Bbe * model.Cbe * model.Hbe
    DC2_footing = V_footing * gc

    # 3. LỰC ĐẨY NỔI (WB)
    # Tính phần ngập nước dưới MNTN (hn1 đo từ đáy bệ)
    WB_total = 0.0
    if model.hn1 > 0:
        if model.hn1 <= model.Hbe:
            V_sub = model.Bbe * model.Cbe * model.hn1
        else:
            h_stem_sub = min(model.Hth, model.hn1 - model.Hbe)
            V_sub = V_footing + Ag_bot * h_stem_sub
        WB_total = V_sub * gw

    # 4. HOẠT TẢI XE HL-93 (2 NHỊP & 1 NHỊP)
    Ls1 = model.Ls1
    Ls2 = model.Ls2

    # Phản lực xe tải lên trụ:
    # 2 nhịp (đặt xe bất lợi nhất qua gối trụ):
    # R_truck_2span ~ 145 + 145*(1 - 4.3/Ls1) + 35*(1 - 8.6/Ls1) + ...
    R_truck_1span = (145.0 * Ls1 + 145.0 * max(0.0, Ls1 - 4.3) + 35.0 * max(0.0, Ls1 - 8.6)) / Ls1
    R_tandem_1span = (110.0 * Ls1 + 110.0 * max(0.0, Ls1 - 1.2)) / Ls1
    R_axle_1span = max(R_truck_1span, R_tandem_1span)
    R_lane_1span = model.qlan * Ls1 / 2.0
    R_1lane_1span_no_m = R_axle_1span * (1.0 + model.IM) + R_lane_1span

    # 2 nhịp giản đơn chất cả 2 bên:
    R_1lane_2span_no_m = 2.0 * R_1lane_1span_no_m

    # Hàng gối lệch lớn nhất e_max (m)
    e_max = max(abs(model.e_left), abs(model.e_right))

    ll_cases_stem: Dict[str, LoadVector] = {}
    ll_cases_footing: Dict[str, LoadVector] = {}

    w_lane = 3.6
    first_lane_y = model.width_Bxe / 2.0 - 0.6 - 1.8 # tim làn ngoài cùng

    # 4.1 Chất 2 nhịp (cho N max)
    for k in range(1, model.num_lanes + 1):
        m_k = get_multi_lane_factor(k)
        N_k = k * R_1lane_2span_no_m * m_k

        lane_positions = [first_lane_y - i * w_lane for i in range(k)]
        avg_ey = sum(lane_positions) / k if k > 0 else 0.0

        Mx_ecc = N_k * avg_ey

        # Lệch tâm ngang
        ll_cases_stem[f"LL_2span_{k}lan_lech"] = LoadVector(
            name=f"LL 2 nhịp ({k} làn lệch)", N=N_k, Mx=Mx_ecc, My=0.0
        )
        ll_cases_footing[f"LL_2span_{k}lan_lech"] = LoadVector(
            name=f"LL 2 nhịp ({k} làn lệch)", N=N_k, Mx=Mx_ecc, My=0.0
        )

        # Đúng tâm
        ll_cases_stem[f"LL_2span_{k}lan_dung"] = LoadVector(
            name=f"LL 2 nhịp ({k} làn đúng)", N=N_k, Mx=0.0, My=0.0
        )
        ll_cases_footing[f"LL_2span_{k}lan_dung"] = LoadVector(
            name=f"LL 2 nhịp ({k} làn đúng)", N=N_k, Mx=0.0, My=0.0
        )

    # 4.2 Chất 1 nhịp (cho My max)
    for k in range(1, model.num_lanes + 1):
        m_k = get_multi_lane_factor(k)
        N_k = k * R_1lane_1span_no_m * m_k

        lane_positions = [first_lane_y - i * w_lane for i in range(k)]
        avg_ey = sum(lane_positions) / k if k > 0 else 0.0

        Mx_ecc = N_k * avg_ey
        My_1span = N_k * e_max

        ll_cases_stem[f"LL_1span_{k}lan"] = LoadVector(
            name=f"LL 1 nhịp ({k} làn)", N=N_k, Mx=Mx_ecc, My=My_1span
        )
        ll_cases_footing[f"LL_1span_{k}lan"] = LoadVector(
            name=f"LL 1 nhịp ({k} làn)", N=N_k, Mx=Mx_ecc, My=My_1span
        )

    # 5. LỰC HÃM XE BR VÀ MA SÁT GỐI FR
    # Nếu có gối FIXED thì truyền BR
    BR_1lane = max(0.25 * 325.0, 0.05 * (325.0 + model.qlan * (Ls1 + Ls2)))
    m_all = get_multi_lane_factor(model.num_lanes)
    BR_total = model.num_lanes * BR_1lane * m_all
    # Cao độ đặt BR: trên mặt cầu 1.8m
    z_BR_footing = model.Hbe + model.Hth + model.hxm + model.h_bearing + model.d_kcn + 1.8
    z_BR_stem = model.Hth + model.hxm + model.h_bearing + model.d_kcn + 1.8

    My_BR_footing = BR_total * z_BR_footing
    My_BR_stem = BR_total * z_BR_stem

    # 6. HỆ GỐI VÀ BIẾN DẠNG CƯỠNG BỨC (TU, CR, SH, FR)
    # Giải hệ gối bằng BearingChainSolver
    nodes = model.chain_nodes
    if not nodes:
        # Tự động tạo 1 nút trụ đang tính nếu chưa có
        nodes = [
            BearingNode(
                name=model.pier_name,
                x=model.span_L1,
                L_next_span=model.span_L2,
                bearing_type_left="Chậu di động 1 phương ngang",
                bearing_type_right="Chậu di động 2 phương",
                state_left=model.bearing_state_left,
                state_right=model.bearing_state_right,
                K_pier=1.7e5,
                mu_friction=model.friction_mu
            )
        ]
    chain_solver = BearingChainSolver(nodes)
    bearing_res = chain_solver.solve_pier_forces(
        target_node_name=model.pier_name,
        N_left_DL=model.DC1_left + model.DW_left,
        N_right_DL=model.DC1_right + model.DW_right
    )

    # 7. GIÓ (WS, WL)
    V_des = model.VB * model.S_factor
    q_wind_des = 0.5 * 1.25e-3 * (V_des ** 2)
    q_wind_25 = 0.5 * 1.25e-3 * (25.0 ** 2)

    # Diện tích chắn gió KCN: d_kcn * (Ls1 + Ls2) / 2
    A_wind_kcn = model.d_kcn * ((Ls1 + Ls2) / 2.0)
    WS_kcn_ngang_des = q_wind_des * model.Cd_kcn * A_wind_kcn
    WS_kcn_ngang_25 = q_wind_25 * model.Cd_kcn * A_wind_kcn

    # Gió lên thân trụ: chiều cao Hth, bề rộng trung bình (bth1+bth2)/2
    b_pier_avg = (model.bth1 + model.bth2) / 2.0 if model.is_tapered else model.bth1
    A_wind_pier = b_pier_avg * model.Hth
    WS_pier_ngang_des = q_wind_des * model.Cd_pier * A_wind_pier
    WS_pier_ngang_25 = q_wind_25 * model.Cd_pier * A_wind_pier

    WS_ngang_des = WS_kcn_ngang_des + WS_pier_ngang_des
    WS_ngang_25 = WS_kcn_ngang_25 + WS_pier_ngang_25

    WS_doc_des = 0.25 * WS_kcn_ngang_des
    WS_doc_25 = 0.25 * WS_kcn_ngang_25

    z_kcn_stem = model.Hth + model.hxm + model.h_bearing + model.d_kcn / 2.0
    z_kcn_footing = model.Hbe + z_kcn_stem
    z_pier_stem = model.Hth / 2.0
    z_pier_footing = model.Hbe + z_pier_stem

    Mx_WS_des_stem = WS_kcn_ngang_des * z_kcn_stem + WS_pier_ngang_des * z_pier_stem
    Mx_WS_des_footing = WS_kcn_ngang_des * z_kcn_footing + WS_pier_ngang_des * z_pier_footing

    Mx_WS_25_stem = WS_kcn_ngang_25 * z_kcn_stem + WS_pier_ngang_25 * z_pier_stem
    Mx_WS_25_footing = WS_kcn_ngang_25 * z_kcn_footing + WS_pier_ngang_25 * z_pier_footing

    My_WS_des_stem = WS_doc_des * z_kcn_stem
    My_WS_des_footing = WS_doc_des * z_kcn_footing

    My_WS_25_stem = WS_doc_25 * z_kcn_stem
    My_WS_25_footing = WS_doc_25 * z_kcn_footing

    # Gió đứng Pv
    A_deck = model.width_W * ((Ls1 + Ls2) / 2.0)
    Pv_des = 0.00045 * (V_des ** 2) * A_deck

    # Gió trên hoạt tải WL: 1.46 kN/m ngang, 0.55 kN/m dọc
    WL_ngang = 1.46 * ((Ls1 + Ls2) / 2.0)
    WL_doc = 0.55 * ((Ls1 + Ls2) / 2.0)
    Mx_WL_stem = WL_ngang * z_BR_stem
    Mx_WL_footing = WL_ngang * z_BR_footing
    My_WL_stem = WL_doc * z_BR_stem
    My_WL_footing = WL_doc * z_BR_footing

    # 8. DÒNG CHẢY (WA)
    WA_total = 0.0
    Mx_WA_stem = 0.0
    Mx_WA_footing = 0.0
    if model.V_water > 0 and model.hn1 > 0:
        # Áp lực dòng chảy p = 5.14e-4 * CD * V² (MPa) = 0.514 * CD * V² (kN/m²)
        p_water = 0.514 * model.CD_water * (model.V_water ** 2)
        h_water_sub = min(model.Hth, max(0.0, model.hn1 - model.Hbe))
        A_water = model.hth1 * h_water_sub
        WA_total = p_water * A_water
        z_WA_stem = h_water_sub / 2.0
        z_WA_footing = model.Hbe + z_WA_stem
        # Tác dụng theo phương dọc cầu
        My_WA_stem = WA_total * z_WA_stem
        My_WA_footing = WA_total * z_WA_footing
    else:
        My_WA_stem = 0.0
        My_WA_footing = 0.0

    # 9. ĐỘNG ĐẤT (EQ)
    Csm = min(2.5 * model.accel_A, (1.2 * model.accel_A * model.S_seismic) / (0.5 ** (2.0 / 3.0)))
    N_LL_max = model.num_lanes * R_1lane_2span_no_m * m_all

    F_EQ_kcn = Csm * (DC1_total + DW_total + 0.5 * N_LL_max) / model.R_pier
    F_EQ_sub_stem = Csm * (DC2_cap + DC2_stem) / model.R_self
    F_EQ_sub_footing = Csm * (DC2_cap + DC2_stem + DC2_footing) / model.R_self

    EQ_stem = F_EQ_kcn + F_EQ_sub_stem
    EQ_footing = F_EQ_kcn + F_EQ_sub_footing

    # EQ ngang (Mx) và EQ dọc (My)
    Mx_EQ_stem = F_EQ_kcn * z_kcn_stem + F_EQ_sub_stem * (model.Hth / 2.0)
    Mx_EQ_footing = F_EQ_kcn * z_kcn_footing + F_EQ_sub_footing * (model.Hbe + model.Hth / 2.0)

    My_EQ_stem = F_EQ_kcn * z_kcn_stem + F_EQ_sub_stem * (model.Hth / 2.0)
    My_EQ_footing = F_EQ_kcn * z_kcn_footing + F_EQ_sub_footing * (model.Hbe + model.Hth / 2.0)

    # 10. VA XE (CT = 1800 kN) VÀ VA TÀU (CV)
    CT_val = model.CT if model.has_vehicle_collision else 0.0
    z_CT = model.z_CT  # đo từ đáy bệ
    z_CT_stem = max(0.0, z_CT - model.Hbe)
    My_CT_stem = CT_val * z_CT_stem
    My_CT_footing = CT_val * z_CT

    CV_val = model.CV
    z_CV = model.z_CV
    z_CV_stem = max(0.0, z_CV - model.Hbe)
    My_CV_stem = CV_val * z_CV_stem
    My_CV_footing = CV_val * z_CV

    # TẬP HỢP TẢI TRỌNG MẶT CẮT ĐỈNH BỆ (STEM BASE)
    loads_stem: Dict[str, LoadVector] = {
        "DC1": LoadVector("DC1 (KCN)", N=DC1_total, My=My_DC1),
        "DW": LoadVector("DW (Lớp phủ)", N=DW_total, My=My_DW),
        "DC2": LoadVector("DC2 (Bản thân trụ)", N=DC2_cap + DC2_stem, My=0.0),
        "WB": LoadVector("WB (Đẩy nổi)", N=-WB_total, My=0.0),
        "BR": LoadVector("BR (Lực hãm xe)", Hx=BR_total, My=My_BR_stem),
        "TU_pos": LoadVector("TU+ (Nhiệt tăng)", Hx=bearing_res.H_TU_pos, My=bearing_res.H_TU_pos * model.Hth),
        "TU_neg": LoadVector("TU- (Nhiệt giảm)", Hx=bearing_res.H_TU_neg, My=bearing_res.H_TU_neg * model.Hth),
        "CR": LoadVector("CR (Từ biến)", Hx=bearing_res.H_CR, My=bearing_res.H_CR * model.Hth),
        "SH": LoadVector("SH (Co ngót)", Hx=bearing_res.H_SH, My=bearing_res.H_SH * model.Hth),
        "FR_pos": LoadVector("FR+ (Ma sát gối)", Hx=bearing_res.H_FR, My=bearing_res.H_FR * model.Hth),
        "FR_neg": LoadVector("FR- (Ma sát gối)", Hx=-bearing_res.H_FR, My=-bearing_res.H_FR * model.Hth),
        "WS_ngang_des": LoadVector("WS ngang Vtk", Hy=WS_ngang_des, Mx=Mx_WS_des_stem),
        "WS_doc_des": LoadVector("WS dọc Vtk", Hx=WS_doc_des, My=My_WS_des_stem),
        "WS_ngang_25": LoadVector("WS ngang 25m/s", Hy=WS_ngang_25, Mx=Mx_WS_25_stem),
        "WS_doc_25": LoadVector("WS dọc 25m/s", Hx=WS_doc_25, My=My_WS_25_stem),
        "WS_dung": LoadVector("WS thẳng đứng", N=Pv_des, My=0.0),
        "WL_ngang": LoadVector("WL ngang", Hy=WL_ngang, Mx=Mx_WL_stem),
        "WL_doc": LoadVector("WL dọc", Hx=WL_doc, My=My_WL_stem),
        "WA": LoadVector("WA (Dòng chảy)", Hx=WA_total, My=My_WA_stem),
        "EQ_ngang": LoadVector("EQ ngang", Hy=EQ_stem, Mx=Mx_EQ_stem),
        "EQ_doc": LoadVector("EQ dọc", Hx=EQ_stem, My=My_EQ_stem),
        "CT": LoadVector("CT (Va xe 1800kN)", Hx=CT_val, My=My_CT_stem),
        "CV": LoadVector("CV (Va tàu)", Hx=CV_val, My=My_CV_stem)
    }
    loads_stem.update(ll_cases_stem)

    # TẬP HỢP TẢI TRỌNG MẶT CẮT ĐÁY BỆ (FOOTING BASE)
    loads_footing: Dict[str, LoadVector] = {
        "DC1": LoadVector("DC1 (KCN)", N=DC1_total, My=My_DC1),
        "DW": LoadVector("DW (Lớp phủ)", N=DW_total, My=My_DW),
        "DC2": LoadVector("DC2 (Bản thân trụ)", N=DC2_cap + DC2_stem + DC2_footing, My=0.0),
        "WB": LoadVector("WB (Đẩy nổi)", N=-WB_total, My=0.0),
        "BR": LoadVector("BR (Lực hãm xe)", Hx=BR_total, My=My_BR_footing),
        "TU_pos": LoadVector("TU+ (Nhiệt tăng)", Hx=bearing_res.H_TU_pos, My=bearing_res.H_TU_pos * (model.Hbe + model.Hth)),
        "TU_neg": LoadVector("TU- (Nhiệt giảm)", Hx=bearing_res.H_TU_neg, My=bearing_res.H_TU_neg * (model.Hbe + model.Hth)),
        "CR": LoadVector("CR (Từ biến)", Hx=bearing_res.H_CR, My=bearing_res.H_CR * (model.Hbe + model.Hth)),
        "SH": LoadVector("SH (Co ngót)", Hx=bearing_res.H_SH, My=bearing_res.H_SH * (model.Hbe + model.Hth)),
        "FR_pos": LoadVector("FR+ (Ma sát gối)", Hx=bearing_res.H_FR, My=bearing_res.H_FR * (model.Hbe + model.Hth)),
        "FR_neg": LoadVector("FR- (Ma sát gối)", Hx=-bearing_res.H_FR, My=-bearing_res.H_FR * (model.Hbe + model.Hth)),
        "WS_ngang_des": LoadVector("WS ngang Vtk", Hy=WS_ngang_des, Mx=Mx_WS_des_footing),
        "WS_doc_des": LoadVector("WS dọc Vtk", Hx=WS_doc_des, My=My_WS_des_footing),
        "WS_ngang_25": LoadVector("WS ngang 25m/s", Hy=WS_ngang_25, Mx=Mx_WS_25_footing),
        "WS_doc_25": LoadVector("WS dọc 25m/s", Hx=WS_doc_25, My=My_WS_25_footing),
        "WS_dung": LoadVector("WS thẳng đứng", N=Pv_des, My=0.0),
        "WL_ngang": LoadVector("WL ngang", Hy=WL_ngang, Mx=Mx_WL_footing),
        "WL_doc": LoadVector("WL dọc", Hx=WL_doc, My=My_WL_footing),
        "WA": LoadVector("WA (Dòng chảy)", Hx=WA_total, My=My_WA_footing),
        "EQ_ngang": LoadVector("EQ ngang", Hy=EQ_footing, Mx=Mx_EQ_footing),
        "EQ_doc": LoadVector("EQ dọc", Hx=EQ_footing, My=My_EQ_footing),
        "CT": LoadVector("CT (Va xe 1800kN)", Hx=CT_val, My=My_CT_footing),
        "CV": LoadVector("CV (Va tàu)", Hx=CV_val, My=My_CV_footing)
    }
    loads_footing.update(ll_cases_footing)

    # TẬP HỢP TẢI TRỌNG CHÂN XÀ MŨ (CAP BASE)
    loads_cap: Dict[str, LoadVector] = {
        "DC1": LoadVector("DC1", N=DC1_total, My=My_DC1),
        "DW": LoadVector("DW", N=DW_total, My=My_DW),
        "DC2": LoadVector("DC2", N=DC2_cap, My=0.0)
    }
    loads_cap.update(ll_cases_stem)

    return PierLoadsSummary(
        loads_cap_base=loads_cap,
        loads_stem_base=loads_stem,
        loads_footing_base=loads_footing,
        bearing_forces=bearing_res,
        DC2_cap=DC2_cap,
        DC2_stem=DC2_stem,
        DC2_footing=DC2_footing,
        WB_total=WB_total,
        WA_total=WA_total
    )
