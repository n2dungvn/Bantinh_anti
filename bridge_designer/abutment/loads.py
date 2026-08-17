"""
Module: abutment.loads
Tính toán chi tiết các tải trọng tác dụng lên mố cầu:
- Tĩnh tải kết cấu nhịp (DC1, DW)
- Tĩnh tải bản thân mố (DC2) và đất trên bệ (EV)
- Hoạt tải xe cộ HL-93 (chất 1..n làn), người đi bộ, lực hãm xe BR, lực ly tâm CE
- Áp lực đất tĩnh Coulomb EH, hoạt tải chất thêm LS, VS, ma sát gối FR
- Tải trọng gió WS, WL, Pv (CĐ III, CĐ V, SD I)
- Tải trọng động đất EQ và áp lực đất động Mononobe-Okabe ΔEAE
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple
from .model import AbutmentModel
from ..tcvn.loads import get_multi_lane_factor, get_wind_s_factor, WIND_VB_MAP, SEISMIC_SITE_FACTORS
from ..tcvn.materials import Soil, Water


@dataclass
class LoadVector:
    """Vector nội lực (N, Hx, Hy, Mx, My) tại một mặt cắt"""
    name: str
    N: float = 0.0             # Lực dọc (kN, nén dương)
    Hx: float = 0.0            # Lực ngang dọc cầu (kN, đẩy về phía nhịp dương)
    Hy: float = 0.0            # Lực ngang phương ngang cầu (kN)
    Mx: float = 0.0            # Mô men uốn quanh trục X (ngang cầu) (kN.m)
    My: float = 0.0            # Mô men uốn quanh trục Y (dọc cầu) (kN.m)


@dataclass
class AbutmentLoadsSummary:
    """Tổng hợp tải trọng tiêu chuẩn tại Đỉnh bệ và Đáy bệ"""
    # Tại đỉnh bệ (stem base)
    loads_stem_base: Dict[str, LoadVector]
    # Tại đáy bệ (footing base)
    loads_footing_base: Dict[str, LoadVector]
    # Các giá trị trung gian
    DC2_total: float
    EV_total: float
    EH_footing: float
    EH_stem: float
    LS_footing: float
    LS_stem: float
    delta_EAE_footing: float
    delta_EAE_stem: float
    FR_val: float
    Ka: float
    KAE: float


def calculate_abutment_loads(model: AbutmentModel) -> AbutmentLoadsSummary:
    """
    Tính toàn bộ các trường hợp tải trọng tiêu chuẩn cho mố cầu
    """
    sin_a = math.sin(model.alpha_rad)
    cos_a = math.cos(model.alpha_rad)
    Beff = model.Beff
    Hdb = model.Hdb
    Htb = model.Htb

    # Cánh tay đòn tính từ tim bệ (x=0 ở tim bệ, dương hướng về phía nhịp):
    # Tim gối cách tim bệ:
    # y_goi = B1/2 - B4 - B3 + B7 + B8 (theo bản vẽ định hình)
    # hoặc y_goi = B1/2 - B4 - (B3 - B7 - B8)
    y_goi = model.B1 / 2.0 - model.B4 - (model.B3 - model.B7 - model.B8)

    # Trọng tâm tường thân so với tim bệ:
    y_than = model.B1 / 2.0 - model.B4 - model.B3 / 2.0

    # Trọng tâm tường đỉnh so với tim bệ:
    y_dinh = model.B1 / 2.0 - model.B4 - model.B3 + model.B7 / 2.0

    # Đuôi bệ (phần đất đè lên): chiều dài = B1 - B4 - B3
    L_duoi_be = max(0.0, model.B1 - model.B4 - model.B3)
    y_duoi_be = -(model.B1 / 2.0 - L_duoi_be / 2.0) # Nằm phía sau tim bệ (-)

    # 1. TĨNH TẢI DC2 (BẢN THÂN MỐ)
    gc = model.gamma_c

    # 1.1 Bệ mố
    V_be = model.B1 * model.H1 * model.C1 * gc
    M_be_footing = 0.0

    # 1.2 Tường thân
    V_than = model.B3 * model.H6 * (model.C1 / sin_a) * gc
    M_than_stem = 0.0 # Tại trọng tâm thân
    M_than_footing = V_than * y_than

    # 1.3 Tường đỉnh
    V_dinh = model.B7 * model.H7 * (model.C1 / sin_a) * gc
    M_dinh_stem = V_dinh * (y_dinh - y_than)
    M_dinh_footing = V_dinh * y_dinh

    # 1.4 Tường cánh (2 bên)
    # Diện tích 1 tường cánh = (B2+B5)*H4 + ((B2+B5)+B2)/2*H3 + B2*H2
    A_tc_1 = (model.B2 + model.B5) * model.H4 + ((model.B2 + model.B5) + model.B2) / 2.0 * model.H3 + model.B2 * model.H2
    V_tc = model.ntc * A_tc_1 * model.C3 * gc
    # Trọng tâm tường cánh sơ bộ
    y_tc = - (model.B5 / 2.0) # Phía sau tim bệ
    M_tc_footing = V_tc * y_tc
    M_tc_stem = V_tc * (y_tc - y_than)

    # 1.5 Tường tai
    V_tt = model.ntt * model.B7 * model.H8 * model.C4 * gc
    y_tt = y_dinh
    M_tt_footing = V_tt * y_tt

    # 1.6 Ụ chống xô & mấu đỡ bản quá độ
    V_cx = model.num_cx * model.B11 * model.h_cx * model.C6 * gc
    y_cx = model.B1 / 2.0 - model.B4 - model.B11 / 2.0
    M_cx_footing = V_cx * y_cx

    V_mau = model.B9 * model.B9 * (model.C1 / sin_a) * gc
    y_mau = y_dinh - model.B7 / 2.0 - model.B9 / 2.0
    M_mau_footing = V_mau * y_mau

    # Tổng DC2
    DC2_total = V_be + V_than + V_dinh + V_tc + V_tt + V_cx + V_mau
    DC2_stem = V_than + V_dinh + V_tc + V_tt + V_cx + V_mau
    M_DC2_footing = M_be_footing + M_than_footing + M_dinh_footing + M_tc_footing + M_tt_footing + M_cx_footing + M_mau_footing
    M_DC2_stem = M_dinh_stem + M_tc_stem

    # 2. TĨNH TẢI KẾT CẤU NHỊP (DC1, DW)
    DC1 = model.DC_kcn
    DW = model.DW_kcn
    M_DC1_footing = DC1 * y_goi
    M_DC1_stem = DC1 * (y_goi - y_than)
    M_DW_footing = DW * y_goi
    M_DW_stem = DW * (y_goi - y_than)

    # 3. ĐẤT TRÊN BỆ (EV) VÀ HOẠT TẢI CHẤT THÊM ĐỨNG (VS)
    gs = model.gamma_s
    EV_total = L_duoi_be * Htb * (model.C1 / sin_a) * gs
    M_EV_footing = EV_total * y_duoi_be

    # Chiều cao đất tương đương heq cho LS (TCVN 11823-3 Bảng 22)
    # H <= 1.5m: heq = 1.2m; H = 3.0m: heq = 0.9m; H >= 6.0m: heq = 0.6m
    if Hdb <= 1.5:
        heq_db = 1.2
    elif Hdb <= 3.0:
        heq_db = 1.2 - (1.2 - 0.9) * (Hdb - 1.5) / 1.5
    elif Hdb <= 6.0:
        heq_db = 0.9 - (0.9 - 0.6) * (Hdb - 3.0) / 3.0
    else:
        heq_db = 0.6

    if Htb <= 1.5:
        heq_tb = 1.2
    elif Htb <= 3.0:
        heq_tb = 1.2 - (1.2 - 0.9) * (Htb - 1.5) / 1.5
    elif Htb <= 6.0:
        heq_tb = 0.9 - (0.9 - 0.6) * (Htb - 3.0) / 3.0
    else:
        heq_tb = 0.6

    VS_total = gs * heq_db * L_duoi_be * (model.C1 / sin_a)
    M_VS_footing = VS_total * y_duoi_be

    # 4. ÁP LỰC ĐẤT CHỦ ĐỘNG (EH) VÀ HOẠT TẢI ĐẮP ĐẤT (LS)
    soil = Soil(gamma_s=model.gamma_s, phi=model.phi, delta=model.delta, beta=model.beta)
    Ka = soil.Ka

    # Áp lực đất lên toàn bộ chiều cao mố đến đáy bệ
    EH_footing = 0.5 * gs * (Hdb ** 2) * Ka * Beff
    # Điểm đặt tại Hdb/3 tính từ đáy bệ -> Cánh tay đòn mô men My = Hdb/3
    M_EH_footing = EH_footing * (Hdb / 3.0)

    # Áp lực đất lên thân mố đến đỉnh bệ
    EH_stem = 0.5 * gs * (Htb ** 2) * Ka * Beff
    M_EH_stem = EH_stem * (Htb / 3.0)

    # Hoạt tải chất thêm ngang LS
    LS_footing = gs * heq_db * Ka * Beff * Hdb
    M_LS_footing = LS_footing * (Hdb / 2.0)

    LS_stem = gs * heq_tb * Ka * Beff * Htb
    M_LS_stem = LS_stem * (Htb / 2.0)

    # 5. HOẠT TẢI XE HL-93 VÀ HỆ SỐ LÀN m
    # Phản lực xe tải thiết kế lên 1 mố:
    # Xe tải: 35kN @0, 145kN @4.3m, 145kN @8.6m
    # R_truck = (145*Ls + 145*(Ls - 4.3) + 35*(Ls - 8.6)) / Ls
    Ls = model.Ls
    R_truck = (145.0 * Ls + 145.0 * max(0.0, Ls - 4.3) + 35.0 * max(0.0, Ls - 8.6)) / Ls
    # Xe 2 trục (Tandem): 110kN @0, 110kN @1.2m
    R_tandem = (110.0 * Ls + 110.0 * max(0.0, Ls - 1.2)) / Ls
    R_axle_max = max(R_truck, R_tandem)
    R_lane = model.qlan * Ls / 2.0

    # Phản lực 1 làn xe (chưa nhân m)
    R_1lane_no_m = R_axle_max * (1.0 + model.IM) + R_lane

    # Bảng các trường hợp xếp k làn (k = 1..num_lanes)
    # Xét lệch tâm ngang cầu: khoảng cách từ tim cầu đến trọng tâm xe ngoài cùng
    # Làn 1: y_lane = (Bxe/2 - 0.6 - 1.5) v.v.
    # Để tính Mx ngang cầu: Mx = N_k * e_y
    ll_cases_footing: Dict[str, LoadVector] = {}
    ll_cases_stem: Dict[str, LoadVector] = {}

    for k in range(1, model.num_lanes + 1):
        m_k = get_multi_lane_factor(k)
        N_k = k * R_1lane_no_m * m_k

        # Độ lệch tâm ngang cầu ey cho k làn xếp dồn 1 bên
        # Mỗi làn rộng 3.6m hoặc Bxe/k, tim xe dồn về mép lan can
        w_lane = 3.6
        first_lane_y = model.width_Bxe / 2.0 - 0.6 - 1.8 # tim làn ngoài cùng
        lane_positions = [first_lane_y - i * w_lane for i in range(k)]
        avg_ey = sum(lane_positions) / k if k > 0 else 0.0

        Mx_ecc = N_k * avg_ey
        My_k_footing = N_k * y_goi
        My_k_stem = N_k * (y_goi - y_than)

        # Trường hợp lệch tâm
        case_name_ecc = f"LL_IM_{k}lan_lech"
        ll_cases_footing[case_name_ecc] = LoadVector(
            name=f"LL+IM ({k} làn lệch tâm)", N=N_k, Mx=Mx_ecc, My=My_k_footing
        )
        ll_cases_stem[case_name_ecc] = LoadVector(
            name=f"LL+IM ({k} làn lệch tâm)", N=N_k, Mx=Mx_ecc, My=My_k_stem
        )

        # Trường hợp đúng tâm (Mx = 0)
        case_name_cen = f"LL_IM_{k}lan_dung"
        ll_cases_footing[case_name_cen] = LoadVector(
            name=f"LL+IM ({k} làn đúng tâm)", N=N_k, Mx=0.0, My=My_k_footing
        )
        ll_cases_stem[case_name_cen] = LoadVector(
            name=f"LL+IM ({k} làn đúng tâm)", N=N_k, Mx=0.0, My=My_k_stem
        )

    # 6. LỰC HÃM XE BR VÀ LỰC MA SÁT GỐI FR
    # Lực hãm BR (Điều 6.4): chỉ truyền xuống mố khi gối CỐ ĐỊNH (bearing_type == 1)
    # BR = max(0.25 * 325, 0.05 * (325 + qlan * Ls)) = max(81.25, 16.25 + 0.05*9.3*Ls)
    BR_1lane = max(0.25 * 325.0, 0.05 * (325.0 + model.qlan * Ls))
    m_all = get_multi_lane_factor(model.num_lanes)
    BR_total = model.num_lanes * BR_1lane * m_all if model.bearing_type == 1 else 0.0
    # Cao độ đặt lực hãm: 1.8m trên mặt cầu -> tính đến đáy bệ = Hdb + h_bearing + h_girder + t_deck + 1.8
    z_BR_footing = Hdb + model.h_bearing + model.h_girder + model.t_deck + 1.8
    z_BR_stem = Htb + model.h_bearing + model.h_girder + model.t_deck + 1.8
    M_BR_footing = BR_total * z_BR_footing
    M_BR_stem = BR_total * z_BR_stem

    # Lực ma sát gối FR (gối di động bearing_type == 0)
    # FR = mu * (DC1 + DW + LL_max)
    N_LL_max = model.num_lanes * R_1lane_no_m * m_all
    FR_val = model.friction_mu * (DC1 + DW + N_LL_max) if model.bearing_type == 0 else 0.0
    z_FR_footing = Hdb + model.h_bearing
    z_FR_stem = Htb + model.h_bearing
    M_FR_footing = FR_val * z_FR_footing
    M_FR_stem = FR_val * z_FR_stem

    # 7. GIÓ (WS, WL)
    # V thiết kế
    V_des = model.VB * model.S_factor
    q_wind_des = 0.5 * 1.25e-3 * (V_des ** 2) # kN/m²

    # V = 25 m/s cho CĐ V và SD I
    q_wind_25 = 0.5 * 1.25e-3 * (25.0 ** 2)

    # Diện tích chắn gió KCN: A_kcn = (h_girder + t_deck + h_barrier) * Ls / 2
    h_wind_kcn = model.h_girder + model.t_deck + model.h_barrier
    A_wind_kcn = h_wind_kcn * (Ls / 2.0)
    WS_kcn_ngang_des = q_wind_des * model.Cd_kcn * A_wind_kcn
    WS_kcn_ngang_25 = q_wind_25 * model.Cd_kcn * A_wind_kcn

    # Gió lên thân mố: A_than = H6 * (C1 / sin a)
    A_wind_than = model.H6 * (model.C1 / sin_a)
    WS_than_ngang_des = q_wind_des * model.Cx_sub * A_wind_than
    WS_than_ngang_25 = q_wind_25 * model.Cx_sub * A_wind_than

    WS_ngang_des = WS_kcn_ngang_des + WS_than_ngang_des
    WS_ngang_25 = WS_kcn_ngang_des + WS_than_ngang_25

    # Gió dọc KCN = 0.25 * Gió ngang KCN
    WS_doc_des = 0.25 * WS_kcn_ngang_des
    WS_doc_25 = 0.25 * WS_kcn_ngang_25

    # Cao độ đặt gió KCN và thân mố
    z_kcn_footing = Hdb + model.h_bearing + h_wind_kcn / 2.0
    z_kcn_stem = Htb + model.h_bearing + h_wind_kcn / 2.0
    z_than_footing = model.H1 + model.H6 / 2.0
    z_than_stem = model.H6 / 2.0

    Mx_WS_ngang_des_footing = WS_kcn_ngang_des * z_kcn_footing + WS_than_ngang_des * z_than_footing
    Mx_WS_ngang_des_stem = WS_kcn_ngang_des * z_kcn_stem + WS_than_ngang_des * z_than_stem

    Mx_WS_ngang_25_footing = WS_kcn_ngang_25 * z_kcn_footing + WS_than_ngang_25 * z_than_footing
    Mx_WS_ngang_25_stem = WS_kcn_ngang_25 * z_kcn_stem + WS_than_ngang_25 * z_than_stem

    My_WS_doc_des_footing = WS_doc_des * z_kcn_footing
    My_WS_doc_des_stem = WS_doc_des * z_kcn_stem

    My_WS_doc_25_footing = WS_doc_25 * z_kcn_footing
    My_WS_doc_25_stem = WS_doc_25 * z_kcn_stem

    # Gió thẳng đứng Pv = 0.00045 * V² * A_deck (Điều 8.2)
    A_deck = model.width_W * (Ls / 2.0)
    Pv_des = 0.00045 * (V_des ** 2) * A_deck
    M_Pv_footing = Pv_des * y_goi
    M_Pv_stem = Pv_des * (y_goi - y_than)

    # Gió trên hoạt tải WL (Điều 8.1.3): 1.46 kN/m ngang, 0.55 kN/m dọc
    WL_ngang = 1.46 * (Ls / 2.0)
    WL_doc = 0.55 * (Ls / 2.0)
    z_WL_footing = Hdb + model.h_bearing + model.h_girder + model.t_deck + 1.8
    z_WL_stem = Htb + model.h_bearing + model.h_girder + model.t_deck + 1.8
    Mx_WL_footing = WL_ngang * z_WL_footing
    Mx_WL_stem = WL_ngang * z_WL_stem
    My_WL_footing = WL_doc * z_WL_footing
    My_WL_stem = WL_doc * z_WL_stem

    # 8. ĐỘNG ĐẤT (EQ) VÀ MONONOBE-OKABE (ΔEAE)
    # Hệ số động đất Csm (Điều 9.6): Csm = 1.2 * A * S / T^(2/3) <= 2.5 * A
    # Thường lấy chặn trên Csm = 2.5 * A cho kết cấu cứng mố cầu
    Csm = min(2.5 * model.accel_A, (1.2 * model.accel_A * model.S_seismic) / (0.5 ** (2.0 / 3.0)))

    # Lực quán tính KCN: F_EQ_kcn = Csm * (DC1 + DW + 0.5*N_LL) / R_super
    F_EQ_kcn = Csm * (DC1 + DW + 0.5 * N_LL_max) / model.R_super

    # Lực quán tính thân bệ mố: F_EQ_sub = Csm * DC2_total / model.R_sub
    F_EQ_sub_footing = Csm * DC2_total / model.R_sub
    F_EQ_sub_stem = Csm * DC2_stem / model.R_sub

    # Áp lực đất động Mononobe-Okabe ΔEAE:
    # kh = model.kh_seismic; kv = 0
    # theta_EQ = arctan(kh / (1 - kv))
    kh = model.kh_seismic
    theta_EQ = math.atan(kh)
    phi_r = math.radians(model.phi)
    delta_r = math.radians(model.delta)
    beta_r = math.radians(model.beta)

    num_KAE = math.sin(phi_r - theta_EQ) ** 2
    den_KAE_1 = math.cos(theta_EQ) * (math.sin(math.pi/2.0 - theta_EQ) ** 2) * math.sin(math.pi/2.0 + theta_EQ + delta_r)
    term_KAE = math.sin(phi_r + delta_r) * math.sin(phi_r - theta_EQ - beta_r) / (math.sin(math.pi/2.0 + theta_EQ + delta_r) * math.cos(beta_r))
    term_KAE = max(0.0, term_KAE)
    den_KAE_2 = (1.0 + math.sqrt(term_KAE)) ** 2
    KAE = num_KAE / (den_KAE_1 * den_KAE_2) if den_KAE_1 * den_KAE_2 > 0 else Ka

    # Delta KAE = KAE - Ka
    dKAE = max(0.0, KAE - Ka)
    delta_EAE_footing = 0.5 * gs * (Hdb ** 2) * dKAE * Beff
    delta_EAE_stem = 0.5 * gs * (Htb ** 2) * dKAE * Beff

    # Điểm đặt ΔEAE tại 0.6 H
    M_dEAE_footing = delta_EAE_footing * (0.6 * Hdb)
    M_dEAE_stem = delta_EAE_stem * (0.6 * Htb)

    # Tổng EQ dọc: F_EQ_kcn + F_EQ_sub + ΔEAE
    EQ_doc_footing = F_EQ_kcn + F_EQ_sub_footing + delta_EAE_footing
    My_EQ_doc_footing = F_EQ_kcn * z_kcn_footing + F_EQ_sub_footing * (Hdb / 2.0) + M_dEAE_footing

    EQ_doc_stem = F_EQ_kcn + F_EQ_sub_stem + delta_EAE_stem
    My_EQ_doc_stem = F_EQ_kcn * z_kcn_stem + F_EQ_sub_stem * (Htb / 2.0) + M_dEAE_stem

    # EQ ngang: F_EQ_kcn + F_EQ_sub
    EQ_ngang_footing = F_EQ_kcn + F_EQ_sub_footing
    Mx_EQ_ngang_footing = F_EQ_kcn * z_kcn_footing + F_EQ_sub_footing * (Hdb / 2.0)

    EQ_ngang_stem = F_EQ_kcn + F_EQ_sub_stem
    Mx_EQ_ngang_stem = F_EQ_kcn * z_kcn_stem + F_EQ_sub_stem * (Htb / 2.0)

    # ĐÓNG GÓI CÁC TẢI TRỌNG VÀO TỪNG TẬP VECTOR
    loads_footing: Dict[str, LoadVector] = {
        "DC1": LoadVector("DC1 (KCN)", N=DC1, My=M_DC1_footing),
        "DW": LoadVector("DW (Lớp phủ)", N=DW, My=M_DW_footing),
        "DC2": LoadVector("DC2 (Bản thân mố)", N=DC2_total, My=M_DC2_footing),
        "EV": LoadVector("EV (Đất trên bệ)", N=EV_total, My=M_EV_footing),
        "VS": LoadVector("VS (Hoạt tải đứng trên bệ)", N=VS_total, My=M_VS_footing),
        "EH": LoadVector("EH (Áp lực đất ngang)", Hx=EH_footing, My=M_EH_footing),
        "LS": LoadVector("LS (Hoạt tải đắp ngang)", Hx=LS_footing, My=M_LS_footing),
        "BR": LoadVector("BR (Lực hãm xe)", Hx=BR_total, My=M_BR_footing),
        "FR": LoadVector("FR (Ma sát gối)", Hx=FR_val, My=M_FR_footing),
        "WS_ngang_des": LoadVector("WS ngang Vtk", Hy=WS_ngang_des, Mx=Mx_WS_ngang_des_footing),
        "WS_doc_des": LoadVector("WS dọc Vtk", Hx=WS_doc_des, My=My_WS_doc_des_footing),
        "WS_ngang_25": LoadVector("WS ngang 25m/s", Hy=WS_ngang_25, Mx=Mx_WS_ngang_25_footing),
        "WS_doc_25": LoadVector("WS dọc 25m/s", Hx=WS_doc_25, My=My_WS_doc_25_footing),
        "WS_dung": LoadVector("WS thẳng đứng", N=Pv_des, My=M_Pv_footing),
        "WL_ngang": LoadVector("WL ngang", Hy=WL_ngang, Mx=Mx_WL_footing),
        "WL_doc": LoadVector("WL dọc", Hx=WL_doc, My=My_WL_footing),
        "EQ_doc": LoadVector("EQ dọc (+ΔEAE)", Hx=EQ_doc_footing, My=My_EQ_doc_footing),
        "EQ_ngang": LoadVector("EQ ngang", Hy=EQ_ngang_footing, Mx=Mx_EQ_ngang_footing),
    }
    loads_footing.update(ll_cases_footing)

    loads_stem: Dict[str, LoadVector] = {
        "DC1": LoadVector("DC1 (KCN)", N=DC1, My=M_DC1_stem),
        "DW": LoadVector("DW (Lớp phủ)", N=DW, My=M_DW_stem),
        "DC2": LoadVector("DC2 (Bản thân mố)", N=DC2_stem, My=M_DC2_stem),
        "EV": LoadVector("EV (Đất trên bệ)", N=0.0, My=0.0),
        "VS": LoadVector("VS (Hoạt tải đứng)", N=0.0, My=0.0),
        "EH": LoadVector("EH (Áp lực đất ngang)", Hx=EH_stem, My=M_EH_stem),
        "LS": LoadVector("LS (Hoạt tải đắp ngang)", Hx=LS_stem, My=M_LS_stem),
        "BR": LoadVector("BR (Lực hãm xe)", Hx=BR_total, My=M_BR_stem),
        "FR": LoadVector("FR (Ma sát gối)", Hx=FR_val, My=M_FR_stem),
        "WS_ngang_des": LoadVector("WS ngang Vtk", Hy=WS_ngang_des, Mx=Mx_WS_ngang_des_stem),
        "WS_doc_des": LoadVector("WS dọc Vtk", Hx=WS_doc_des, My=My_WS_doc_des_stem),
        "WS_ngang_25": LoadVector("WS ngang 25m/s", Hy=WS_ngang_25, Mx=Mx_WS_ngang_25_stem),
        "WS_doc_25": LoadVector("WS dọc 25m/s", Hx=WS_doc_25, My=My_WS_doc_25_stem),
        "WS_dung": LoadVector("WS thẳng đứng", N=Pv_des, My=M_Pv_stem),
        "WL_ngang": LoadVector("WL ngang", Hy=WL_ngang, Mx=Mx_WL_stem),
        "WL_doc": LoadVector("WL dọc", Hx=WL_doc, My=My_WL_stem),
        "EQ_doc": LoadVector("EQ dọc (+ΔEAE)", Hx=EQ_doc_stem, My=My_EQ_doc_stem),
        "EQ_ngang": LoadVector("EQ ngang", Hy=EQ_ngang_stem, Mx=Mx_EQ_ngang_stem),
    }
    loads_stem.update(ll_cases_stem)

    return AbutmentLoadsSummary(
        loads_stem_base=loads_stem,
        loads_footing_base=loads_footing,
        DC2_total=DC2_total,
        EV_total=EV_total,
        EH_footing=EH_footing,
        EH_stem=EH_stem,
        LS_footing=LS_footing,
        LS_stem=LS_stem,
        delta_EAE_footing=delta_EAE_footing,
        delta_EAE_stem=delta_EAE_stem,
        FR_val=FR_val,
        Ka=Ka,
        KAE=KAE
    )
