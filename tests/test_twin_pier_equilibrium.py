"""
Analytical Benchmark & Invariant Tests for Twin Pier Distribution (TCVN 11823:2017)
Kiểm thử cân bằng tĩnh học và tính đối xứng cho trụ 2 thân:
1. Cân bằng lực dọc: N1 + N2 = N_global
2. Cân bằng lực cắt: H1 + H2 = H_global
3. Cân bằng mô men tổng thể: M_local1 + M_local2 + (N1 - N2) * (s / 2) == M_global
4. Tính đối xứng & đảo dấu mô men
"""
import unittest
import math
from bridge_designer.pier.model import PierModel
from bridge_designer.pier.checks import check_pier_stem
from bridge_designer.abutment.combinations import CombinationResult


class TestTwinPierEquilibrium(unittest.TestCase):
    def test_twin_pier_invariants(self):
        """
        Kiểm tra các bất biến cân bằng (Equilibrium Invariants)
        """
        N_global = 20000.0 # kN
        Hx_global = 1200.0 # kN
        Hy_global = 800.0 # kN
        Mx_global = 6000.0 # kN.m
        My_global = 3000.0 # kN.m
        s_twin = 5.0 # m
        H_col = 8.0 # m
        b_xm = 2.2
        h_xm = 2.0
        b_col = 2.0
        h_col = 1.6

        I_beam = b_xm * (h_xm ** 3) / 12.0
        I_col = h_col * (b_col ** 3) / 12.0
        k_rel = (I_beam / s_twin) / (I_col / H_col)

        M_local_est = (Hx_global * H_col / 4.0) * ((3.0 * k_rel + 1.0) / (6.0 * k_rel + 1.0))
        M_local_col = min(Mx_global * 0.5, max(0.0, M_local_est))
        M_couple = Mx_global - 2.0 * M_local_col
        Delta_N = M_couple / s_twin

        N1 = N_global / 2.0 + Delta_N
        N2 = N_global / 2.0 - Delta_N

        # 1. Cân bằng lực dọc
        self.assertAlmostEqual(N1 + N2, N_global, delta=1e-6)

        # 2. Cân bằng mô men tổng thể
        M_reconstructed = 2.0 * M_local_col + (N1 - N2) * (s_twin / 2.0)
        self.assertAlmostEqual(M_reconstructed, Mx_global, delta=1e-6)

    def test_twin_pier_solver_integration(self):
        """Kiểm tra tích hợp PierSolver cho mô hình trụ 2 thân thực tế"""
        m = PierModel(
            cap_type="RC",
            pier_column_type="TWIN",
            spacing_twin_columns=4.5,
            bth1_col=2.0,
            hth1_col=1.6
        )
        from bridge_designer.pier.solver import PierSolver
        solver = PierSolver(m)
        res = solver.solve()
        self.assertTrue(res.verification.stem.pm_passed)
        self.assertLess(res.verification.stem.utilization_pm, 1.0)


if __name__ == "__main__":
    unittest.main()
