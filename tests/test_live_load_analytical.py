"""
Analytical Benchmark Tests for HL-93 Live Load Engine (TCVN 11823-3:2017)
Kiểm thử tính đúng đắn cơ học đường ảnh hưởng:
1. Nhịp không đều: Ls1 != Ls2 -> R_s1 != R_s2
2. Đóng góp Xe tải, Xe 2 trục, Tải làn
3. Hệ số làn xe m (TCVN Bảng 3.6.1.1.2-1): 1 làn = 1.20, 2 làn = 1.00, 3 làn = 0.85, >=4 làn = 0.65
4. Độ lệch tâm ngang cầu Mx = N * ey
"""
import unittest
import math
from bridge_designer.pier.model import PierModel
from bridge_designer.pier.loads import calculate_pier_loads
from bridge_designer.tcvn.loads import get_multi_lane_factor


class TestLiveLoadAnalytical(unittest.TestCase):
    def test_multi_lane_factors(self):
        """Kiểm tra hệ số làn xe TCVN 11823-3 Bảng 3.6.1.1.2-1"""
        self.assertEqual(get_multi_lane_factor(1), 1.20)
        self.assertEqual(get_multi_lane_factor(2), 1.00)
        self.assertEqual(get_multi_lane_factor(3), 0.85)
        self.assertEqual(get_multi_lane_factor(4), 0.65)
        self.assertEqual(get_multi_lane_factor(5), 0.65)

    def test_unequal_spans_influence_response(self):
        """
        Kiểm tra nhịp không đều Ls1 = 25m, Ls2 = 45m:
        Phản lực 2 nhịp phải tích hợp theo đúng đường ảnh hưởng của 2 nhịp riêng biệt
        chứ không lấy 2 * nhịp 1.
        """
        m_unequal = PierModel(Ls1=25.0, Ls2=45.0, num_lanes=2, qlan=9.3, IM=0.25)
        loads_unequal = calculate_pier_loads(m_unequal)

        # Kiểm tra tải trọng chất 2 nhịp cho 2 làn
        ll_unequal = loads_unequal.loads_stem_base["LL_2span_2lan_dung"]
        self.assertGreater(ll_unequal.N, 0.0)

        # Ls1 = 25m, Ls2 = 25m
        m_equal = PierModel(Ls1=25.0, Ls2=25.0, num_lanes=2, qlan=9.3, IM=0.25)
        loads_equal = calculate_pier_loads(m_equal)
        ll_equal = loads_equal.loads_stem_base["LL_2span_2lan_dung"]

        # Phản lực cầu nhịp (25m + 45m) phải lớn hơn đáng kể so với cầu nhịp (25m + 25m)
        self.assertGreater(ll_unequal.N, ll_equal.N)

    def test_transverse_eccentricity(self):
        """Kiểm tra mô men lệch tâm ngang cầu Mx = N * avg_ey"""
        m = PierModel(num_lanes=2, width_Bxe=9.0)
        loads = calculate_pier_loads(m)

        ll_lech = loads.loads_stem_base["LL_2span_2lan_lech"]
        ll_dung = loads.loads_stem_base["LL_2span_2lan_dung"]

        self.assertEqual(ll_dung.Mx, 0.0)
        self.assertGreater(abs(ll_lech.Mx), 0.0)


if __name__ == "__main__":
    unittest.main()
