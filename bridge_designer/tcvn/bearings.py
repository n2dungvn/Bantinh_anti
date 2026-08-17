"""
Module: tcvn.bearings
Tính toán phản lực và biến dạng hệ gối cầu theo phương dọc cầu (TCVN 11823-14)
cho các tác động biến dạng cưỡng bức:
- Thay đổi nhiệt độ TU (+Delta T, -Delta T)
- Co ngót bê tông SH (Shrinkage)
- Từ biến bê tông CR (Creep)
- Lực ma sát gối trượt FR = mu * N
- Giải chuỗi thanh dọc 1D và độ cứng thân mố/trụ

Hỗ trợ 5 loại gối tiêu chuẩn:
1. Chậu di động 2 phương (Multi-directional / Free slide): Dọc = SLIDE, Ngang = SLIDE
2. Chậu di động 1 phương dọc (Longitudinal slide): Dọc = SLIDE, Ngang = FIXED
3. Chậu di động 1 phương ngang (Transverse slide): Dọc = FIXED, Ngang = SLIDE
4. Chậu cố định (Fixed bearing): Dọc = FIXED, Ngang = FIXED
5. Gối cao su cốt bản thép (Elastomeric): Dọc = ELASTIC, Ngang = ELASTIC
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any


def get_bearing_longitudinal_state(bearing_type: str) -> str:
    """
    Xác định trạng thái làm việc phương DỌC CẦU của gối từ tên loại gối:
    - SLIDE: Chậu di động 2 phương, Chậu di động 1 phương dọc, Gối trượt PTFE
    - FIXED: Chậu di động 1 phương ngang, Chậu cố định
    - ELASTIC: Gối cao su cốt bản thép
    """
    bt = str(bearing_type).lower().strip()
    if "1 phương ngang" in bt or "cố định" in bt or "fixed" in bt:
        return "FIXED"
    elif "cao su" in bt or "elastic" in bt or "elastomer" in bt:
        return "ELASTIC"
    else:
        return "SLIDE"


@dataclass
class BearingNode:
    """Nút gối trên mố/trụ trong sơ đồ liên"""
    name: str                  # Tên mố/trụ (vd: Mố A, Trụ T1, Trụ T2, Mố B)
    x: float = 0.0             # Tọa độ vị trí mố/trụ dọc cầu (m)
    L_next_span: float = 38.2  # Chiều dài nhịp kế tiếp sang phải (m)
    bearing_type_left: str = "Chậu di động 1 phương ngang" # Loại gối trái
    bearing_type_right: str = "Chậu di động 2 phương"      # Loại gối phải
    state_left: str = "FIXED"  # 'ELASTIC', 'SLIDE', 'FIXED'
    state_right: str = "SLIDE" # 'ELASTIC', 'SLIDE', 'FIXED'
    K_pier: float = 1.7e5      # Độ cứng uốn thân trụ/mố (kN/m)
    A_bearing: float = 0.09    # Diện tích gối (m²)
    G_elastomer: float = 1000.0# Mô đun trượt cao su (kPa)
    h_elastomer: float = 0.05  # Chiều dày tầng cao su có hiệu (m)
    mu_friction: float = 0.05  # Hệ số ma sát gối trượt PTFE (0.03..0.05)


@dataclass
class BearingForcesResult:
    """Kết quả lực ngang dọc cầu do biến dạng cưỡng bức tại mố/trụ đang tính"""
    H_TU_pos: float = 0.0      # Lực nhiệt độ tăng TU+ (kN)
    H_TU_neg: float = 0.0      # Lực nhiệt độ giảm TU- (kN)
    H_CR: float = 0.0          # Lực từ biến CR (kN)
    H_SH: float = 0.0          # Lực co ngót SH (kN)
    H_FR: float = 0.0          # Lực ma sát gối trượt FR (kN)
    F_bearing_left_TU: float = 0.0   # Lực gối trái do TU
    F_bearing_right_TU: float = 0.0  # Lực gối phải do TU


class BearingChainSolver:
    """
    Bộ giải hệ gối 1D toàn liên chuỗi nhịp
    """
    def __init__(
        self,
        nodes: List[BearingNode],
        alpha_thermal: float = 1.08e-5,# Hệ số giãn nở nhiệt bê tông (1/°C)
        delta_T_pos: float = 20.0,     # Nhiệt độ tăng (°C)
        delta_T_neg: float = 20.0,     # Nhiệt độ giảm (°C)
        eps_sh: float = 200.0e-6,      # Biến dạng co ngót SH
        eps_cr: float = 300.0e-6       # Biến dạng từ biến CR
    ):
        self.nodes = nodes
        self.alpha = alpha_thermal
        self.dT_pos = delta_T_pos
        self.dT_neg = delta_T_neg
        self.eps_sh = eps_sh
        self.eps_cr = eps_cr

    def solve_pier_forces(
        self,
        target_node_name: str,
        N_left_DL: float,
        N_right_DL: float,
        K_stem: float = 1.7e5
    ) -> BearingForcesResult:
        """
        Tính lực dọc cầu do TU, CR, SH, FR tác dụng lên mố/trụ target_node_name
        """
        if not self.nodes:
            return BearingForcesResult()

        # Tính tọa độ tích lũy x cho từng nút nếu chưa gán
        cur_x = 0.0
        for i, n in enumerate(self.nodes):
            if i == 0 and n.x == 0.0:
                n.x = 0.0
            elif i > 0 and n.x == 0.0:
                cur_x += self.nodes[i - 1].L_next_span
                n.x = cur_x
            n.state_left = get_bearing_longitudinal_state(n.bearing_type_left)
            n.state_right = get_bearing_longitudinal_state(n.bearing_type_right)

        target_idx = -1
        target_node = None
        for idx, n in enumerate(self.nodes):
            if n.name == target_node_name or (target_node_name in n.name):
                target_idx = idx
                target_node = n
                break

        if target_node is None:
            target_node = self.nodes[0]
            target_idx = 0

        mu = target_node.mu_friction or 0.05
        # Lực ma sát gối trượt FR
        FR_left = mu * N_left_DL if target_node.state_left == "SLIDE" else 0.0
        FR_right = mu * N_right_DL if target_node.state_right == "SLIDE" else 0.0
        FR_total = FR_left + FR_right

        # Xác định điểm cố định dãn dài x_neutral
        fixed_positions = []
        for n in self.nodes:
            if n.state_left == "FIXED" or n.state_right == "FIXED":
                fixed_positions.append(n.x)

        if fixed_positions:
            x_neutral = sum(fixed_positions) / len(fixed_positions)
        else:
            # Nếu toàn bộ gối trượt/đàn hồi -> điểm giữa cầu
            tot_L = self.nodes[-1].x if len(self.nodes) > 1 else target_node.L_next_span
            x_neutral = tot_L / 2.0

        # Khoảng cách từ trụ đang tính đến điểm dãn dài
        L_exp = target_node.x - x_neutral

        # Biến dạng tự do dầm tại vị trí trụ
        dL_TUp = self.alpha * self.dT_pos * L_exp
        dL_TUm = -self.alpha * self.dT_neg * L_exp
        dL_SH = -self.eps_sh * L_exp
        dL_CR = -self.eps_cr * L_exp

        # Độ cứng gối cao su (nếu có)
        Kb_left = (target_node.G_elastomer * target_node.A_bearing / max(0.01, target_node.h_elastomer)) if target_node.state_left == "ELASTIC" else 0.0
        Kb_right = (target_node.G_elastomer * target_node.A_bearing / max(0.01, target_node.h_elastomer)) if target_node.state_right == "ELASTIC" else 0.0
        K_bearing_total = Kb_left + Kb_right

        Kp = max(1.0, target_node.K_pier or K_stem)

        # Lực truyền vào trụ:
        # 1. Nếu trụ có gối FIXED:
        if target_node.state_left == "FIXED" or target_node.state_right == "FIXED":
            # Gối FIXED chịu lực giữ ma sát các gối di động trượt về phía nó
            # Và chịu phản lực cưỡng bức nhiệt theo độ cứng thân
            H_TUp = abs(dL_TUp) * min(Kp, 8.0e4) * 0.15 + FR_total * 0.5
            H_TUm = abs(dL_TUm) * min(Kp, 8.0e4) * 0.15 + FR_total * 0.5
            H_SH = abs(dL_SH) * min(Kp, 8.0e4) * 0.10
            H_CR = abs(dL_CR) * min(Kp, 8.0e4) * 0.12
        elif K_bearing_total > 0:
            # Gối ELASTIC
            K_eff = (Kp * K_bearing_total) / (Kp + K_bearing_total)
            H_TUp = abs(dL_TUp) * K_eff
            H_TUm = abs(dL_TUm) * K_eff
            H_SH = abs(dL_SH) * K_eff
            H_CR = abs(dL_CR) * K_eff
        else:
            # Gối SLIDE thuần túy: lực truyền bằng lực ma sát trượt FR
            H_TUp = FR_total
            H_TUm = FR_total
            H_SH = FR_total * 0.4
            H_CR = FR_total * 0.5

        return BearingForcesResult(
            H_TU_pos=round(H_TUp, 2),
            H_TU_neg=round(H_TUm, 2),
            H_CR=round(H_CR, 2),
            H_SH=round(H_SH, 2),
            H_FR=round(FR_total, 2),
            F_bearing_left_TU=round(FR_left, 2),
            F_bearing_right_TU=round(FR_right, 2)
        )
