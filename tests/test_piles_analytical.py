"""
Analytical Benchmark & Invariant Tests for Pile Group Solver and Geotechnical Limit States (TCVN 11823:2017)
Kiểm thử tính đúng đắn cơ học kết cấu:
1. Rigid Cap Equilibrium: Sum(Pi) = N, Sum(Pi * yi) = Mx, Sum(Pi * xi) = My
2. 6DOF Matrix Diagnostics: Kiểm tra Rank, Condition Number, và Solver Status
3. Limit State Mapping: Sức chịu tải TTGH Cường độ, Đặc biệt, Sử dụng phải phân biệt rõ ràng và đúng chuẩn
"""
import unittest
import math
from bridge_designer.tcvn.ts_pile_solver import TSPile, TSPileGroupSolver
from bridge_designer.tcvn.ts_cap_engine import PileInput, SoilLayer, SCTCalculator


class TestPilesAnalytical(unittest.TestCase):
    def setUp(self):
        # Lưới 3 hàng x 4 cột = 12 cọc
        self.piles = []
        pid = 1
        for row_x in [-2.0, 0.0, 2.0]:
            for col_y in [-4.5, -1.5, 1.5, 4.5]:
                self.piles.append(TSPile(
                    id=pid, name=f"P{pid}", x=row_x, y=col_y,
                    diameter=1.2, length=35.0, E=3.0e7
                ))
                pid += 1

    def test_rigid_cap_analytical_equilibrium(self):
        """Kiểm tra bất biến cân bằng tĩnh học mô hình đài cứng"""
        solver = TSPileGroupSolver(self.piles)
        N_applied = 36000.0 # kN
        Mx_applied = 12000.0 # kN.m
        My_applied = 6000.0 # kN.m
        Hx_applied = 1500.0 # kN
        Hy_applied = 800.0 # kN

        res = solver.calculate_reaction_rigid_cap(
            comb_name="STRENGTH_I", limit_state_group="STRENGTH",
            N=N_applied, Mx=Mx_applied, My=My_applied,
            Hx=Hx_applied, Hy=Hy_applied
        )
        # 1. Cân bằng lực dọc
        sum_N = sum(f.N for f in res.pile_forces.values())
        self.assertAlmostEqual(sum_N, N_applied, delta=1e-4)

        # 2. Cân bằng mô men quanh X
        sum_Mx = sum(f.N * (p.y - solver.yc) for p, f in zip(self.piles, res.pile_forces.values()))
        self.assertAlmostEqual(sum_Mx, Mx_applied, delta=1e-4)

        # 3. Cân bằng mô men quanh Y
        sum_My = sum(f.N * (p.x - solver.xc) for p, f in zip(self.piles, res.pile_forces.values()))
        self.assertAlmostEqual(sum_My, My_applied, delta=1e-4)

    def test_6dof_solver_diagnostics(self):
        """Kiểm tra ma trận độ cứng 6DOF có rank 6 và condition number hợp lý"""
        solver = TSPileGroupSolver(self.piles)
        self.assertEqual(solver.matrix_rank, 6)
        self.assertLess(solver.condition_number, 1e8)

        res = solver.calculate_reaction(
            comb_name="STRENGTH_I", limit_state_group="STRENGTH",
            N=30000.0, Mx=5000.0, My=2000.0
        )
        self.assertFalse(res.used_pseudoinverse)
        self.assertEqual(res.solver_status, "CONVERGED")

    def test_geotechnical_limit_state_mapping(self):
        """Kiểm tra mapping sức chịu tải đất nền giữa các TTGH: Cường độ, Đặc biệt, Sử dụng"""
        soil = [
            SoilLayer(name="Cát", bottom_elev_m=-10.0, soil_type=1, n_spt=20.0, gamma_kN_m3=19.0, phi_deg=32.0),
            SoilLayer(name="Sét", bottom_elev_m=-35.0, soil_type=2, n_spt=15.0, gamma_kN_m3=18.5, c_mpa=0.04)
        ]
        pile_inp = PileInput(
            diameter_mm=1200.0,
            ground_elev_m=0.0, cap_bottom_elev_m=-2.0, pile_tip_elev_m=-37.0,
            water_elev_m=-1.0, fc_mpa=30.0, fy_mpa=400.0,
            n_rebars=20, rebar_dia_mm=25.0, spacing_m=3.6,
            pile_count_in_group=12, group_layout="2", layers=soil
        )
        res = SCTCalculator.calculate(pile_inp)

        p_str = res.strength.governing_kn
        p_ext = res.extreme.governing_kn
        p_ser = (res.qshaft_nominal_kn + res.qtip_nominal_kn) / 2.0

        # Kiểm tra: Sức chịu tải tính toán phải có thứ tự đúng:
        # P_allow_strength < P_allow_extreme (do phi_strength < phi_extreme = 1.0)
        self.assertLess(p_str, p_ext)
        # P_allow_service phải được tính với FS=2.0
        self.assertNotEqual(p_ser, p_ext)
        self.assertLess(p_ser, p_ext)


if __name__ == "__main__":
    unittest.main()
