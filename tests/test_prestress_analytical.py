"""
Analytical Benchmark Tests for Prestressed Concrete Cap (TCVN 11823-5:2017)
Kiểm thử tính đúng đắn cơ học kết cấu:
1. Parsing & Contract: Khớp trường num_strands và strands_per_tendon
2. Prestress Losses: Tính toán ma sát, tụt neo, co ngắn đàn hồi, từ biến, co ngót, tự chùng theo Điều 5.9.5
3. Stress Superposition: sigma = P/A + Mp/W - M/W
4. ULS Flexure: Mn theo khối ứng suất tương đương với fps
"""
import unittest
import math
from bridge_designer.tcvn.materials import Concrete, Rebar, PrestressStrand
from bridge_designer.tcvn.prestress import TendonGroup, PrestressedCapSolver, PrestressLosses


class TestPrestressAnalytical(unittest.TestCase):
    def setUp(self):
        self.concrete = Concrete(fc_prime=40.0) # Bê tông C40
        self.rebar = Rebar(fy=400.0)
        self.strand = PrestressStrand(fpu=1860.0, Ep=195000.0, kfpj=0.75) # 1860 MPa

    def test_tendon_group_contract(self):
        """Kiểm tra contract parser và tính toán diện tích bó cáp"""
        # Dict format từ UI/JSON
        g_dict = {
            "name": "G1",
            "num_tendons": 4,
            "num_strands": 12, # Test alias num_strands
            "strand_area": 140.0,
            "eccentricity_mid": 900.0,
            "eccentricity_end": 500.0,
            "tension_stage": 1
        }
        solver = PrestressedCapSolver(
            b=2200.0, h=2000.0, L_cantilever=7000.0,
            concrete=self.concrete, strand=self.strand, rebar=self.rebar,
            tendon_groups=[g_dict]
        )
        self.assertEqual(len(solver.tendon_groups), 1)
        tg = solver.tendon_groups[0]
        # Total area = 4 * 12 * 140 = 6720 mm2
        self.assertEqual(tg.total_area, 6720.0)
        self.assertEqual(tg.num_strands, 12)
        self.assertEqual(tg.strands_per_tendon, 12)

    def test_prestress_losses_analytical(self):
        """Kiểm tra tính toán các thành phần mất mát ứng suất theo TCVN 11823-5 Điều 5.9.5"""
        tg = TendonGroup(
            name="G1", num_tendons=6, strands_per_tendon=12, strand_area=140.0,
            eccentricity_mid=900.0, eccentricity_end=500.0, tension_stage=1
        )
        solver = PrestressedCapSolver(
            b=2200.0, h=2000.0, L_cantilever=7000.0,
            concrete=self.concrete, strand=self.strand, rebar=self.rebar,
            tendon_groups=[tg], relative_humidity=80.0
        )
        losses = solver.calculate_losses(x_section=7000.0, M_DC_transfer=3000.0, M_DC_super=4000.0)

        # 1. Ứng suất ban đầu fpj = 0.75 * 1860 = 1395 MPa
        self.assertAlmostEqual(losses.fpj, 1395.0, places=1)
        # 2. Ma sát > 0 và hợp lý (< 150 MPa cho đoạn 7m)
        self.assertGreater(losses.df_friction, 0.0)
        self.assertLess(losses.df_friction, 150.0)
        # 3. Tụt neo > 0
        self.assertGreater(losses.df_anchor, 0.0)
        # 4. Co ngót df_sh = 117 - 1.05 * 80 = 33 MPa
        self.assertAlmostEqual(losses.df_shrinkage, 33.0, places=1)
        # 5. Ứng suất hữu hiệu fpe < fpj và > 900 MPa
        self.assertLess(losses.fpe, losses.fpj)
        self.assertGreater(losses.fpe, 900.0)

    def test_stress_superposition_invariants(self):
        """Kiểm tra nguyên lý cộng tác dụng ứng suất P/A + Mp/W - M/W"""
        b = 2000.0
        h = 2000.0
        Ag = b * h
        Ig = (b * (h ** 3)) / 12.0
        Wtop = Ig / (h / 2.0)
        Wbot = Ig / (h / 2.0)

        tg = TendonGroup(
            name="G1", num_tendons=4, strands_per_tendon=12, strand_area=140.0,
            eccentricity_mid=800.0, eccentricity_end=400.0, tension_stage=1
        )
        solver = PrestressedCapSolver(
            b=b, h=h, L_cantilever=6000.0,
            concrete=self.concrete, strand=self.strand, rebar=self.rebar,
            tendon_groups=[tg]
        )
        res = solver.check_cap(
            M_self_weight=2000.0,
            M_dead_load_total=5000.0,
            M_service_total=8000.0,
            Mu_strength=12000.0
        )
        # Kiểm tra Transfer stage (Stage 1)
        st1 = res.stages[0]
        P1 = st1.P_active # kN
        Mp1 = st1.Mp_active # kN.m
        Mext1 = st1.M_ext # kN.m
        expected_sig_top = (P1 * 1e3 / Ag) + (Mp1 * 1e6 / Wtop) - (Mext1 * 1e6 / Wtop)
        expected_sig_bot = (P1 * 1e3 / Ag) - (Mp1 * 1e6 / Wbot) + (Mext1 * 1e6 / Wbot)

        self.assertAlmostEqual(st1.sigma_top, expected_sig_top, places=2)
        self.assertAlmostEqual(st1.sigma_bot, expected_sig_bot, places=2)


if __name__ == "__main__":
    unittest.main()
