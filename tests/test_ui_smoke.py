"""
Module: tests.test_ui_smoke
Smoke test cho FastAPI Web Application và API endpoints sử dụng in-process TestClient.
Đảm bảo kiểm tra toàn diện giao diện và API mà KHÔNG cần khởi chạy server mạng thật hay mở browser.
"""
import unittest
import json
import os
from fastapi.testclient import TestClient
from bridge_designer.ui.app import app


class TestUiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_index_html(self):
        """Kiểm tra endpoint GET / phục vụ giao diện Web HTML"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("PHẦN MỀM TÍNH TOÁN KẾT CẤU MỐ & TRỤ CẦU", response.text)

    def test_get_presets(self):
        """Kiểm tra nạp toàn bộ các file mẫu JSON đối chuẩn"""
        presets = [
            "default_abutment",
            "default_pier_rc",
            "default_pier_pt",
            "default_pier_twin_rc",
            "default_pier_twin_pt"
        ]
        for name in presets:
            res = self.client.get(f"/api/presets/{name}")
            self.assertEqual(res.status_code, 200, f"Preset {name} không tải được (HTTP {res.status_code})")
            data = res.json()
            self.assertIsInstance(data, dict)
            self.assertGreater(len(data), 5)

    def test_post_calculate_abutment(self):
        """Kiểm tra API tính toán Mố cầu POST /api/calculate/abutment"""
        preset_res = self.client.get("/api/presets/default_abutment")
        self.assertEqual(preset_res.status_code, 200)
        payload = preset_res.json()

        calc_res = self.client.post("/api/calculate/abutment", json=payload)
        self.assertEqual(calc_res.status_code, 200)
        result = calc_res.json()

        self.assertIn("summary", result)
        self.assertIn("reports", result)
        self.assertTrue(result["summary"]["stem_flexure"]["pass"])

    def test_post_calculate_pier_rc(self):
        """Kiểm tra API tính toán Trụ RC POST /api/calculate/pier"""
        preset_res = self.client.get("/api/presets/default_pier_rc")
        self.assertEqual(preset_res.status_code, 200)
        payload = preset_res.json()

        calc_res = self.client.post("/api/calculate/pier", json=payload)
        self.assertEqual(calc_res.status_code, 200)
        result = calc_res.json()

        self.assertIn("summary", result)
        self.assertIn("bearing_forces", result)
        self.assertIn("loads_stem", result)
        self.assertIn("loads_footing", result)
        self.assertIn("H_TU_pos", result["bearing_forces"])

    def test_post_calculate_pier_pt(self):
        """Kiểm tra API tính toán Trụ DƯL (PT) POST /api/calculate/pier"""
        preset_res = self.client.get("/api/presets/default_pier_pt")
        self.assertEqual(preset_res.status_code, 200)
        payload = preset_res.json()

        calc_res = self.client.post("/api/calculate/pier", json=payload)
        self.assertEqual(calc_res.status_code, 200)
        result = calc_res.json()

        self.assertIn("summary", result)
        self.assertIn("bearing_forces", result)
        self.assertIn("pt_stages", result)
        self.assertGreater(len(result["pt_stages"]), 0)

    def test_post_calculate_pier_twin(self):
        """Kiểm tra API tính toán Trụ 2 thân RC & PT POST /api/calculate/pier"""
        for name in ["default_pier_twin_rc", "default_pier_twin_pt"]:
            preset_res = self.client.get(f"/api/presets/{name}")
            self.assertEqual(preset_res.status_code, 200)
            payload = preset_res.json()

            calc_res = self.client.post("/api/calculate/pier", json=payload)
            self.assertEqual(calc_res.status_code, 200)
            result = calc_res.json()
            self.assertIn("summary", result)


if __name__ == "__main__":
    unittest.main()
