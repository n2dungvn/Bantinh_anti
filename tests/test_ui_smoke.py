"""
Module: tests.test_ui_smoke
Smoke test cho FastAPI Web Application và API endpoints sử dụng in-process TestClient.
Đảm bảo kiểm tra toàn diện giao diện và API mà KHÔNG cần khởi chạy server mạng thật,
KHÔNG mở browser và KHÔNG làm thay đổi repository (side-effect free).
"""
import sys
import unittest
import tempfile
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
import bridge_designer.ui.app

app_module = sys.modules["bridge_designer.ui.app"]
app = app_module.app


class TestUiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.orig_output_dir = app_module.OUTPUT_DIR
        app_module.OUTPUT_DIR = cls.temp_dir.name
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app_module.OUTPUT_DIR = cls.orig_output_dir
        cls.temp_dir.cleanup()

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

    @patch("bridge_designer.ui.app.generate_abutment_docx_report", return_value="dummy.docx")
    @patch("bridge_designer.ui.app.generate_abutment_html_report", return_value="dummy.html")
    @patch("bridge_designer.ui.app.generate_abutment_pdf_report", return_value="dummy.pdf")
    def test_post_calculate_abutment(self, mock_pdf, mock_html, mock_docx):
        """Kiểm tra API tính toán Mố cầu POST /api/calculate/abutment"""
        preset_res = self.client.get("/api/presets/default_abutment")
        self.assertEqual(preset_res.status_code, 200)
        payload = preset_res.json()

        calc_res = self.client.post("/api/calculate/abutment", json=payload)
        self.assertEqual(calc_res.status_code, 200)
        result = calc_res.json()

        self.assertIn("summary", result)
        self.assertIn("reports", result)
        self.assertIn("stem_flexure", result["summary"])
        self.assertIn("pass", result["summary"]["stem_flexure"])

    @patch("bridge_designer.ui.app.generate_pier_docx_report", return_value="dummy.docx")
    @patch("bridge_designer.ui.app.generate_pier_html_report", return_value="dummy.html")
    @patch("bridge_designer.ui.app.generate_pier_pdf_report", return_value="dummy.pdf")
    def test_post_calculate_pier_rc(self, mock_pdf, mock_html, mock_docx):
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
        self.assertIn("reports", result)

    @patch("bridge_designer.ui.app.generate_pier_docx_report", return_value="dummy.docx")
    @patch("bridge_designer.ui.app.generate_pier_html_report", return_value="dummy.html")
    @patch("bridge_designer.ui.app.generate_pier_pdf_report", return_value="dummy.pdf")
    def test_post_calculate_pier_pt(self, mock_pdf, mock_html, mock_docx):
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
        self.assertIn("reports", result)

    @patch("bridge_designer.ui.app.generate_pier_docx_report", return_value="dummy.docx")
    @patch("bridge_designer.ui.app.generate_pier_html_report", return_value="dummy.html")
    @patch("bridge_designer.ui.app.generate_pier_pdf_report", return_value="dummy.pdf")
    def test_post_calculate_pier_twin(self, mock_pdf, mock_html, mock_docx):
        """Kiểm tra API tính toán Trụ 2 thân RC & PT POST /api/calculate/pier"""
        for name in ["default_pier_twin_rc", "default_pier_twin_pt"]:
            preset_res = self.client.get(f"/api/presets/{name}")
            self.assertEqual(preset_res.status_code, 200)
            payload = preset_res.json()

            calc_res = self.client.post("/api/calculate/pier", json=payload)
            self.assertEqual(calc_res.status_code, 200)
            result = calc_res.json()
            self.assertIn("summary", result)
            self.assertIn("reports", result)


if __name__ == "__main__":
    unittest.main()
