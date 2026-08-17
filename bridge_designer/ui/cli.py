"""
Module: ui.cli
Giao diện dòng lệnh (Command Line Interface) cho phần mềm tính toán mố và trụ cầu.
Sử dụng:
  python -m bridge_designer.ui.cli --module abutment --input data/default_abutment.json --output Bao_cao_Mo.docx
  python -m bridge_designer.ui.cli --module pier --input data/default_pier_rc.json --format all
"""
import argparse
import json
import os
import sys

from ..abutment import AbutmentModel, AbutmentSolver
from ..pier import PierModel, PierSolver
from ..reporting import (
    generate_abutment_docx_report, generate_pier_docx_report,
    generate_abutment_html_report, generate_pier_html_report,
    generate_abutment_pdf_report, generate_pier_pdf_report
)


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Phần mềm Tính toán Mố & Trụ Cầu theo TCVN 11823-2017"
    )
    parser.add_argument(
        "--cli", "-c", action="store_true", default=False,
        help="Chạy chế độ dòng lệnh (CLI)"
    )
    parser.add_argument(
        "--module", "-m", choices=["abutment", "pier", "mo", "tru"], default="abutment",
        help="Module tính toán: abutment (mố) hoặc pier (trụ)"
    )
    parser.add_argument(
        "--input", "-i", type=str, default="",
        help="Đường dẫn file cấu hình JSON dự án"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="",
        help="Đường dẫn file báo cáo đầu ra (.docx, .html, .pdf)"
    )
    parser.add_argument(
        "--format", "-f", choices=["docx", "html", "pdf", "all"], default="all",
        help="Định dạng báo cáo: docx, html, pdf, hoặc all"
    )

    args = parser.parse_args()

    mod = "abutment" if args.module in ["abutment", "mo"] else "pier"
    data = {}

    if args.input and os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Đã nạp file dữ liệu: {args.input}")
    else:
        print(f"Sử dụng thông số mặc định đối chuẩn cho {mod.upper()}...")

    out_dir = os.path.dirname(args.output) if args.output else "output_reports"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    if mod == "abutment":
        model = AbutmentModel(**data) if data else AbutmentModel()
        solver = AbutmentSolver(model)
        result = solver.solve()

        base_name = os.path.splitext(args.output)[0] if args.output else os.path.join("output_reports", f"{model.abutment_name}_Bao_cao")

        if args.format in ["docx", "all"]:
            p = generate_abutment_docx_report(result, f"{base_name}.docx")
            print(f"✓ Đã xuất báo cáo Word: {p}")
        if args.format in ["html", "all"]:
            p = generate_abutment_html_report(result, f"{base_name}.html")
            print(f"✓ Đã xuất báo cáo HTML: {p}")
        if args.format in ["pdf", "all"]:
            p = generate_abutment_pdf_report(result, f"{base_name}.pdf")
            print(f"✓ Đã xuất báo cáo PDF: {p}")

        print(f"\nKẾT QUẢ: {'ĐẠT TOÀN BỘ' if result.is_success else 'MỘT SỐ MỤC CHƯA ĐẠT'}")

    else:
        model = PierModel(**data) if data else PierModel()
        solver = PierSolver(model)
        result = solver.solve()

        base_name = os.path.splitext(args.output)[0] if args.output else os.path.join("output_reports", f"{model.pier_name}_Bao_cao")

        if args.format in ["docx", "all"]:
            p = generate_pier_docx_report(result, f"{base_name}.docx")
            print(f"✓ Đã xuất báo cáo Word: {p}")
        if args.format in ["html", "all"]:
            p = generate_pier_html_report(result, f"{base_name}.html")
            print(f"✓ Đã xuất báo cáo HTML: {p}")
        if args.format in ["pdf", "all"]:
            p = generate_pier_pdf_report(result, f"{base_name}.pdf")
            print(f"✓ Đã xuất báo cáo PDF: {p}")

        print(f"\nKẾT QUẢ: {'ĐẠT TOÀN BỘ' if result.is_success else 'MỘT SỐ MỤC CHƯA ĐẠT'}")


if __name__ == "__main__":
    main()
