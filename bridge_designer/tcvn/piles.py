"""
Module: tcvn.piles
Tính toán và phân bố phản lực đầu cọc cho móng mố và móng trụ cầu
theo mô hình đài cọc tuyệt đối cứng (TCVN 11823-10).
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class Pile:
    """Định nghĩa một cọc trong nhóm cọc"""
    id: int
    x: float                   # Tọa độ x (dọc cầu / vuông góc tim mố trụ) (m)
    y: float                   # Tọa độ y (ngang cầu / song song tim mố trụ) (m)
    diameter: float = 1.2      # Đường kính cọc D (m)


@dataclass
class PileReactionResult:
    """Kết quả tính toán phản lực cọc cho một tổ hợp tải trọng"""
    comb_name: str
    N_total: float             # Lực dọc tổng tại đáy bệ (kN)
    Mx_total: float            # Mô men uốn quanh trục X (kN.m)
    My_total: float            # Mô men uốn quanh trục Y (kN.m)
    Hx_total: float            # Lực cắt Hx (kN)
    Hy_total: float            # Lực cắt Hy (kN)
    P_max: float               # Phản lực cọc nén lớn nhất (kN)
    P_min: float               # Phản lực cọc nén nhỏ nhất / kéo (kN)
    H_max: float               # Lực ngang lớn nhất tác dụng lên 1 cọc (kN)
    pile_forces: Dict[int, float] # Phản lực từng cọc {pile_id: Pi (kN)}


class PileGroupSolver:
    """
    Bộ giải phân bố phản lực nhóm cọc cho đài cứng
    """
    def __init__(self, piles: List[Pile]):
        self.piles = piles
        self.num_piles = len(piles)

        # Tính trọng tâm nhóm cọc
        if self.num_piles > 0:
            self.xc = sum(p.x for p in piles) / self.num_piles
            self.yc = sum(p.y for p in piles) / self.num_piles
        else:
            self.xc = 0.0
            self.yc = 0.0

        # Tính tổng bình phương khoảng cách
        self.sum_x2 = sum((p.x - self.xc) ** 2 for p in piles) if self.num_piles > 0 else 1.0
        self.sum_y2 = sum((p.y - self.yc) ** 2 for p in piles) if self.num_piles > 0 else 1.0

    def calculate_reaction(
        self,
        comb_name: str,
        N: float,              # Lực dọc (kN, nén dương)
        Mx: float,             # Mô men quanh trục X (kN.m)
        My: float,             # Mô men quanh trục Y (kN.m)
        Hx: float = 0.0,       # Lực ngang X (kN)
        Hy: float = 0.0        # Lực ngang Y (kN)
    ) -> PileReactionResult:
        """
        Tính phản lực cọc theo công thức đàn hồi đài cứng:
        Pi = N / n + Mx * (yi - yc) / sum(y²) + My * (xi - xc) / sum(x²)
        """
        if self.num_piles == 0:
            return PileReactionResult(
                comb_name=comb_name, N_total=N, Mx_total=Mx, My_total=My,
                Hx_total=Hx, Hy_total=Hy, P_max=0.0, P_min=0.0, H_max=0.0,
                pile_forces={}
            )

        pile_forces: Dict[int, float] = {}
        for p in self.piles:
            dx = p.x - self.xc
            dy = p.y - self.yc

            term_N = N / self.num_piles
            term_Mx = (Mx * dy) / self.sum_y2 if self.sum_y2 > 0 else 0.0
            term_My = (My * dx) / self.sum_x2 if self.sum_x2 > 0 else 0.0

            Pi = term_N + term_Mx + term_My
            pile_forces[p.id] = Pi

        p_vals = list(pile_forces.values())
        p_max = max(p_vals) if p_vals else 0.0
        p_min = min(p_vals) if p_vals else 0.0

        H_total = math.sqrt(Hx ** 2 + Hy ** 2)
        H_pile = H_total / self.num_piles if self.num_piles > 0 else 0.0

        return PileReactionResult(
            comb_name=comb_name,
            N_total=N,
            Mx_total=Mx,
            My_total=My,
            Hx_total=Hx,
            Hy_total=Hy,
            P_max=p_max,
            P_min=p_min,
            H_max=H_pile,
            pile_forces=pile_forces
        )
