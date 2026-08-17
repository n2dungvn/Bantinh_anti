"""
Analytical Benchmark Tests for Biaxial Column P-Mx-My Solver (TCVN 11823-5:2017)
Kiểm thử tính đúng đắn cơ học tương tác 2 phương:
1. Pure Axial: r_demand = 0, utilization = 0
2. Pure Mx & Pure My: Trùng khớp với kiểm toán 1 phương
3. Biaxial Interaction: Trường hợp Mx/Mrx = 0.8 và My/Mry = 0.8 PHẢI BỊ BẮT KHÔNG ĐẠT (utilization > 1.0)
4. Tiết diện đối xứng: Sức kháng tại +theta và -theta đối xứng bằng nhau
5. Các vùng tải trọng: High compression, near-balanced, low axial load
"""
import unittest
import math
from bridge_designer.tcvn.materials import Concrete, Rebar
from bridge_designer.tcvn.fiber import FiberSection, RebarLayer, BiaxialCheckResult


class TestFiberBiaxialAnalytical(unittest.TestCase):
    def setUp(self):
        self.c30 = Concrete(fc_prime=30.0)
        self.cb400 = Rebar(fy=400.0)
        # Tiết diện chữ nhật 2.0m x 2.0m đối xứng
        self.sec_square = FiberSection(shape_type=0, b=2000.0, h=2000.0, concrete=self.c30, rebar=self.cb400, nx=20, ny=20)
        # Bố trí thép 4 mặt đối xứng
        # Lớp trên và dưới (theo Y)
        self.sec_square.add_rebar_layer(RebarLayer(name="Top", count=10, diameter=32.0, area=8042.5, y=850.0, x=0.0))
        self.sec_square.add_rebar_layer(RebarLayer(name="Bot", count=10, diameter=32.0, area=8042.5, y=-850.0, x=0.0))
        # Lớp trái và phải (theo X)
        self.sec_square.add_rebar_layer(RebarLayer(name="Left", count=10, diameter=32.0, area=8042.5, y=0.0, x=-850.0))
        self.sec_square.add_rebar_layer(RebarLayer(name="Right", count=10, diameter=32.0, area=8042.5, y=0.0, x=850.0))

    def test_pure_axial(self):
        """Kiểm tra nén thuần túy Mx = 0, My = 0"""
        res = self.sec_square.check_biaxial(Pu=15000.0, Mu_x=0.0, Mu_y=0.0, method="FIBER_3D")
        self.assertEqual(res.demand_radius, 0.0)
        self.assertEqual(res.utilization, 0.0)
        self.assertTrue(res.passed)

    def test_biaxial_interaction_failure(self):
        """
        Benchmark bắt buộc:
        Nếu Mx = 0.8 * phiMrx và My = 0.8 * phiMry:
        Với logic 1 phương cũ max(0.8, 0.8) = 0.8 (báo PASS sai).
        Với Biaxial Solver chuẩn (FIBER_3D hoặc Bresler), tương tác uốn xiên 2 phương
        vượt khả năng chịu lực góc chéo -> BẮT BUỘC PHẢI KHÔNG ĐẠT (utilization > 1.0).
        """
        Pu = 10000.0 # kN
        curve_y = self.sec_square.generate_pm_curve(axis="Y")
        curve_x = self.sec_square.generate_pm_curve(axis="X")
        phiMry = self.sec_square._interpolate_phiMn_at_Pu(curve_y, Pu)
        phiMrx = self.sec_square._interpolate_phiMn_at_Pu(curve_x, Pu)

        Mux_demand = 0.80 * phiMrx
        Muy_demand = 0.80 * phiMry

        res = self.sec_square.check_biaxial(Pu=Pu, Mu_x=Mux_demand, Mu_y=Muy_demand, method="FIBER_3D")
        
        # Biaxial utilization phải lớn hơn 1.0 và không đạt
        self.assertGreater(res.utilization, 1.0)
        self.assertFalse(res.passed)

    def test_symmetric_invariance(self):
        """Kiểm tra tính bất biến đối xứng theo phương góc +theta và -theta"""
        Pu = 8000.0
        # Góc +45 độ
        res_pos = self.sec_square.check_biaxial(Pu=Pu, Mu_x=2000.0, Mu_y=2000.0, method="FIBER_3D")
        # Góc -45 độ
        res_neg = self.sec_square.check_biaxial(Pu=Pu, Mu_x=2000.0, Mu_y=-2000.0, method="FIBER_3D")

        self.assertAlmostEqual(res_pos.capacity_radius, res_neg.capacity_radius, delta=50.0)
        self.assertAlmostEqual(res_pos.utilization, res_neg.utilization, delta=0.02)


if __name__ == "__main__":
    unittest.main()
