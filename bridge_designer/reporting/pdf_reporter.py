"""
Module: reporting.pdf_reporter
Xuất Báo cáo Kỹ thuật Mố / Trụ Cầu định dạng PDF bằng ReportLab
"""
from typing import Optional
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas

from ..abutment.solver import AbutmentAnalysisResult
from ..pier.solver import PierAnalysisResult


class NumberedCanvas(canvas.Canvas):
    """Thêm Header và Số trang vào chân trang PDF"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header
        self.drawString(40, 810, "THUYẾT MINH TÍNH TOÁN KẾT CẤU CẦU — TCVN 11823:2017")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 805, 555, 805)

        # Footer
        self.line(40, 45, 555, 45)
        self.drawRightString(555, 32, f"Trang {self._pageNumber} / {page_count}")
        self.drawString(40, 32, "Phần mềm tính toán Mố Trụ Cầu TCVN 11823")
        self.restoreState()


def generate_abutment_pdf_report(result: AbutmentAnalysisResult, output_path: str) -> str:
    """Xuất file PDF tính toán Mố Cầu"""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=40, rightMargin=40, topMargin=50, bottomMargin=50
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=14, leading=18,
        textColor=colors.HexColor("#1e3a8a"), alignment=1, spaceAfter=8
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
        textColor=colors.HexColor("#475569"), alignment=1, spaceAfter=14
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11, leading=15,
        textColor=colors.HexColor("#1e40af"), spaceBefore=12, spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10
    )

    story = []
    m = result.model
    v = result.verification

    story.append(Paragraph("THUYẾT MINH TÍNH TOÁN KẾT CẤU MỐ CẦU", title_style))
    story.append(Paragraph(f"Dự án: {m.project_name} — Hạng mục: {m.abutment_name} | Tiêu chuẩn: TCVN 11823:2017", subtitle_style))

    story.append(Paragraph("I. TỔNG HỢP KẾT QUẢ KIỂM TOÁN CÁC HẠNG MỤC", h1_style))
    table_data = [
        [Paragraph("<b>Hạng mục kiểm toán</b>", cell_style), Paragraph("<b>Nội lực tính toán</b>", cell_style), Paragraph("<b>Sức kháng / Cho phép</b>", cell_style), Paragraph("<b>D/C</b>", cell_style), Paragraph("<b>Kết luận</b>", cell_style)],
        [Paragraph("1. Thân mố: Uốn Mr", cell_style), Paragraph(f"Mu = {v.stem.Mu_max:.1f} kNm", cell_style), Paragraph(f"Mr = {v.stem.flexure_check.Mr:.1f} kNm", cell_style), Paragraph(f"{v.stem.flexure_check.demand_capacity_ratio:.2f}", cell_style), Paragraph("ĐẠT" if v.stem.flexure_check.passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("2. Thân mố: Cắt Vr", cell_style), Paragraph(f"Vu = {v.stem.Vu_max:.1f} kN", cell_style), Paragraph(f"Vr = {v.stem.shear_check.Vr:.1f} kN", cell_style), Paragraph(f"{v.stem.shear_check.demand_capacity_ratio:.2f}", cell_style), Paragraph("ĐẠT" if v.stem.shear_check.passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("3. Tường đỉnh: Uốn Mr", cell_style), Paragraph(f"Mu = {v.backwall.Mu:.1f} kNm", cell_style), Paragraph(f"Mr = {v.backwall.flexure_check.Mr:.1f} kNm", cell_style), Paragraph(f"{v.backwall.flexure_check.demand_capacity_ratio:.2f}", cell_style), Paragraph("ĐẠT" if v.backwall.flexure_check.passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("4. Tường cánh: Ngàm đứng", cell_style), Paragraph(f"Mu = {v.wing_wall.Mu_vert_fix:.1f} kNm/m", cell_style), Paragraph(f"Mr = {v.wing_wall.flexure_vert_fix.Mr:.1f} kNm/m", cell_style), Paragraph(f"{v.wing_wall.flexure_vert_fix.demand_capacity_ratio:.2f}", cell_style), Paragraph("ĐẠT" if v.wing_wall.flexure_vert_fix.passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("5. Bệ mố: Mép trước", cell_style), Paragraph(f"Mu = {v.footing.Mu_front:.1f} kNm", cell_style), Paragraph(f"Mr = {v.footing.flexure_front.Mr:.1f} kNm", cell_style), Paragraph(f"{v.footing.flexure_front.demand_capacity_ratio:.2f}", cell_style), Paragraph("ĐẠT" if v.footing.flexure_front.passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("6. Bệ mố: Mép sau", cell_style), Paragraph(f"Mu = {v.footing.Mu_rear:.1f} kNm", cell_style), Paragraph(f"Mr = {v.footing.flexure_rear.Mr:.1f} kNm", cell_style), Paragraph(f"{v.footing.flexure_rear.demand_capacity_ratio:.2f}", cell_style), Paragraph("ĐẠT" if v.footing.flexure_rear.passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("7. Móng cọc: Nén Pmax", cell_style), Paragraph(f"Pmax = {result.piles.P_max_service:.1f} kN", cell_style), Paragraph(f"Pcp = {m.pile_capacity_allowable:.1f} kN", cell_style), Paragraph(f"{result.piles.P_max_service/m.pile_capacity_allowable:.2f}", cell_style), Paragraph("ĐẠT" if result.piles.passed_capacity else "KHÔNG ĐẠT", cell_style)]
    ]

    t = Table(table_data, colWidths=[160, 100, 110, 55, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    story.append(Spacer(1, 14))
    story.append(Paragraph("II. THÔNG SỐ KẾT CẤU CHÍNH", h1_style))
    param_data = [
        [Paragraph("Nhịp cầu L / Bề rộng W", cell_style), Paragraph(f"{m.span_L:.2f} m / {m.width_W:.2f} m", cell_style), Paragraph("Bê tông / Thép", cell_style), Paragraph(f"f'c={m.fc_prime} MPa / fy={m.fy} MPa", cell_style)],
        [Paragraph("Kích thước Bệ (B1 × C1 × H1)", cell_style), Paragraph(f"{m.B1} × {m.C1} × {m.H1} m", cell_style), Paragraph("Thân mố (B3 × H6)", cell_style), Paragraph(f"{m.B3} × {m.H6} m", cell_style)],
        [Paragraph("Đất đắp sau mố (γs / φ')", cell_style), Paragraph(f"{m.gamma_s} kN/m³ / {m.phi}°", cell_style), Paragraph("Móng cọc", cell_style), Paragraph(f"{m.total_piles} cọc D = {m.pile_diameter} m", cell_style)]
    ]
    t_param = Table(param_data, colWidths=[140, 115, 120, 140])
    t_param.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_param)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path


def generate_pier_pdf_report(result: PierAnalysisResult, output_path: str) -> str:
    """Xuất file PDF tính toán Trụ Cầu"""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=40, rightMargin=40, topMargin=50, bottomMargin=50
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=14, leading=18,
        textColor=colors.HexColor("#1e3a8a"), alignment=1, spaceAfter=8
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
        textColor=colors.HexColor("#475569"), alignment=1, spaceAfter=14
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11, leading=15,
        textColor=colors.HexColor("#1e40af"), spaceBefore=12, spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10
    )

    story = []
    m = result.model
    v = result.verification

    story.append(Paragraph("THUYẾT MINH TÍNH TOÁN KẾT CẤU TRỤ CẦU", title_style))
    story.append(Paragraph(f"Dự án: {m.project_name} — Hạng mục: {m.pier_name} | {m.pier_column_type} | Xà mũ: {m.cap_type}", subtitle_style))

    story.append(Paragraph("I. TỔNG HỢP KẾT QUẢ KIỂM TOÁN TRỤ", h1_style))
    table_data = [
        [Paragraph("<b>Hạng mục kiểm toán</b>", cell_style), Paragraph("<b>Nội lực tính toán</b>", cell_style), Paragraph("<b>Sức kháng / Cho phép</b>", cell_style), Paragraph("<b>D/C</b>", cell_style), Paragraph("<b>Kết luận</b>", cell_style)],
        [Paragraph("1. Thân trụ: Tương tác P-M-M", cell_style), Paragraph(f"Pu = {v.stem.Pu_max:.1f} kN", cell_style), Paragraph("Biểu đồ P-M Fiber", cell_style), Paragraph(f"{v.stem.utilization_pm:.2f}", cell_style), Paragraph("ĐẠT" if v.stem.pm_passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("2. Thân trụ: Sức kháng cắt Vr", cell_style), Paragraph(f"Vu = {v.stem.Vu_max:.1f} kN", cell_style), Paragraph(f"Vr = {v.stem.shear_check.Vr:.1f} kN", cell_style), Paragraph(f"{v.stem.shear_check.demand_capacity_ratio:.2f}", cell_style), Paragraph("ĐẠT" if v.stem.shear_check.passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("3. Xà mũ: Sức kháng uốn Mr", cell_style), Paragraph(f"Mu = {v.cap.Mu_max:.1f} kNm", cell_style), Paragraph(f"Mr = {(v.cap.rc_flexure.Mr if m.cap_type=='RC' else v.cap.pt_result.Mr):.1f} kNm", cell_style), Paragraph(f"{(v.cap.rc_flexure.demand_capacity_ratio if m.cap_type=='RC' else v.cap.pt_result.demand_capacity_ratio):.2f}", cell_style), Paragraph("ĐẠT" if v.cap.overall_passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("4. Bệ trụ: Sức kháng uốn", cell_style), Paragraph(f"Muy = {v.footing.Muy_max:.1f} kNm", cell_style), Paragraph(f"Mr = {v.footing.flexure_x.Mr:.1f} kNm", cell_style), Paragraph(f"{v.footing.flexure_x.demand_capacity_ratio:.2f}", cell_style), Paragraph("ĐẠT" if v.footing.flexure_x.passed else "KHÔNG ĐẠT", cell_style)],
        [Paragraph("5. Móng cọc: Nén Pmax", cell_style), Paragraph(f"Pmax = {result.piles.P_max_service:.1f} kN", cell_style), Paragraph(f"Pcp = {m.pile_capacity_allowable:.1f} kN", cell_style), Paragraph(f"{result.piles.P_max_service/m.pile_capacity_allowable:.2f}", cell_style), Paragraph("ĐẠT" if result.piles.passed_capacity else "KHÔNG ĐẠT", cell_style)]
    ]

    t = Table(table_data, colWidths=[160, 100, 110, 55, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
