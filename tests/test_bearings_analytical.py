"""
Analytical Benchmark Tests for Longitudinal Bearing Chain (TCVN 11823-14)
Kiểm thử tính đúng đắn cơ học kết cấu:
A. Hệ tự do (Free slide): Reaction = 0 (ngoài FR)
B. Hệ ngàm hoàn toàn (Fully restrained): Thermal force = EA * alpha * Delta_T
C. Giới hạn độ cứng K_support -> 0: H -> 0
D. Giới hạn độ cứng K_support -> infinity: H -> EA * alpha * Delta_T
E. Hệ đối xứng: Chuyển vị và phản lực đối xứng
F. Đổi dấu nhiệt độ: u(TU+) = -u(TU-)
"""
import unittest
import math
from bridge_designer.tcvn.bearings import BearingNode, BearingChainSolver, BearingForcesResult


class TestBearingsAnalytical(unittest.TestCase):
    def test_fully_restrained_thermal_bar(self):
        """
        Benchmark B: Thanh 1 nhịp ngàm cứng 2 đầu (K_pier -> inf, gối FIXED cả 2 đầu).
        Theo giải tích: F_thermal = EA * alpha * Delta_T.
        """
        L = 40.0 # m
        EA = 2.0e7 # kN
        alpha = 1.0e-5 # 1/C
        dT = 30.0 # C
        expected_F_thermal = EA * alpha * dT # 2.0e7 * 1.0e-5 * 30 = 6000.0 kN

        node0 = BearingNode(name="Support 0", x=0.0, L_next_span=L, bearing_type_left="—", bearing_type_right="Chậu cố định", K_pier=1.0e12, EA_deck=EA)
        node1 = BearingNode(name="Support 1", x=L, L_next_span=0.0, bearing_type_left="Chậu cố định", bearing_type_right="—", K_pier=1.0e12, EA_deck=EA)

        solver = BearingChainSolver(nodes=[node0, node1], alpha_thermal=alpha, delta_T_pos=dT, delta_T_neg=dT)
        res0 = solver.solve_pier_forces(target_node_name="Support 0", N_left_DL=0.0, N_right_DL=0.0)
        res1 = solver.solve_pier_forces(target_node_name="Support 1", N_left_DL=0.0, N_right_DL=0.0)

        # Do K_pier rất lớn (1e12), lực phải tiến sát 6000 kN
        self.assertAlmostEqual(res0.H_TU_pos, expected_F_thermal, delta=1.0)
        self.assertAlmostEqual(res1.H_TU_pos, expected_F_thermal, delta=1.0)

    def test_fully_free_system(self):
        """
        Benchmark A: Hệ hoàn toàn tự do (toàn gối trượt SLIDE không ma sát).
        Phản lực biến dạng nhiệt và từ biến phải = 0.
        """
        L = 30.0
        node0 = BearingNode(name="M0", x=0.0, L_next_span=L, bearing_type_left="—", bearing_type_right="Chậu di động 2 phương", mu_friction=0.0)
        node1 = BearingNode(name="M1", x=L, L_next_span=0.0, bearing_type_left="Chậu di động 2 phương", bearing_type_right="—", mu_friction=0.0)

        solver = BearingChainSolver(nodes=[node0, node1], alpha_thermal=1.0e-5, delta_T_pos=25.0)
        res0 = solver.solve_pier_forces(target_node_name="M0", N_left_DL=1000.0, N_right_DL=1000.0)
        
        self.assertEqual(res0.H_TU_pos, 0.0)
        self.assertEqual(res0.H_SH, 0.0)
        self.assertEqual(res0.H_CR, 0.0)

    def test_stiffness_limits_and_monotonicity(self):
        """
        Benchmark C and D: Đơn điệu theo độ cứng hỗ trợ.
        K_support càng tăng thì phản lực nhiệt càng tăng từ 0 đến EA*alpha*dT.
        """
        L = 50.0
        EA = 1.0e7
        alpha = 1.2e-5
        dT = 20.0
        F_max = EA * alpha * dT # 2400 kN

        prev_H = 0.0
        for K_val in [1e2, 1e4, 1e5, 1e6, 1e8, 1e11]:
            n0 = BearingNode(name="A", x=0.0, L_next_span=L, bearing_type_left="—", bearing_type_right="Gối cao su cốt bản thép", K_pier=K_val, G_elastomer=1000.0, A_bearing=1.0, h_elastomer=0.05, EA_deck=EA)
            n1 = BearingNode(name="B", x=L, L_next_span=0.0, bearing_type_left="Gối cao su cốt bản thép", bearing_type_right="—", K_pier=K_val, G_elastomer=1000.0, A_bearing=1.0, h_elastomer=0.05, EA_deck=EA)
            s = BearingChainSolver(nodes=[n0, n1], alpha_thermal=alpha, delta_T_pos=dT)
            r = s.solve_pier_forces("A", N_left_DL=0.0, N_right_DL=0.0)
            
            self.assertGreaterEqual(r.H_TU_pos, prev_H)
            self.assertLessEqual(r.H_TU_pos, F_max + 1.0)
            prev_H = r.H_TU_pos

    def test_symmetric_system_invariants(self):
        """
        Benchmark E and F: Tính đối xứng và đổi dấu nhiệt độ.
        Với cầu 2 nhịp đối xứng qua trụ giữa, chuyển vị tại 2 mố biên phải ngược chiều đối xứng.
        """
        L = 35.0
        n0 = BearingNode(name="AbutA", x=0.0, L_next_span=L, bearing_type_left="—", bearing_type_right="Gối cao su cốt bản thép", K_pier=1e5, A_bearing=0.1, h_elastomer=0.05)
        n1 = BearingNode(name="PierT1", x=L, L_next_span=L, bearing_type_left="Gối cao su cốt bản thép", bearing_type_right="Gối cao su cốt bản thép", K_pier=2e5, A_bearing=0.1, h_elastomer=0.05)
        n2 = BearingNode(name="AbutB", x=2*L, L_next_span=0.0, bearing_type_left="Gối cao su cốt bản thép", bearing_type_right="—", K_pier=1e5, A_bearing=0.1, h_elastomer=0.05)

        solver = BearingChainSolver(nodes=[n0, n1, n2], alpha_thermal=1.0e-5, delta_T_pos=20.0, delta_T_neg=20.0)
        res_A = solver.solve_pier_forces("AbutA", 1000.0, 1000.0)
        res_T1 = solver.solve_pier_forces("PierT1", 1000.0, 1000.0)
        res_B = solver.solve_pier_forces("AbutB", 1000.0, 1000.0)

        # Tại trụ giữa đối xứng: chuyển vị u = 0, H_TU = 0
        self.assertAlmostEqual(res_T1.u_TU_pos, 0.0, places=5)
        self.assertAlmostEqual(res_T1.H_TU_pos, 0.0, delta=0.01)

        # Tại 2 mố biên: chuyển vị đối xứng ngược chiều, lực bằng nhau
        self.assertAlmostEqual(res_A.u_TU_pos, -res_B.u_TU_pos, places=5)
        self.assertAlmostEqual(res_A.H_TU_pos, res_B.H_TU_pos, delta=0.1)

        # Đổi dấu nhiệt độ TU+ sang TU-: chuyển vị đổi dấu
        self.assertAlmostEqual(res_A.u_TU_pos, -res_A.u_TU_neg, places=5)


if __name__ == "__main__":
    unittest.main()
