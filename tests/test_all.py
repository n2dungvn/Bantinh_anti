"""
Unit and benchmark tests for Bridge Designer TCVN 11823-2017
"""
import unittest
import os
from bridge_designer.tcvn import (
    Concrete, Rebar, PrestressStrand, Soil, Water,
    check_flexure_rectangular, check_shear_beam, check_crack_control,
    FiberSection, RebarLayer, Pile, PileGroupSolver,
    BearingNode, BearingChainSolver, TendonGroup, PrestressedCapSolver
)
from bridge_designer.abutment import AbutmentModel, AbutmentSolver
from bridge_designer.pier import PierModel, PierSolver
from bridge_designer.reporting import (
    generate_abutment_docx_report, generate_pier_docx_report,
    generate_abutment_html_report, generate_pier_html_report,
    generate_abutment_pdf_report, generate_pier_pdf_report
)


class TestTCVNCore(unittest.TestCase):
    def test_concrete_properties(self):
        c = Concrete(fc_prime=30.0, gamma_c=24.5)
        self.assertAlmostEqual(c.fr, 3.45065, places=3)
        self.assertAlmostEqual(c.beta1, 0.83571, places=3)
        self.assertAlmostEqual(c.Ec, 28561.3, delta=10.0)

    def test_soil_properties(self):
        s = Soil(gamma_s=19.25, phi=30.0, delta=0.0, beta=0.0)
        self.assertAlmostEqual(s.Ka, 1.0 / 3.0, delta=0.01)

    def test_flexure_rectangular(self):
        c = Concrete(fc_prime=30.0)
        r = Rebar(fy=400.0)
        # b = 1000mm, h = 500mm, dc = 75mm, As = 2094.4 mm2
        res = check_flexure_rectangular(
            b=1000.0, h=500.0, dc=75.0, As=2094.4,
            Mu=235.8, concrete=c, rebar=r
        )
        self.assertTrue(res.passed)
        self.assertGreater(res.Mr, 235.8)

    def test_fiber_section(self):
        c = Concrete(fc_prime=30.0)
        r = Rebar(fy=400.0)
        sec = FiberSection(shape_type=0, b=5500.0, h=1600.0, concrete=c, rebar=r, nx=20, ny=20)
        sec.add_rebar_layer(RebarLayer(name="Top", count=10, diameter=32.0, area=8042.5, y=700.0))
        sec.add_rebar_layer(RebarLayer(name="Bot", count=10, diameter=32.0, area=8042.5, y=-700.0))
        pm_curve = sec.generate_pm_curve(axis="Y", num_points=10)
        self.assertTrue(len(pm_curve) > 5)
        pass_res, _, _, util = sec.check_demand_capacity(Pu=20000.0, Mu_y=5000.0, Mu_x=1000.0, curve_y=pm_curve)
        self.assertTrue(pass_res)
        self.assertLess(util, 1.0)


class TestAbutmentModule(unittest.TestCase):
    def test_abutment_solve(self):
        m = AbutmentModel()
        solver = AbutmentSolver(m)
        res = solver.solve()
        self.assertGreater(res.loads.DC2_total, 10000.0)
        self.assertGreater(res.piles.P_max_strength, 4000.0)
        self.assertTrue(res.verification.stem.flexure_check.passed)
        self.assertTrue(res.verification.backwall.flexure_check.passed)
        self.assertTrue(res.verification.wing_wall.flexure_vert_fix.passed)


class TestPierModule(unittest.TestCase):
    def test_pier_rc_single(self):
        m = PierModel(cap_type="RC", pier_column_type="SINGLE")
        solver = PierSolver(m)
        res = solver.solve()
        self.assertGreater(res.piles.P_max_strength, 4000.0)
        self.assertTrue(res.verification.stem.pm_passed)
        self.assertTrue(res.verification.cap.overall_passed)

    def test_pier_pt_single(self):
        m = PierModel(cap_type="PT", pier_column_type="SINGLE")
        solver = PierSolver(m)
        res = solver.solve()
        self.assertTrue(res.verification.cap.overall_passed)
        self.assertTrue(res.verification.cap.pt_result.flexure_passed)

    def test_pier_twin_columns(self):
        m = PierModel(cap_type="RC", pier_column_type="TWIN", spacing_twin_columns=4.0)
        solver = PierSolver(m)
        res = solver.solve()
        self.assertTrue(res.verification.stem.pm_passed)


class TestReporting(unittest.TestCase):
    def test_reports_generation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            res_mo = AbutmentSolver(AbutmentModel()).solve()
            p1 = generate_abutment_docx_report(res_mo, os.path.join(tmp_dir, "test_mo.docx"))
            p2 = generate_abutment_html_report(res_mo, os.path.join(tmp_dir, "test_mo.html"))
            p3 = generate_abutment_pdf_report(res_mo, os.path.join(tmp_dir, "test_mo.pdf"))
            self.assertTrue(os.path.exists(p1))
            self.assertTrue(os.path.exists(p2))
            self.assertTrue(os.path.exists(p3))


if __name__ == "__main__":
    unittest.main()
