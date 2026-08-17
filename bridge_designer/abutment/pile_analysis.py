"""
Module: abutment.pile_analysis
Phân tích phản lực và nội lực móng cọc mố cầu cho tất cả các tổ hợp tải trọng
theo phương pháp ma trận độ cứng 3D chuẩn TS_PILE (TS_PILE_V1_0).
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple
from .model import AbutmentModel
from .combinations import CombinationResult
from ..tcvn.ts_pile_solver import TSPile, TSPileGroupSolver, TSPileReactionResult, TSPileForces
from ..tcvn.piles import Pile


@dataclass
class AbutmentPileAnalysisSummary:
    """Tổng hợp kết quả phản lực cọc mố"""
    piles: List[Pile]
    reactions_all: List[TSPileReactionResult]
    P_max_strength: float      # Phản lực nén lớn nhất ở TTGH Cường độ (kN)
    P_min_strength: float      # Phản lực nhỏ nhất ở TTGH Cường độ (kN)
    P_max_service: float       # Phản lực nén lớn nhất ở TTGH Sử dụng (kN)
    P_min_service: float       # Phản lực nhỏ nhất ở TTGH Sử dụng (kN)
    P_max_extreme: float       # Phản lực nén lớn nhất ở TTGH Đặc biệt (kN)
    P_min_extreme: float       # Phản lực nhỏ nhất ở TTGH Đặc biệt (kN)
    H_max_all: float           # Lực ngang lớn nhất trên 1 cọc (kN)
    controlling_comb_max: str  # Tổ hợp khống chế Pmax
    controlling_comb_min: str  # Tổ hợp khống chế Pmin
    passed_capacity: bool      # Đạt sức chịu tải cho phép ở mọi TTGH
    passed_tension: bool       # Không bị nhổ ở TTGH Sử dụng


def analyze_abutment_piles(
    model: AbutmentModel,
    combinations: List[CombinationResult]
) -> AbutmentPileAnalysisSummary:
    """
    Sinh lưới tọa độ cọc và giải phản lực cọc theo phương pháp ma trận độ cứng TS_PILE
    """
    ts_piles: List[TSPile] = []
    piles_simple: List[Pile] = []
    pile_id = 1

    if model.custom_piles and len(model.custom_piles) > 0:
        for idx, cp in enumerate(model.custom_piles, 1):
            pid = cp.get("id", idx)
            pname = f"P{pid}"
            px = float(cp.get("x", 0.0))
            py = float(cp.get("y", 0.0))
            pd = float(cp.get("diameter", model.pile_diameter))
            ts_piles.append(TSPile(id=pid, name=pname, x=px, y=py, diameter=pd))
            piles_simple.append(Pile(id=pid, x=px, y=py, diameter=pd))
    else:
        # Tạo tọa độ các cọc từ danh sách hàng cọc
        for row in model.pile_rows:
            if row.count <= 0:
                continue
            total_width = (row.count - 1) * row.spacing
            start_y = -total_width / 2.0
            for j in range(row.count):
                y_pos = start_y + j * row.spacing
                pname = f"P{pile_id}"
                ts_piles.append(TSPile(
                    id=pile_id,
                    name=pname,
                    x=row.x,
                    y=y_pos,
                    diameter=model.pile_diameter
                ))
                piles_simple.append(Pile(
                    id=pile_id,
                    x=row.x,
                    y=y_pos,
                    diameter=model.pile_diameter
                ))
                pile_id += 1

    solver = TSPileGroupSolver(ts_piles, Bx=model.B1, By=model.C1, Cz=model.H1)
    reactions: List[TSPileReactionResult] = []

    p_max_str = -1e9
    p_min_str = 1e9
    p_max_ser = -1e9
    p_min_ser = 1e9
    p_max_ext = -1e9
    p_min_ext = 1e9
    h_max = 0.0

    comb_max = ""
    comb_min = ""

    all_passed_cap = True

    for comb in combinations:
        res = solver.calculate_reaction(
            comb_name=comb.comb_name,
            limit_state_group=comb.limit_state_group,
            N=comb.N,
            Mx=comb.Mx,
            My=comb.My,
            Hx=comb.Hx,
            Hy=comb.Hy,
            Mz=0.0
        )
        reactions.append(res)

        # Kiểm tra sức chịu tải từng tổ hợp theo đúng TTGH TCVN 11823-10
        if comb.limit_state_group == "STRENGTH":
            P_allow_comb = 1.40 * model.pile_capacity_allowable  # Sức kháng tính toán phi*Rn
            if res.P_max > P_allow_comb:
                all_passed_cap = False
            if res.P_max > p_max_str:
                p_max_str = res.P_max
                comb_max = comb.comb_name
            if res.P_min < p_min_str:
                p_min_str = res.P_min
                comb_min = comb.comb_name
        elif comb.limit_state_group == "SERVICE":
            P_allow_comb = model.pile_capacity_allowable  # Sức chịu tải cho phép Rall
            if res.P_max > P_allow_comb:
                all_passed_cap = False
            p_max_ser = max(p_max_ser, res.P_max)
            p_min_ser = min(p_min_ser, res.P_min)
        elif comb.limit_state_group == "EXTREME":
            P_allow_comb = 1.80 * model.pile_capacity_allowable  # Sức kháng đặc biệt phi=1.0
            if res.P_max > P_allow_comb:
                all_passed_cap = False
            p_max_ext = max(p_max_ext, res.P_max)
            p_min_ext = min(p_min_ext, res.P_min)

        h_max = max(h_max, res.H_max)

    # Kiểm tra cọc chịu nhổ ở TTGH Sử dụng
    pass_ten = (p_min_ser >= 0.0)

    return AbutmentPileAnalysisSummary(
        piles=piles_simple,
        reactions_all=reactions,
        P_max_strength=p_max_str,
        P_min_strength=p_min_str,
        P_max_service=p_max_ser,
        P_min_service=p_min_ser,
        P_max_extreme=p_max_ext,
        P_min_extreme=p_min_ext,
        H_max_all=h_max,
        controlling_comb_max=comb_max,
        controlling_comb_min=comb_min,
        passed_capacity=all_passed_cap,
        passed_tension=pass_ten
    )
