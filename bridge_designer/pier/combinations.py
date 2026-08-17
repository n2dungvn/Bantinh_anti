"""
Module: pier.combinations
Tạo lập các trường hợp tổ hợp tải trọng thiết kế cho Trụ cầu
theo TCVN 11823-3:2017.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple
from ..abutment.loads import LoadVector
from ..abutment.combinations import CombinationResult


def generate_pier_combinations(
    loads_dict: Dict[str, LoadVector],
    num_lanes: int
) -> List[CombinationResult]:
    """
    Sinh các tổ hợp tải trọng thiết kế cho trụ cầu
    """
    results: List[CombinationResult] = []

    def get_load(key: str) -> LoadVector:
        return loads_dict.get(key, LoadVector(key))

    dc1 = get_load("DC1")
    dc2 = get_load("DC2")
    dw = get_load("DW")
    wb = get_load("WB")
    br = get_load("BR")
    tu_pos = get_load("TU_pos")
    tu_neg = get_load("TU_neg")
    fr_pos = get_load("FR_pos")
    fr_neg = get_load("FR_neg")
    ws_doc_des = get_load("WS_doc_des")
    ws_ngang_des = get_load("WS_ngang_des")
    ws_doc_25 = get_load("WS_doc_25")
    ws_ngang_25 = get_load("WS_ngang_25")
    wl_doc = get_load("WL_doc")
    wl_ngang = get_load("WL_ngang")
    wa = get_load("WA")
    eq_doc = get_load("EQ_doc")
    eq_ngang = get_load("EQ_ngang")
    ct = get_load("CT")

    # 1. CƯỜNG ĐỘ I (Strength I)
    # 1.1 Chất 2 nhịp lệch tâm (k = 1..num_lanes)
    for k in range(1, num_lanes + 1):
        ll = get_load(f"LL_2span_{k}lan_lech")
        N = (1.25 * (dc1.N + dc2.N) +
             1.50 * dw.N +
             1.00 * wb.N +
             1.75 * ll.N)
        Hx = 1.75 * br.Hx + 1.00 * fr_pos.Hx
        Hy = 0.0
        Mx = 1.75 * ll.Mx
        My = (1.25 * (dc1.My + dc2.My) +
              1.50 * dw.My +
              1.75 * ll.My +
              1.75 * br.My +
              1.00 * fr_pos.My +
              0.50 * tu_pos.My)
        results.append(CombinationResult(
            comb_id=f"CD_Ia_2span_{k}lan_lech",
            comb_name=f"CĐ I(a) max - 2 nhịp lệch tâm {k} làn",
            limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 1.2 Chất 2 nhịp đúng tâm (k = 1..num_lanes)
    for k in range(1, num_lanes + 1):
        ll = get_load(f"LL_2span_{k}lan_dung")
        N = (1.25 * (dc1.N + dc2.N) +
             1.50 * dw.N +
             1.00 * wb.N +
             1.75 * ll.N)
        Hx = 1.75 * br.Hx + 1.00 * fr_pos.Hx
        Hy = 0.0
        Mx = 0.0
        My = (1.25 * (dc1.My + dc2.My) +
              1.50 * dw.My +
              1.75 * br.My +
              1.00 * fr_pos.My +
              0.50 * tu_pos.My)
        results.append(CombinationResult(
            comb_id=f"CD_Ia_2span_{k}lan_dung",
            comb_name=f"CĐ I(a) max - 2 nhịp đúng tâm {k} làn",
            limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 1.3 Chất 1 nhịp (My max) (k = 1..num_lanes)
    for k in range(1, num_lanes + 1):
        ll = get_load(f"LL_1span_{k}lan")
        N = (1.25 * (dc1.N + dc2.N) +
             1.50 * dw.N +
             1.00 * wb.N +
             1.75 * ll.N)
        Hx = 1.75 * br.Hx + 1.00 * fr_pos.Hx
        Hy = 0.0
        Mx = 1.75 * ll.Mx
        My = (1.25 * (dc1.My + dc2.My) +
              1.50 * dw.My +
              1.75 * ll.My +
              1.75 * br.My +
              1.00 * fr_pos.My +
              0.50 * tu_pos.My)
        results.append(CombinationResult(
            comb_id=f"CD_Ia_1span_{k}lan",
            comb_name=f"CĐ I(a) max - 1 nhịp {k} làn",
            limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 1.4 CĐ I(b) min (gamma_DC min = 0.90)
    for k in [1, num_lanes]:
        ll = get_load(f"LL_1span_{k}lan")
        N = (0.90 * (dc1.N + dc2.N) +
             0.65 * dw.N +
             1.00 * wb.N +
             1.75 * ll.N)
        Hx = 1.75 * br.Hx + 1.00 * fr_pos.Hx
        Hy = 0.0
        Mx = 1.75 * ll.Mx
        My = (0.90 * (dc1.My + dc2.My) +
              0.65 * dw.My +
              1.75 * ll.My +
              1.75 * br.My +
              1.00 * fr_pos.My)
        results.append(CombinationResult(
            comb_id=f"CD_Ib_min_1span_{k}lan",
            comb_name=f"CĐ I(b) min - 1 nhịp {k} làn",
            limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 2. CƯỜNG ĐỘ III (Strength III - Gió thiết kế, không hoạt tải)
    # 2a. gamma_DC max
    N_cd3_max = 1.25 * (dc1.N + dc2.N) + 1.50 * dw.N + 1.00 * wb.N
    Hx_cd3 = 1.40 * ws_doc_des.Hx + 1.00 * fr_pos.Hx + 1.00 * wa.Hx
    Hy_cd3 = 1.40 * ws_ngang_des.Hy
    Mx_cd3 = 1.40 * ws_ngang_des.Mx
    My_cd3_max = (1.25 * (dc1.My + dc2.My) +
                  1.50 * dw.My +
                  1.40 * ws_doc_des.My +
                  1.00 * wa.My +
                  1.00 * fr_pos.My +
                  0.50 * tu_pos.My)
    results.append(CombinationResult(
        comb_id="CD_IIIa_max", comb_name="CĐ III(a) max", limit_state_group="STRENGTH",
        N=N_cd3_max, Hx=Hx_cd3, Hy=Hy_cd3, Mx=Mx_cd3, My=My_cd3_max
    ))

    # 2b. gamma_DC min
    N_cd3_min = 0.90 * (dc1.N + dc2.N) + 0.65 * dw.N + 1.00 * wb.N
    My_cd3_min = (0.90 * (dc1.My + dc2.My) +
                  0.65 * dw.My +
                  1.40 * ws_doc_des.My +
                  1.00 * wa.My +
                  1.00 * fr_pos.My)
    results.append(CombinationResult(
        comb_id="CD_IIIb_min", comb_name="CĐ III(b) min", limit_state_group="STRENGTH",
        N=N_cd3_min, Hx=Hx_cd3, Hy=Hy_cd3, Mx=Mx_cd3, My=My_cd3_min
    ))

    # 3. CƯỜNG ĐỘ IV (Strength IV)
    N_cd4 = 1.50 * (dc1.N + dc2.N) + 1.50 * dw.N + 1.00 * wb.N
    My_cd4 = 1.50 * (dc1.My + dc2.My) + 1.50 * dw.My + 1.00 * wa.My
    results.append(CombinationResult(
        comb_id="CD_IV", comb_name="CĐ IV", limit_state_group="STRENGTH",
        N=N_cd4, Hx=1.00 * wa.Hx, Hy=0.0, Mx=0.0, My=My_cd4
    ))

    # 4. CƯỜNG ĐỘ V (Strength V - Gió 25m/s + Hoạt tải)
    for k in [1, num_lanes]:
        ll = get_load(f"LL_2span_{k}lan_lech")
        N = (1.25 * (dc1.N + dc2.N) +
             1.50 * dw.N +
             1.00 * wb.N +
             1.35 * ll.N)
        Hx = 1.35 * br.Hx + 0.40 * ws_doc_25.Hx + 1.00 * wl_doc.Hx + 1.00 * wa.Hx + 1.00 * fr_pos.Hx
        Hy = 0.40 * ws_ngang_25.Hy + 1.00 * wl_ngang.Hy
        Mx = 1.35 * ll.Mx + 0.40 * ws_ngang_25.Mx + 1.00 * wl_ngang.Mx
        My = (1.25 * (dc1.My + dc2.My) +
              1.50 * dw.My +
              1.35 * ll.My +
              1.35 * br.My +
              0.40 * ws_doc_25.My +
              1.00 * wl_doc.My +
              1.00 * wa.My +
              1.00 * fr_pos.My +
              0.50 * tu_pos.My)
        results.append(CombinationResult(
            comb_id=f"CD_V_{k}lan", comb_name=f"CĐ V - {k} làn", limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 5. SỬ DỤNG I (Service I)
    # 5.1 2 nhịp lệch
    for k in range(1, num_lanes + 1):
        ll = get_load(f"LL_2span_{k}lan_lech")
        N = 1.00 * (dc1.N + dc2.N + dw.N + wb.N + ll.N)
        Hx = 1.00 * br.Hx + 0.30 * ws_doc_25.Hx + 1.00 * wl_doc.Hx + 1.00 * wa.Hx + 1.00 * fr_pos.Hx
        Hy = 0.30 * ws_ngang_25.Hy + 1.00 * wl_ngang.Hy
        Mx = 1.00 * ll.Mx + 0.30 * ws_ngang_25.Mx + 1.00 * wl_ngang.Mx
        My = (1.00 * (dc1.My + dc2.My + dw.My + ll.My) +
              1.00 * br.My +
              0.30 * ws_doc_25.My +
              1.00 * wl_doc.My +
              1.00 * wa.My +
              1.00 * fr_pos.My +
              1.00 * tu_pos.My)
        results.append(CombinationResult(
            comb_id=f"SD_I_2span_{k}lan_lech", comb_name=f"SD I - 2 nhịp lệch tâm {k} làn", limit_state_group="SERVICE",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 5.2 2 nhịp đúng
    for k in range(1, num_lanes + 1):
        ll = get_load(f"LL_2span_{k}lan_dung")
        N = 1.00 * (dc1.N + dc2.N + dw.N + wb.N + ll.N)
        Hx = 1.00 * br.Hx + 1.00 * wa.Hx + 1.00 * fr_pos.Hx
        Hy = 0.0
        Mx = 0.0
        My = (1.00 * (dc1.My + dc2.My + dw.My) +
              1.00 * br.My +
              1.00 * wa.My +
              1.00 * fr_pos.My +
              1.00 * tu_pos.My)
        results.append(CombinationResult(
            comb_id=f"SD_I_2span_{k}lan_dung", comb_name=f"SD I - 2 nhịp đúng tâm {k} làn", limit_state_group="SERVICE",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 5.3 1 nhịp
    for k in range(1, num_lanes + 1):
        ll = get_load(f"LL_1span_{k}lan")
        N = 1.00 * (dc1.N + dc2.N + dw.N + wb.N + ll.N)
        Hx = 1.00 * br.Hx + 1.00 * wa.Hx + 1.00 * fr_pos.Hx
        Hy = 0.0
        Mx = 1.00 * ll.Mx
        My = (1.00 * (dc1.My + dc2.My + dw.My + ll.My) +
              1.00 * br.My +
              1.00 * wa.My +
              1.00 * fr_pos.My +
              1.00 * tu_pos.My)
        results.append(CombinationResult(
            comb_id=f"SD_I_1span_{k}lan", comb_name=f"SD I - 1 nhịp {k} làn", limit_state_group="SERVICE",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 6. SỬ DỤNG III (Service III - Kiểm ứng suất kéo xà mũ DƯL: gamma_LL = 0.80)
    for k in [1, num_lanes]:
        ll = get_load(f"LL_2span_{k}lan_lech")
        N_sd3 = 1.00 * (dc1.N + dc2.N + dw.N + wb.N) + 0.80 * ll.N
        Mx_sd3 = 0.80 * ll.Mx
        My_sd3 = 1.00 * (dc1.My + dc2.My + dw.My) + 0.80 * ll.My
        results.append(CombinationResult(
            comb_id=f"SD_III_{k}lan", comb_name=f"SD III - {k} làn", limit_state_group="SERVICE",
            N=N_sd3, Hx=0.0, Hy=0.0, Mx=Mx_sd3, My=My_sd3
        ))

    # 7. ĐẶC BIỆT I (Động đất)
    ll_eq = get_load(f"LL_2span_{num_lanes}lan_dung")
    N_eq = 1.25 * (dc1.N + dc2.N) + 1.50 * dw.N + 1.00 * wb.N + 0.50 * ll_eq.N
    # EQ dọc
    Hx_eq_doc = 1.00 * eq_doc.Hx + 1.00 * wa.Hx
    My_eq_doc = (1.25 * (dc1.My + dc2.My) +
                 1.50 * dw.My +
                 1.00 * eq_doc.My +
                 1.00 * wa.My)
    results.append(CombinationResult(
        comb_id="DB_I_EQ_doc", comb_name="ĐB I - EQ dọc", limit_state_group="EXTREME",
        N=N_eq, Hx=Hx_eq_doc, Hy=0.0, Mx=0.0, My=My_eq_doc
    ))

    # EQ ngang
    Hy_eq_ngang = 1.00 * eq_ngang.Hy
    Mx_eq_ngang = 1.00 * eq_ngang.Mx
    results.append(CombinationResult(
        comb_id="DB_I_EQ_ngang", comb_name="ĐB I - EQ ngang", limit_state_group="EXTREME",
        N=N_eq, Hx=1.00 * wa.Hx, Hy=Hy_eq_ngang, Mx=Mx_eq_ngang, My=My_eq_doc - 1.00 * eq_doc.My
    ))

    # 8. ĐẶC BIỆT II (Va xe CT = 1800 kN)
    if ct.Hx > 0:
        Hx_ct = 1.00 * ct.Hx + 1.00 * wa.Hx
        My_ct = (1.25 * (dc1.My + dc2.My) +
                 1.50 * dw.My +
                 0.50 * ll_eq.My +
                 1.00 * ct.My +
                 1.00 * wa.My)
        results.append(CombinationResult(
            comb_id="DB_II_VaXe", comb_name="ĐB II - Va xe (CT=1800kN)", limit_state_group="EXTREME",
            N=N_eq, Hx=Hx_ct, Hy=0.0, Mx=0.0, My=My_ct
        ))

    # 9. ĐẶC BIỆT III (Va tàu CV)
    cv = get_load("CV")
    if cv.Hx > 0:
        Hx_cv = 1.00 * cv.Hx + 1.00 * wa.Hx
        My_cv = (1.25 * (dc1.My + dc2.My) +
                 1.50 * dw.My +
                 0.50 * ll_eq.My +
                 1.00 * cv.My +
                 1.00 * wa.My)
        results.append(CombinationResult(
            comb_id="DB_III_VaTau", comb_name="ĐB III - Va tàu (CV)", limit_state_group="EXTREME",
            N=N_eq, Hx=Hx_cv, Hy=0.0, Mx=0.0, My=My_cv
        ))

    return results
