"""
Module: abutment.combinations
Tạo lập các trường hợp tổ hợp tải trọng thiết kế cho Mố cầu
theo TCVN 11823-3:2017 (Bảng 3 & Bảng 4).
Bao gồm:
- Cường độ I: Các trường hợp 1..n làn (lệch tâm / đúng tâm), gamma_DC max và min
- Cường độ II: Xe đặc biệt
- Cường độ III: Gió bão thiết kế (V_des)
- Cường độ IV: Tỷ số tĩnh tải lớn (gamma_DC = 1.50)
- Cường độ V: Gió vừa (25 m/s) + Hoạt tải
- Sử dụng I: Điều kiện khai thác tiêu chuẩn (nứt, độ võng)
- Sử dụng IV: Ứng suất nền móng (gió 0.70)
- Đặc biệt I: Động đất dọc và ngang (+ΔEAE)
- Mỏi I: Tải trọng mỏi
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple
from .loads import LoadVector, AbutmentLoadsSummary
from ..tcvn.loads import get_standard_load_combinations, LoadCombinationFactors


@dataclass
class CombinationResult:
    """Kết quả nội lực của một tổ hợp cụ thể"""
    comb_id: str
    comb_name: str
    limit_state_group: str     # 'STRENGTH', 'SERVICE', 'EXTREME', 'FATIGUE'
    N: float                   # Lực dọc (kN, nén dương)
    Hx: float                  # Lực cắt dọc cầu (kN)
    Hy: float                  # Lực cắt ngang cầu (kN)
    Mx: float                  # Mô men uốn ngang cầu (kN.m)
    My: float                  # Mô men uốn dọc cầu (kN.m)


def generate_abutment_combinations(
    loads_dict: Dict[str, LoadVector],
    num_lanes: int
) -> List[CombinationResult]:
    """
    Sinh các tổ hợp tải trọng thiết kế đầy đủ từ tập tải trọng thành phần
    """
    results: List[CombinationResult] = []

    # Danh sách các trường hợp làn xe
    lane_keys_ecc = [f"LL_IM_{k}lan_lech" for k in range(1, num_lanes + 1)]
    lane_keys_cen = [f"LL_IM_{k}lan_dung" for k in range(1, num_lanes + 1)]

    # 1. CƯỜNG ĐỘ I (Strength I)
    # 1a. gamma_DC max = 1.25, gamma_DW = 1.50, gamma_EV = 1.35, gamma_EH = 1.50, gamma_LS = 1.75, gamma_LL = 1.75
    # Trường hợp lệch tâm
    for k, key in enumerate(lane_keys_ecc, 1):
        ll = loads_dict.get(key, LoadVector(key))
        N = (1.25 * (loads_dict["DC1"].N + loads_dict["DC2"].N) +
             1.50 * loads_dict["DW"].N +
             1.35 * loads_dict["EV"].N +
             1.75 * loads_dict["VS"].N +
             1.75 * ll.N)
        Hx = (1.50 * loads_dict["EH"].Hx +
              1.75 * loads_dict["LS"].Hx +
              1.00 * loads_dict["FR"].Hx)
        Hy = 0.0
        Mx = 1.75 * ll.Mx
        My = (1.25 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
              1.50 * loads_dict["DW"].My +
              1.35 * loads_dict["EV"].My +
              1.75 * loads_dict["VS"].My +
              1.75 * ll.My +
              1.50 * loads_dict["EH"].My +
              1.75 * loads_dict["LS"].My +
              1.00 * loads_dict["FR"].My)
        results.append(CombinationResult(
            comb_id=f"CD_Ia_max_{k}lan_lech",
            comb_name=f"CĐ I(a) max - {k} làn lệch",
            limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # Trường hợp đúng tâm (Mx = 0)
    for k, key in enumerate(lane_keys_cen, 1):
        ll = loads_dict.get(key, LoadVector(key))
        N = (1.25 * (loads_dict["DC1"].N + loads_dict["DC2"].N) +
             1.50 * loads_dict["DW"].N +
             1.35 * loads_dict["EV"].N +
             1.75 * loads_dict["VS"].N +
             1.75 * ll.N)
        Hx = (1.50 * loads_dict["EH"].Hx +
              1.75 * loads_dict["LS"].Hx +
              1.00 * loads_dict["FR"].Hx)
        Hy = 0.0
        Mx = 0.0
        My = (1.25 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
              1.50 * loads_dict["DW"].My +
              1.35 * loads_dict["EV"].My +
              1.75 * loads_dict["VS"].My +
              1.75 * ll.My +
              1.50 * loads_dict["EH"].My +
              1.75 * loads_dict["LS"].My +
              1.00 * loads_dict["FR"].My)
        results.append(CombinationResult(
            comb_id=f"CD_Ia_max_{k}lan_dung",
            comb_name=f"CĐ I(a) max - {k} làn đúng",
            limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 1b. gamma_DC min = 0.90, gamma_DW = 0.65, gamma_EV = 1.00 (gây trượt / lật / kéo bất lợi)
    for k, key in enumerate(lane_keys_ecc, 1):
        ll = loads_dict.get(key, LoadVector(key))
        N = (0.90 * (loads_dict["DC1"].N + loads_dict["DC2"].N) +
             0.65 * loads_dict["DW"].N +
             1.00 * loads_dict["EV"].N +
             1.75 * loads_dict["VS"].N +
             1.75 * ll.N)
        Hx = (1.50 * loads_dict["EH"].Hx +
              1.75 * loads_dict["LS"].Hx +
              1.00 * loads_dict["FR"].Hx)
        Hy = 0.0
        Mx = 1.75 * ll.Mx
        My = (0.90 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
              0.65 * loads_dict["DW"].My +
              1.00 * loads_dict["EV"].My +
              1.75 * loads_dict["VS"].My +
              1.75 * ll.My +
              1.50 * loads_dict["EH"].My +
              1.75 * loads_dict["LS"].My +
              1.00 * loads_dict["FR"].My)
        results.append(CombinationResult(
            comb_id=f"CD_Ib_min_{k}lan_lech",
            comb_name=f"CĐ I(b) min - {k} làn lệch",
            limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 2. CƯỜNG ĐỘ III (Strength III - Gió bão thiết kế, không có hoạt tải xe)
    # 2a. gamma_DC max
    N_cd3_max = 1.25 * (loads_dict["DC1"].N + loads_dict["DC2"].N) + 1.50 * loads_dict["DW"].N + 1.35 * loads_dict["EV"].N
    Hx_cd3 = 1.50 * loads_dict["EH"].Hx + 1.40 * loads_dict["WS_doc_des"].Hx + 1.00 * loads_dict["FR"].Hx
    Hy_cd3 = 1.40 * loads_dict["WS_ngang_des"].Hy
    Mx_cd3 = 1.40 * loads_dict["WS_ngang_des"].Mx
    My_cd3_max = (1.25 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
                  1.50 * loads_dict["DW"].My +
                  1.35 * loads_dict["EV"].My +
                  1.50 * loads_dict["EH"].My +
                  1.40 * loads_dict["WS_doc_des"].My +
                  1.00 * loads_dict["FR"].My)
    results.append(CombinationResult(
        comb_id="CD_IIIa_max", comb_name="CĐ III(a) max", limit_state_group="STRENGTH",
        N=N_cd3_max, Hx=Hx_cd3, Hy=Hy_cd3, Mx=Mx_cd3, My=My_cd3_max
    ))

    # 2b. gamma_DC min
    N_cd3_min = 0.90 * (loads_dict["DC1"].N + loads_dict["DC2"].N) + 0.65 * loads_dict["DW"].N + 1.00 * loads_dict["EV"].N
    My_cd3_min = (0.90 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
                  0.65 * loads_dict["DW"].My +
                  1.00 * loads_dict["EV"].My +
                  1.50 * loads_dict["EH"].My +
                  1.40 * loads_dict["WS_doc_des"].My +
                  1.00 * loads_dict["FR"].My)
    results.append(CombinationResult(
        comb_id="CD_IIIb_min", comb_name="CĐ III(b) min", limit_state_group="STRENGTH",
        N=N_cd3_min, Hx=Hx_cd3, Hy=Hy_cd3, Mx=Mx_cd3, My=My_cd3_min
    ))

    # 3. CƯỜNG ĐỘ IV (Strength IV - Tỷ số tĩnh tải cao, gamma_DC = 1.50)
    N_cd4 = 1.50 * (loads_dict["DC1"].N + loads_dict["DC2"].N) + 1.50 * loads_dict["DW"].N + 1.35 * loads_dict["EV"].N
    Hx_cd4 = 1.50 * loads_dict["EH"].Hx + 1.00 * loads_dict["FR"].Hx
    My_cd4 = (1.50 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
              1.50 * loads_dict["DW"].My +
              1.35 * loads_dict["EV"].My +
              1.50 * loads_dict["EH"].My +
              1.00 * loads_dict["FR"].My)
    results.append(CombinationResult(
        comb_id="CD_IV", comb_name="CĐ IV", limit_state_group="STRENGTH",
        N=N_cd4, Hx=Hx_cd4, Hy=0.0, Mx=0.0, My=My_cd4
    ))

    # 4. CƯỜNG ĐỘ V (Strength V - Gió 25 m/s + Hoạt tải 1.35)
    for k in [1, num_lanes]:
        key = f"LL_IM_{k}lan_lech"
        ll = loads_dict.get(key, LoadVector(key))
        N = (1.25 * (loads_dict["DC1"].N + loads_dict["DC2"].N) +
             1.50 * loads_dict["DW"].N +
             1.35 * loads_dict["EV"].N +
             1.35 * loads_dict["VS"].N +
             1.35 * ll.N)
        Hx = (1.50 * loads_dict["EH"].Hx +
              1.35 * loads_dict["LS"].Hx +
              0.40 * loads_dict["WS_doc_25"].Hx +
              1.00 * loads_dict["WL_doc"].Hx +
              1.00 * loads_dict["FR"].Hx)
        Hy = 0.40 * loads_dict["WS_ngang_25"].Hy + 1.00 * loads_dict["WL_ngang"].Hy
        Mx = 1.35 * ll.Mx + 0.40 * loads_dict["WS_ngang_25"].Mx + 1.00 * loads_dict["WL_ngang"].Mx
        My = (1.25 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
              1.50 * loads_dict["DW"].My +
              1.35 * loads_dict["EV"].My +
              1.35 * loads_dict["VS"].My +
              1.35 * ll.My +
              1.50 * loads_dict["EH"].My +
              1.35 * loads_dict["LS"].My +
              0.40 * loads_dict["WS_doc_25"].My +
              1.00 * loads_dict["WL_doc"].My +
              1.00 * loads_dict["FR"].My)
        results.append(CombinationResult(
            comb_id=f"CD_V_{k}lan", comb_name=f"CĐ V - {k} làn", limit_state_group="STRENGTH",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 5. SỬ DỤNG I (Service I - Khai thác tiêu chuẩn)
    for k, key in enumerate(lane_keys_ecc, 1):
        ll = loads_dict.get(key, LoadVector(key))
        N = (1.00 * (loads_dict["DC1"].N + loads_dict["DC2"].N) +
             1.00 * loads_dict["DW"].N +
             1.00 * loads_dict["EV"].N +
             1.00 * loads_dict["VS"].N +
             1.00 * ll.N)
        Hx = (1.00 * loads_dict["EH"].Hx +
              1.00 * loads_dict["LS"].Hx +
              0.30 * loads_dict["WS_doc_25"].Hx +
              1.00 * loads_dict["WL_doc"].Hx +
              1.00 * loads_dict["FR"].Hx)
        Hy = 0.30 * loads_dict["WS_ngang_25"].Hy + 1.00 * loads_dict["WL_ngang"].Hy
        Mx = 1.00 * ll.Mx + 0.30 * loads_dict["WS_ngang_25"].Mx + 1.00 * loads_dict["WL_ngang"].Mx
        My = (1.00 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
              1.00 * loads_dict["DW"].My +
              1.00 * loads_dict["EV"].My +
              1.00 * loads_dict["VS"].My +
              1.00 * ll.My +
              1.00 * loads_dict["EH"].My +
              1.00 * loads_dict["LS"].My +
              0.30 * loads_dict["WS_doc_25"].My +
              1.00 * loads_dict["WL_doc"].My +
              1.00 * loads_dict["FR"].My)
        results.append(CombinationResult(
            comb_id=f"SD_I_{k}lan_lech", comb_name=f"SD I - {k} làn lệch", limit_state_group="SERVICE",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # Đúng tâm SD I
    for k, key in enumerate(lane_keys_cen, 1):
        ll = loads_dict.get(key, LoadVector(key))
        N = (1.00 * (loads_dict["DC1"].N + loads_dict["DC2"].N) +
             1.00 * loads_dict["DW"].N +
             1.00 * loads_dict["EV"].N +
             1.00 * loads_dict["VS"].N +
             1.00 * ll.N)
        Hx = (1.00 * loads_dict["EH"].Hx +
              1.00 * loads_dict["LS"].Hx +
              1.00 * loads_dict["FR"].Hx)
        Hy = 0.0
        Mx = 0.0
        My = (1.00 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
              1.00 * loads_dict["DW"].My +
              1.00 * loads_dict["EV"].My +
              1.00 * loads_dict["VS"].My +
              1.00 * ll.My +
              1.00 * loads_dict["EH"].My +
              1.00 * loads_dict["LS"].My +
              1.00 * loads_dict["FR"].My)
        results.append(CombinationResult(
            comb_id=f"SD_I_{k}lan_dung", comb_name=f"SD I - {k} làn đúng", limit_state_group="SERVICE",
            N=N, Hx=Hx, Hy=Hy, Mx=Mx, My=My
        ))

    # 6. ĐẶC BIỆT I (Extreme Event I - Động đất)
    # EQ dọc
    ll_eq = loads_dict.get(f"LL_IM_{num_lanes}lan_dung", LoadVector("LL_EQ"))
    N_eq = 1.25 * (loads_dict["DC1"].N + loads_dict["DC2"].N) + 1.50 * loads_dict["DW"].N + 1.35 * loads_dict["EV"].N + 0.50 * ll_eq.N
    Hx_eq_doc = 1.50 * loads_dict["EH"].Hx + 1.00 * loads_dict["EQ_doc"].Hx
    My_eq_doc = (1.25 * (loads_dict["DC1"].My + loads_dict["DC2"].My) +
                 1.50 * loads_dict["DW"].My +
                 1.35 * loads_dict["EV"].My +
                 0.50 * ll_eq.My +
                 1.50 * loads_dict["EH"].My +
                 1.00 * loads_dict["EQ_doc"].My)
    results.append(CombinationResult(
        comb_id="DB_I_EQ_doc", comb_name="ĐB I - EQ dọc (+ΔEAE)", limit_state_group="EXTREME",
        N=N_eq, Hx=Hx_eq_doc, Hy=0.0, Mx=0.0, My=My_eq_doc
    ))

    # EQ ngang
    Hy_eq_ngang = 1.00 * loads_dict["EQ_ngang"].Hy
    Mx_eq_ngang = 1.00 * loads_dict["EQ_ngang"].Mx
    results.append(CombinationResult(
        comb_id="DB_I_EQ_ngang", comb_name="ĐB I - EQ ngang", limit_state_group="EXTREME",
        N=N_eq, Hx=1.50 * loads_dict["EH"].Hx, Hy=Hy_eq_ngang, Mx=Mx_eq_ngang, My=My_eq_doc - 1.00 * loads_dict["EQ_doc"].My
    ))

    return results
