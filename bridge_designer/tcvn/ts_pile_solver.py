"""
Module: tcvn.ts_pile_solver
Bộ giải phân tích phản lực và nội lực móng nhóm cọc theo phương pháp ma trận độ cứng
chuẩn theo công cụ TS_PILE (TS_PILE_V1_0_20260704_final_ACTIVE_FIXED_V6).
Mô hình đài tuyệt đối cứng liên kết đàn hồi với nhóm cọc trong không gian 3D.
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import numpy as np


@dataclass
class TSPile:
    """Định nghĩa một cọc trong nhóm cọc theo chuẩn TS_PILE"""
    id: int
    name: str
    x: float                   # Tọa độ x (phương vuông góc tim mố / dọc cầu) (m)
    y: float                   # Tọa độ y (phương song song tim mố / ngang cầu) (m)
    z: float = 0.0             # Cao độ đầu cọc so với đáy bệ (m)
    diameter: float = 1.2      # Đường kính cọc D (m)
    length: float = 30.0       # Chiều dài cọc (m)
    angle_deg: float = 0.0     # Góc xiên cọc (độ, 0 = cọc thẳng đứng)
    azimuth_deg: float = 0.0   # Hướng xiên (độ)
    # Đặc trưng độ cứng
    E: float = 3.0e7           # Mô đun đàn hồi cọc (kN/m²)
    # Hệ số nền cọc theo MCOC/TS_PILE
    Co: float = 12000.0        # Độ cứng dọc cọc (kN/m)
    Ct: float = 2500.0         # Độ cứng ngang cọc (kN/m)
    Fo: float = 1500.0         # Độ cứng xoay cọc (kNm/rad)
    Io: float = 2000.0         # Liên kết ngang-xoay (kN/rad)


@dataclass
class TSPileForces:
    """Nội lực đầu cọc theo chuẩn TS_PILE"""
    pile_id: int
    pile_name: str
    N: float                   # Lực dọc cọc (kN, nén dương)
    Qx: float                  # Lực cắt phương X (kN)
    Qy: float                  # Lực cắt phương Y (kN)
    Mx: float                  # Mô men uốn quanh X (kNm)
    My: float                  # Mô men uốn quanh Y (kNm)
    Mz: float                  # Mô men xoắn (kNm)


@dataclass
class TSPileReactionResult:
    """Kết quả phản lực nhóm cọc cho một tổ hợp tải trọng"""
    comb_name: str
    limit_state_group: str     # 'STRENGTH', 'SERVICE', 'EXTREME'
    N_total: float             # Lực dọc tổng (kN)
    Hx_total: float            # Lực ngang X (kN)
    Hy_total: float            # Lực ngang Y (kN)
    Mx_total: float            # Mô men quanh X (kNm)
    My_total: float            # Mô men quanh Y (kNm)
    Mz_total: float            # Mô men quanh Z (kNm)
    # Chuyển vị đài móng
    u: float                   # Chuyển vị ngang X (m)
    v: float                   # Chuyển vị ngang Y (m)
    w: float                   # Lún đứng Z (m)
    rot_x: float               # Góc xoay quanh X (rad)
    rot_y: float               # Góc xoay quanh Y (rad)
    rot_z: float               # Góc xoay quanh Z (rad)
    # Phản lực cọc
    P_max: float               # Lực nén cọc lớn nhất (kN)
    P_min: float               # Lực nén cọc nhỏ nhất / kéo (kN)
    H_max: float               # Lực cắt đầu cọc lớn nhất (kN)
    pile_forces: Dict[int, TSPileForces] # Chi tiết nội lực từng cọc
    used_pseudoinverse: bool = False
    matrix_rank: int = 6
    condition_number: float = 1.0
    solver_mode: str = "INTERNAL_6DOF"
    solver_status: str = "CONVERGED"


class TSPileGroupSolver:
    """
    Bộ giải ma trận độ cứng nhóm cọc theo chuẩn TS_PILE (6DOF) và Rigid Cap Analytical
    """
    def __init__(self, piles: List[TSPile], Bx: float = 6.0, By: float = 23.55, Cz: float = 1.8):
        self.piles = piles
        self.num_piles = len(piles)
        self.Bx = Bx
        self.By = By
        self.Cz = Cz

        # Tính trọng tâm nhóm cọc
        if self.num_piles > 0:
            self.xc = sum(p.x for p in piles) / float(self.num_piles)
            self.yc = sum(p.y for p in piles) / float(self.num_piles)
        else:
            self.xc = 0.0
            self.yc = 0.0

        # Xây dựng ma trận độ cứng tổng thể K (6x6)
        self.K_global = self._build_global_stiffness()
        self.matrix_rank = int(np.linalg.matrix_rank(self.K_global)) if self.num_piles > 0 else 0
        try:
            self.condition_number = float(np.linalg.cond(self.K_global)) if self.num_piles > 0 else 1.0
        except Exception:
            self.condition_number = 1e16

    def _get_pile_local_stiffness(self, p: TSPile) -> np.ndarray:
        """Ma trận độ cứng 6x6 đầu cọc theo hệ tọa độ cục bộ (TS_PILE)"""
        r = p.diameter / 2.0
        A = math.pi * (r ** 2)
        I = math.pi * (r ** 4) / 4.0
        J = 2.0 * I

        # Độ cứng cọc dọc trục: K_axial = E*A / L_eq hoặc dùng Co
        K_axial = (p.E * A) / max(5.0, p.length * 0.5) if p.length > 0 else 50000.0
        # Độ cứng ngang cọc K_lat và uốn K_rot
        K_lat = p.Ct if p.Ct > 0 else (3.0 * p.E * I / (5.0 ** 3))
        K_rot = p.Fo if p.Fo > 0 else (4.0 * p.E * I / 5.0)
        K_lat_rot = p.Io if p.Io > 0 else (6.0 * p.E * I / (5.0 ** 2))
        K_tor = (p.E * J) / (2.6 * max(5.0, p.length))

        # [Qx, Qy, N, Mx, My, Mz]
        A3 = np.zeros((6, 6))
        A3[0, 0] = K_lat
        A3[0, 4] = -K_lat_rot
        A3[4, 0] = -K_lat_rot
        A3[4, 4] = K_rot

        A3[1, 1] = K_lat
        A3[1, 3] = K_lat_rot
        A3[3, 1] = K_lat_rot
        A3[3, 3] = K_rot

        A3[2, 2] = K_axial
        A3[5, 5] = K_tor

        return A3

    def _get_transformation_matrix(self, p: TSPile) -> np.ndarray:
        """Ma trận chuyển tọa độ từ trọng tâm đài (xc, yc, 0) đến đầu cọc (dx, dy, 0)"""
        dx = p.x - self.xc
        dy = p.y - self.yc
        dz = p.z

        # Ma trận T (6x6)
        T = np.array([
            [1.0, 0.0, 0.0, 0.0,  dz, -dy],
            [0.0, 1.0, 0.0, -dz, 0.0,  dx],
            [0.0, 0.0, 1.0,  dy, -dx, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        ], dtype=float)

        return T

    def _build_global_stiffness(self) -> np.ndarray:
        """Tích lũy ma trận độ cứng tổng thể K = sum(T_i^T * A3_i * T_i)"""
        K = np.zeros((6, 6), dtype=float)
        for p in self.piles:
            A3 = self._get_pile_local_stiffness(p)
            T = self._get_transformation_matrix(p)
            K += T.T @ A3 @ T
        return 0.5 * (K + K.T)

    def calculate_reaction_rigid_cap(
        self,
        comb_name: str,
        limit_state_group: str,
        N: float,              # Lực dọc (kN, nén dương)
        Mx: float,             # Mô men quanh X (kNm)
        My: float,             # Mô men quanh Y (kNm)
        Hx: float = 0.0,       # Lực cắt X (kN)
        Hy: float = 0.0        # Lực cắt Y (kN)
    ) -> TSPileReactionResult:
        """
        Giải giải tích đài tuyệt đối cứng (Analytical Rigid Cap Solution):
        P_i = N / n + Mx * dy_i / sum(dy^2) + My * dx_i / sum(dx^2)
        """
        n = self.num_piles
        if n == 0:
            return TSPileReactionResult(
                comb_name=comb_name, limit_state_group=limit_state_group,
                N_total=N, Hx_total=Hx, Hy_total=Hy, Mx_total=Mx, My_total=My, Mz_total=0.0,
                u=0.0, v=0.0, w=0.0, rot_x=0.0, rot_y=0.0, rot_z=0.0,
                P_max=0.0, P_min=0.0, H_max=0.0, pile_forces={}, solver_mode="RIGID_CAP_ANALYTICAL"
            )

        sum_dx2 = sum((p.x - self.xc) ** 2 for p in self.piles)
        sum_dy2 = sum((p.y - self.yc) ** 2 for p in self.piles)

        pile_forces_dict: Dict[int, TSPileForces] = {}
        for p in self.piles:
            dx = p.x - self.xc
            dy = p.y - self.yc
            # Lực dọc
            term_x = (My * dx / sum_dx2) if sum_dx2 > 1e-4 else 0.0
            term_y = (Mx * dy / sum_dy2) if sum_dy2 > 1e-4 else 0.0
            Ni = N / float(n) + term_x + term_y
            Qxi = Hx / float(n)
            Qyi = Hy / float(n)

            pile_forces_dict[p.id] = TSPileForces(
                pile_id=p.id, pile_name=p.name,
                N=Ni, Qx=Qxi, Qy=Qyi, Mx=0.0, My=0.0, Mz=0.0
            )

        p_vals = [f.N for f in pile_forces_dict.values()]
        p_max = max(p_vals) if p_vals else 0.0
        p_min = min(p_vals) if p_vals else 0.0
        h_vals = [math.sqrt(f.Qx**2 + f.Qy**2) for f in pile_forces_dict.values()]
        h_max = max(h_vals) if h_vals else 0.0

        return TSPileReactionResult(
            comb_name=comb_name, limit_state_group=limit_state_group,
            N_total=N, Hx_total=Hx, Hy_total=Hy, Mx_total=Mx, My_total=My, Mz_total=0.0,
            u=0.0, v=0.0, w=0.0, rot_x=0.0, rot_y=0.0, rot_z=0.0,
            P_max=p_max, P_min=p_min, H_max=h_max, pile_forces=pile_forces_dict,
            solver_mode="RIGID_CAP_ANALYTICAL", solver_status="CONVERGED"
        )

    def calculate_reaction(
        self,
        comb_name: str,
        limit_state_group: str,
        N: float,              # Lực dọc tại đáy bệ (kN, nén dương)
        Mx: float,             # Mô men quanh trục X (kNm)
        My: float,             # Mô men quanh trục Y (kNm)
        Hx: float = 0.0,       # Lực ngang X (kN)
        Hy: float = 0.0,       # Lực ngang Y (kN)
        Mz: float = 0.0        # Mô men xoắn Z (kNm)
    ) -> TSPileReactionResult:
        """
        Giải hệ phương trình độ cứng K * Delta = P và tính nội lực từng cọc (INTERNAL_6DOF)
        """
        if self.num_piles == 0:
            return TSPileReactionResult(
                comb_name=comb_name, limit_state_group=limit_state_group,
                N_total=N, Hx_total=Hx, Hy_total=Hy, Mx_total=Mx, My_total=My, Mz_total=Mz,
                u=0.0, v=0.0, w=0.0, rot_x=0.0, rot_y=0.0, rot_z=0.0,
                P_max=0.0, P_min=0.0, H_max=0.0, pile_forces={}
            )

        P_vec = np.array([Hx, Hy, N, Mx, My, Mz], dtype=float)
        used_pinv = False
        status = "CONVERGED"

        if self.matrix_rank < 6 or self.condition_number > 1e14:
            used_pinv = True
            status = "WARNING_HIGH_CONDITION_NUMBER"
            Delta = np.linalg.pinv(self.K_global) @ P_vec
        else:
            try:
                Delta = np.linalg.solve(self.K_global, P_vec)
            except np.linalg.LinAlgError:
                used_pinv = True
                status = "WARNING_SINGULAR_MATRIX_PINV"
                Delta = np.linalg.pinv(self.K_global) @ P_vec

        u, v, w, rx, ry, rz = Delta

        pile_forces_dict: Dict[int, TSPileForces] = {}
        for p in self.piles:
            A3 = self._get_pile_local_stiffness(p)
            T = self._get_transformation_matrix(p)
            F_local = A3 @ (T @ Delta)

            pf = TSPileForces(
                pile_id=p.id,
                pile_name=p.name,
                Qx=float(F_local[0]),
                Qy=float(F_local[1]),
                N=float(F_local[2]),
                Mx=float(F_local[3]),
                My=float(F_local[4]),
                Mz=float(F_local[5])
            )
            pile_forces_dict[p.id] = pf

        p_vals = [f.N for f in pile_forces_dict.values()]
        p_max = max(p_vals) if p_vals else 0.0
        p_min = min(p_vals) if p_vals else 0.0

        h_vals = [math.sqrt(f.Qx**2 + f.Qy**2) for f in pile_forces_dict.values()]
        h_max = max(h_vals) if h_vals else 0.0

        return TSPileReactionResult(
            comb_name=comb_name,
            limit_state_group=limit_state_group,
            N_total=N, Hx_total=Hx, Hy_total=Hy, Mx_total=Mx, My_total=My, Mz_total=Mz,
            u=float(u), v=float(v), w=float(w),
            rot_x=float(rx), rot_y=float(ry), rot_z=float(rz),
            P_max=p_max, P_min=p_min, H_max=h_max,
            pile_forces=pile_forces_dict,
            used_pseudoinverse=used_pinv,
            matrix_rank=self.matrix_rank,
            condition_number=round(self.condition_number, 2),
            solver_mode="INTERNAL_6DOF",
            solver_status=status
        )
