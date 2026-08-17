"""
Module: tcvn.bearings
Tính toán phản lực và biến dạng hệ gối cầu theo phương dọc cầu (TCVN 11823-14)
cho các tác động biến dạng cưỡng bức:
- Thay đổi nhiệt độ TU (+Delta T, -Delta T)
- Co ngót bê tông SH (Shrinkage)
- Từ biến bê tông CR (Creep)
- Lực ma sát gối trượt FR = mu * N
- Giải chuỗi thanh dọc 1D và độ cứng thân mố/trụ
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class BearingNode:
    """Nút gối trên mố/trụ trong sơ đồ liên"""
    name: str                  # Tên mố/trụ (vd: Mố A, Trụ T1, Mố B)
    x: float                   # Tọa độ vị trí mố/trụ dọc cầu (m)
    L_next_span: float         # Chiều dài nhịp kế tiếp sang phải (m)
    bearing_type_left: str     # Loại gối trái: 'Cao su', 'Chậu di động 2 phương', 'Chậu di động 1 phương dọc', 'Chậu di động 1 phương ngang', 'Cố định'
    bearing_type_right: str    # Loại gối phải
    state_left: str            # 'ELASTIC', 'SLIDE', 'FIXED'
    state_right: str           # 'ELASTIC', 'SLIDE', 'FIXED'
    K_pier: float              # Độ cứng uốn thân trụ/mố (kN/m)
    A_bearing: float = 0.09    # Diện tích gối (m²)
    G_elastomer: float = 1000.0 # Mô đun trượt cao su (kPa)
    h_elastomer: float = 0.05  # Chiều dày tầng cao su có hiệu (m)
    mu_friction: float = 0.07  # Hệ số ma sát gối trượt PTFE


@dataclass
class BearingForcesResult:
    """Kết quả lực ngang dọc cầu do biến dạng cưỡng bức tại mố/trụ đang tính"""
    H_TU_pos: float            # Lực nhiệt độ tăng TU+ (kN)
    H_TU_neg: float            # Lực nhiệt độ giảm TU- (kN)
    H_CR: float                # Lực từ biến CR (kN)
    H_SH: float                # Lực co ngót SH (kN)
    H_FR: float                # Lực ma sát gối trượt FR (kN)
    F_bearing_left_TU: float   # Lực gối trái do TU
    F_bearing_right_TU: float  # Lực gối phải do TU


class BearingChainSolver:
    """
    Bộ giải hệ gối 1D toàn liên
    """
    def __init__(
        self,
        nodes: List[BearingNode],
        alpha_thermal: float = 1.0e-5, # Hệ số giãn nở nhiệt bê tông (1/°C)
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

    def solve_pier_forces(self, target_node_name: str, N_left_DL: float, N_right_DL: float) -> BearingForcesResult:
        """
        Tính lực dọc cầu do TU, CR, SH, FR tác dụng lên mố/trụ target_node_name
        """
        target_node = None
        for n in self.nodes:
            if n.name == target_node_name:
                target_node = n
                break

        if target_node is None:
            return BearingForcesResult(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Tính lực ma sát FR = mu * N
        FR_left = target_node.mu_friction * N_left_DL if target_node.state_left == "SLIDE" else 0.0
        FR_right = target_node.mu_friction * N_right_DL if target_node.state_right == "SLIDE" else 0.0
        FR_total = FR_left + FR_right

        # Độ cứng gối cao su Kb = G * A / h (kN/m)
        Kb_left = (target_node.G_elastomer * target_node.A_bearing / target_node.h_elastomer) if target_node.state_left == "ELASTIC" else 0.0
        Kb_right = (target_node.G_elastomer * target_node.A_bearing / target_node.h_elastomer) if target_node.state_right == "ELASTIC" else 0.0

        # Chuyển vị nhiệt độ tự do của 2 nhịp kề
        # Giả thiết sơ bộ nhịp giản đơn dãn từ tim nhịp
        L_left = target_node.L_next_span  # có thể lấy từ nhịp trước
        L_right = target_node.L_next_span

        u_TU_pos_L = self.alpha * self.dT_pos * (L_left / 2.0)
        u_TU_pos_R = -self.alpha * self.dT_pos * (L_right / 2.0)

        u_TU_neg_L = -self.alpha * self.dT_neg * (L_left / 2.0)
        u_TU_neg_R = self.alpha * self.dT_neg * (L_right / 2.0)

        u_SH_L = -self.eps_sh * (L_left / 2.0)
        u_SH_R = self.eps_sh * (L_right / 2.0)

        u_CR_L = -self.eps_cr * (L_left / 2.0)
        u_CR_R = self.eps_cr * (L_right / 2.0)

        # Cân bằng chuyển vị đỉnh trụ u_p = (sum k_i * u_i) / (Kp + sum k_i)
        Kp = max(1.0, target_node.K_pier)
        K_sum = Kb_left + Kb_right

        up_TUp = (Kb_left * u_TU_pos_L + Kb_right * u_TU_pos_R) / (Kp + K_sum) if K_sum > 0 else 0.0
        up_TUm = (Kb_left * u_TU_neg_L + Kb_right * u_TU_neg_R) / (Kp + K_sum) if K_sum > 0 else 0.0
        up_SH = (Kb_left * u_SH_L + Kb_right * u_SH_R) / (Kp + K_sum) if K_sum > 0 else 0.0
        up_CR = (Kb_left * u_CR_L + Kb_right * u_CR_R) / (Kp + K_sum) if K_sum > 0 else 0.0

        # Lực truyền vào đỉnh trụ H = Kp * up
        H_TUp = Kp * up_TUp
        H_TUm = Kp * up_TUm
        H_SH = Kp * up_SH
        H_CR = Kp * up_CR

        F_left_TU = Kb_left * (u_TU_pos_L - up_TUp)
        F_right_TU = Kb_right * (u_TU_pos_R - up_TUp)

        return BearingForcesResult(
            H_TU_pos=H_TUp,
            H_TU_neg=H_TUm,
            H_CR=H_CR,
            H_SH=H_SH,
            H_FR=FR_total,
            F_bearing_left_TU=F_left_TU,
            F_bearing_right_TU=F_right_TU
        )
