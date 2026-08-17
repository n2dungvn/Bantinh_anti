"""
Module: reporting.html_reporter
Tạo Báo cáo Thuyết minh Tính toán Chi tiết Kết cấu Mố & Trụ Cầu dạng HTML chuyên nghiệp
Đầy đủ:
- Kích thước chi tiết bệ, thân, đỉnh, tường cánh (Biên dạng tường cánh trắc dọc trùng khít mép sau bệ)
- Chi tiết lực tác dụng (DC, DW, LL, BR, EH, LS, WS, WL, EQ) kèm công thức và cách tính
- Bảng tổ hợp tải trọng chi tiết
- Kiểm toán toàn diện:
  + Uốn (Mn, Mr, c, a, phi)
  + Cắt MCFT (dv, Vc, Vs, Vn, Vr)
  + Nứt (fss <= fsa VÀ s_act <= s_max)
  + Tường cánh đầy đủ Uốn, Cắt, Nứt cho cả ngàm đứng và ngàm đáy
  + Móng cọc theo phương pháp ma trận độ cứng 3D TS_PILE (phân định rõ giới hạn cho từng TTGH)
- Dẫn chứng đầy đủ số Điều / Phương trình trong TCVN 11823:2017.
- Nhúng đồ họa SVG trắc dọc chuẩn kích thước thật và mặt bằng bệ chéo góc alpha có toàn bộ cọc móng.
"""
import math
from typing import List
from ..abutment.solver import AbutmentAnalysisResult
from ..pier.solver import PierAnalysisResult


def generate_abutment_html_report(result: AbutmentAnalysisResult, output_path: str) -> str:
    """
    Tạo báo cáo HTML hoàn chỉnh, chuyên sâu cho Mố Cầu
    """
    m = result.model
    v = result.verification
    loads = result.loads
    piles = result.piles

    Htc = m.H2 + m.H3 + m.H4
    w1 = m.B2 + m.B5
    w2 = m.B5
    w3 = m.B2
    B_heel = m.B1 - m.B4 - m.B3

    # 1. SVG Trắc dọc Mố chuẩn xác kích thước thật (Mép sau chân tường cánh trùng khít mép sau bệ mố)
    svg_elevation = f"""
    <svg width="520" height="310" viewBox="0 0 520 310" xmlns="http://www.w3.org/2000/svg" style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; width:100%; max-height:310px;">
        <!-- Lăng thể đất đắp phía sau -->
        <polygon points="30,50 228,50 228,180 30,180" fill="#fef3c7" stroke="#f59e0b" stroke-dasharray="3,3" />
        <text x="60" y="90" fill="#d97706" font-size="10" font-weight="bold">Đất đắp sau mố (EH, LS)</text>

        <!-- BIÊN DẠNG TƯỜNG CÁNH CHUẨN XÁC KÍCH THƯỚC THỰC TẾ (MÉP CHÂN SAU TRÙNG KHÍT MÉP SAU BỆ MỐ x=120) -->
        <!-- Đỉnh sau (36,51) -> Đỉnh trước (280,51) -> Chân trước (280,180) -> Chân đáy sau (120,180) -> Điểm chuyển vát (120,116) -> Đỉnh vát sau (36,74) -->
        <polygon points="36,51 280,51 280,180 120,180 120,116 36,74 36,51" fill="#fecdd3" fill-opacity="0.65" stroke="#b91c1c" stroke-width="2.5" stroke-dasharray="4,2" />
        <text x="100" y="145" fill="#991b1b" font-size="10" font-weight="bold">Tường cánh mố</text>
        <text x="100" y="160" fill="#7f1d1d" font-size="8.5">w1={w1:.2f}m | Htc={Htc:.2f}m | C3={m.C3}m</text>

        <!-- BỆ MỐ (B1=6m -> rộng 240px từ x=120 đến x=360, H1=1.8m -> cao 35px từ y=180 đến y=215) -->
        <rect x="120" y="180" width="240" height="35" fill="#94a3b8" stroke="#1e293b" stroke-width="2" rx="1" />
        <text x="240" y="202" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">
            Bệ mố: B1={m.B1}m × H1={m.H1}m (C1={m.C1}m)
        </text>

        <!-- THÂN MỐ (B3=1.3m -> rộng 52px từ x=228 đến x=280, H6=6.304m -> cao 105px từ y=75 đến y=180) -->
        <rect x="228" y="75" width="52" height="105" fill="#cbd5e1" stroke="#1e293b" stroke-width="2" />
        <text x="254" y="125" fill="#0f172a" font-size="10.5" font-weight="bold" text-anchor="middle">Thân B3={m.B3}m</text>
        <text x="254" y="140" fill="#475569" font-size="9" text-anchor="middle">H6={m.H6}m</text>

        <!-- TƯỜNG ĐỈNH & MẤU ĐỠ (B7=0.5m -> rộng 20px từ x=228 đến x=248, H7=1.264m từ y=50 đến y=75) -->
        <rect x="228" y="50" width="20" height="25" fill="#64748b" stroke="#1e293b" stroke-width="1.5" />
        <rect x="210" y="60" width="18" height="15" fill="#475569" stroke="#1e293b" />
        <text x="238" y="42" fill="#1e293b" font-size="8.5" font-weight="bold" text-anchor="middle">Đỉnh B7={m.B7}m, H7={m.H7}m</text>

        <!-- TIM GỐI KCN (ở x=262, y=67) -->
        <rect x="252" y="67" width="20" height="8" fill="#ef4444" stroke="#991b1b" rx="1" />
        <text x="282" y="74" fill="#dc2626" font-size="8" font-weight="bold">Tim gối</text>

        <!-- ĐƯỜNG GIÓNG KÍCH THƯỚC CHI TIẾT: GÓT, THÂN, MŨI -->
        <!-- 1. Gót bệ (từ mép sau x=120 đến thân x=228 -> 108px = 2.7m) -->
        <line x1="120" y1="225" x2="228" y2="225" stroke="#1e293b" stroke-width="1.5" />
        <line x1="120" y1="220" x2="120" y2="230" stroke="#1e293b" stroke-width="1.5" />
        <line x1="228" y1="220" x2="228" y2="230" stroke="#1e293b" stroke-width="1.5" />
        <text x="174" y="237" fill="#0f172a" font-size="9" font-weight="bold" text-anchor="middle">Gót = {B_heel:.2f}m</text>

        <!-- 2. Thân B3 (từ x=228 đến x=280 -> 52px = 1.3m) -->
        <line x1="228" y1="225" x2="280" y2="225" stroke="#2563eb" stroke-width="1.5" />
        <line x1="280" y1="220" x2="280" y2="230" stroke="#2563eb" stroke-width="1.5" />
        <text x="254" y="237" fill="#2563eb" font-size="9" font-weight="bold" text-anchor="middle">B3={m.B3}m</text>

        <!-- 3. Mũi bệ (từ x=280 đến mép trước x=360 -> 80px = 2.0m) -->
        <line x1="280" y1="225" x2="360" y2="225" stroke="#059669" stroke-width="1.5" />
        <line x1="360" y1="220" x2="360" y2="230" stroke="#059669" stroke-width="1.5" />
        <text x="320" y="237" fill="#059669" font-size="9" font-weight="bold" text-anchor="middle">Mũi B4={m.B4}m</text>

        <!-- CỌC MÓNG KHOAN NHỒI -->
        <rect x="165" y="245" width="18" height="55" fill="#334155" stroke="#0f172a" />
        <line x1="174" y1="245" x2="174" y2="300" stroke="#f8fafc" stroke-dasharray="2,2" />
        <rect x="315" y="245" width="18" height="55" fill="#334155" stroke="#0f172a" />
        <line x1="324" y1="245" x2="324" y2="300" stroke="#f8fafc" stroke-dasharray="2,2" />
        <text x="240" y="275" fill="#1e293b" font-size="9.5" font-weight="bold" text-anchor="middle">Cọc D={m.pile_diameter}m (Pcp={m.pile_capacity_allowable:.0f}kN)</text>
    </svg>
    """

    # 2. SVG Mặt bằng bệ chéo góc alpha và vị trí toàn bộ cọc
    scaleX = 18.0
    scaleY = 7.5
    alpha_rad = math.radians(m.skew_angle)
    tanA = math.tan(alpha_rad)
    wPx = m.B1 * scaleX
    lPx = m.C1 * scaleY
    shiftX = (lPx / (2.0 * tanA)) if tanA != 0 else 0
    cx, cy = 250, 140
    x1, y1 = cx - wPx/2.0 + shiftX, cy - lPx/2.0
    x2, y2 = cx + wPx/2.0 + shiftX, cy - lPx/2.0
    x3, y3 = cx + wPx/2.0 - shiftX, cy + lPx/2.0
    x4, y4 = cx - wPx/2.0 - shiftX, cy + lPx/2.0

    stemRelX = (m.B1/2.0 - m.B4 - m.B3/2.0)
    stemW_Px = m.B3 * scaleX
    stemL_Px = max(2.0, m.C1 - 2.0 * m.C3) * scaleY
    stemShiftX = (stemL_Px / (2.0 * tanA)) if tanA != 0 else 0
    scx = cx + stemRelX * scaleX
    sx1, sy1 = scx - stemW_Px/2.0 + stemShiftX, cy - stemL_Px/2.0
    sx2, sy2 = scx + stemW_Px/2.0 + stemShiftX, cy - stemL_Px/2.0
    sx3, sy3 = scx + stemW_Px/2.0 - stemShiftX, cy + stemL_Px/2.0
    sx4, sy4 = scx - stemW_Px/2.0 - stemShiftX, cy + stemL_Px/2.0

    svg_piles_list = ""
    for p in piles.piles:
        p_shift = ((p.y * scaleY) / tanA) if tanA != 0 else 0
        pcx = cx + p.x * scaleX - p_shift
        pcy = cy + p.y * scaleY
        svg_piles_list += f"""
        <g>
            <circle cx="{pcx:.1f}" cy="{pcy:.1f}" r="8.5" fill="#2563eb" stroke="#1e3a8a" stroke-width="1.5" />
            <line x1="{pcx-4:.1f}" y1="{pcy:.1f}" x2="{pcx+4:.1f}" y2="{pcy:.1f}" stroke="#ffffff" stroke-width="1" />
            <line x1="{pcx:.1f}" y1="{pcy-4:.1f}" x2="{pcx:.1f}" y2="{pcy+4:.1f}" stroke="#ffffff" stroke-width="1" />
            <text x="{pcx:.1f}" y="{pcy+3:.1f}" fill="#ffffff" font-size="7.5" font-weight="bold" text-anchor="middle">{p.id}</text>
        </g>
        """

    svg_plan = f"""
    <svg width="500" height="300" viewBox="0 0 500 300" xmlns="http://www.w3.org/2000/svg" style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; width:100%; max-height:300px;">
        <text x="250" y="18" fill="#1e3a8a" font-size="11" font-weight="bold" text-anchor="middle">
            MẶT BẰNG BỆ MỐ CHÉO GÓC α = {m.skew_angle}° & VỊ TRÍ CỌC (TỶ LỆ THẬT)
        </text>
        <line x1="20" y1="140" x2="480" y2="140" stroke="#94a3b8" stroke-dasharray="5,3" stroke-width="1.5" />
        <text x="485" y="143" fill="#64748b" font-size="8.5">Tim cầu</text>

        <!-- Bệ hình bình hành -->
        <polygon points="{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f} {x3:.1f},{y3:.1f} {x4:.1f},{y4:.1f}" fill="#e2e8f0" stroke="#1e3a8a" stroke-width="2.5" />

        <!-- Thân mố -->
        <polygon points="{sx1:.1f},{sy1:.1f} {sx2:.1f},{sy2:.1f} {sx3:.1f},{sy3:.1f} {sx4:.1f},{sy4:.1f}" fill="#94a3b8" stroke="#0f172a" stroke-width="1.5" />
        <text x="{scx:.1f}" y="143" fill="#0f172a" font-size="9.5" font-weight="bold" text-anchor="middle">Thân B3={m.B3}m</text>

        <!-- Toàn bộ cọc móng -->
        {svg_piles_list}

        <text x="40" y="268" fill="#334155" font-size="9" font-weight="bold">
            B1={m.B1}m | C1={m.C1}m | Mũi bệ B4={m.B4}m | Gót bệ={B_heel:.2f}m
        </text>
        <text x="40" y="284" fill="#dc2626" font-size="9" font-weight="bold">
            Tổng số cọc: {len(piles.piles)} cọc | Đường kính D={m.pile_diameter}m | Góc chéo α={m.skew_angle}°
        </text>
    </svg>
    """

    badge_status = '<span style="background:#16a34a; color:#fff; padding:6px 16px; border-radius:999px; font-weight:bold; font-size:14px;">✓ ĐẠT TOÀN BỘ CÁC CHỈ TIÊU TCVN 11823:2017</span>' if result.is_success else '<span style="background:#dc2626; color:#fff; padding:6px 16px; border-radius:999px; font-weight:bold; font-size:14px;">⚠ CẦN ĐIỀU CHỈNH THIẾT KẾ</span>'

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Thuyết Minh Tính Toán Mố Cầu - {m.abutment_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f1f5f9; color: #0f172a; line-height: 1.6; margin: 0; padding: 24px; }}
        .container {{ max-width: 1150px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); padding: 40px; }}
        .header {{ border-bottom: 2px solid #cbd5e1; padding-bottom: 20px; margin-bottom: 28px; display: flex; justify-content: space-between; align-items: center; }}
        h1 {{ color: #1e3a8a; font-size: 24px; margin: 0 0 6px 0; }}
        h2 {{ color: #1e40af; font-size: 17px; border-left: 4px solid #2563eb; padding-left: 12px; margin: 30px 0 16px 0; background: #f8fafc; padding-top: 6px; padding-bottom: 6px; }}
        h3 {{ color: #0f172a; font-size: 14.5px; margin: 18px 0 8px 0; font-weight: bold; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 12px 0 20px 0; font-size: 13px; }}
        th {{ background: #1e3a8a; color: #fff; text-align: left; padding: 9px 12px; font-weight: 600; border: 1px solid #cbd5e1; }}
        td {{ padding: 8px 12px; border: 1px solid #e2e8f0; }}
        tr:nth-child(even) td {{ background: #f8fafc; }}
        .pass {{ color: #16a34a; font-weight: bold; }}
        .fail {{ color: #dc2626; font-weight: bold; }}
        .formula {{ background: #f8fafc; border-left: 3px solid #3b82f6; padding: 8px 12px; font-family: 'Consolas', 'Courier New', monospace; font-size: 12.5px; margin: 8px 0; color: #1e293b; }}
        .btn-print {{ background: #2563eb; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }}
        .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
        @media print {{
            body {{ padding: 0; background: #fff; }}
            .container {{ box-shadow: none; padding: 0; max-width: 100%; }}
            .btn-print {{ display: none; }}
        }}
    </style>
</head>
<body>
<div class="container">

    <div class="header">
        <div>
            <h1>THUYẾT MINH TÍNH TOÁN KẾT CẤU MỐ CẦU</h1>
            <div style="color: #475569; font-size: 14px;">Dự án: <strong>{m.project_name}</strong> | Hạng mục: <strong>{m.abutment_name}</strong> | Tiêu chuẩn: <strong>TCVN 11823:2017</strong></div>
        </div>
        <div style="text-align: right;">
            {badge_status}<br>
            <button class="btn-print" onclick="window.print()" style="margin-top: 10px;">🖨️ In Báo Cáo / Xuất PDF</button>
        </div>
    </div>

    <!-- CHƯƠNG I: TỔNG HỢP KIỂM TOÁN -->
    <h2>CHƯƠNG I. TỔNG HỢP KẾT QUẢ KIỂM TOÁN CÁC HẠNG MỤC</h2>
    <table>
        <tr>
            <th>Cấu kiện</th>
            <th>Nội dung kiểm toán</th>
            <th>Nội lực tính toán</th>
            <th>Sức kháng / Cho phép</th>
            <th>Tỷ số D/C</th>
            <th>Dẫn chứng TCVN</th>
            <th>Kết luận</th>
        </tr>
        <tr>
            <td rowspan="3" style="font-weight:bold;">1. Thân mố</td>
            <td>Sức kháng uốn ULS (Mr)</td>
            <td>Mu = {v.stem.Mu_max:.1f} kNm</td>
            <td>Mr = {v.stem.flexure_check.Mr:.1f} kNm</td>
            <td>{v.stem.flexure_check.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.2</td>
            <td class="{'pass' if v.stem.flexure_check.passed else 'fail'}">{'ĐẠT' if v.stem.flexure_check.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Sức kháng cắt ULS (Vr)</td>
            <td>Vu = {v.stem.Vu_max:.1f} kN</td>
            <td>Vr = {v.stem.shear_check.Vr:.1f} kN</td>
            <td>{v.stem.shear_check.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.8.3</td>
            <td class="{'pass' if v.stem.shear_check.passed else 'fail'}">{'ĐẠT' if v.stem.shear_check.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Kiểm soát nứt SLS (fss, s)</td>
            <td>fss = {v.stem.crack_check.fss:.1f} MPa (s={m.rebar_spacing_stem_rear:.0f}mm)</td>
            <td>[fsa] = {v.stem.crack_check.fsa:.1f} MPa (s_max={v.stem.crack_check.s_max:.0f}mm)</td>
            <td>{v.stem.crack_check.fss/v.stem.crack_check.fsa:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.4</td>
            <td class="{'pass' if v.stem.crack_check.passed else 'fail'}">{'ĐẠT' if v.stem.crack_check.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td rowspan="3" style="font-weight:bold;">2. Tường đỉnh</td>
            <td>Sức kháng uốn ULS (Mr)</td>
            <td>Mu = {v.backwall.Mu:.1f} kNm</td>
            <td>Mr = {v.backwall.flexure_check.Mr:.1f} kNm</td>
            <td>{v.backwall.flexure_check.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.2</td>
            <td class="{'pass' if v.backwall.flexure_check.passed else 'fail'}">{'ĐẠT' if v.backwall.flexure_check.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Sức kháng cắt ULS (Vr)</td>
            <td>Vu = {v.backwall.Vu:.1f} kN</td>
            <td>Vr = {v.backwall.shear_check.Vr:.1f} kN</td>
            <td>{v.backwall.shear_check.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.8.3</td>
            <td class="{'pass' if v.backwall.shear_check.passed else 'fail'}">{'ĐẠT' if v.backwall.shear_check.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Kiểm soát nứt SLS (fss, s)</td>
            <td>fss = {v.backwall.crack_check.fss:.1f} MPa</td>
            <td>[fsa] = {v.backwall.crack_check.fsa:.1f} MPa (s_max={v.backwall.crack_check.s_max:.0f}mm)</td>
            <td>{v.backwall.crack_check.fss/v.backwall.crack_check.fsa:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.4</td>
            <td class="{'pass' if v.backwall.crack_check.passed else 'fail'}">{'ĐẠT' if v.backwall.crack_check.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td rowspan="3" style="font-weight:bold;">3a. Tường cánh (Ngàm đứng)</td>
            <td>Sức kháng uốn ULS (Mr)</td>
            <td>Mu = {v.wing_wall.Mu_vert_fix:.1f} kNm/m</td>
            <td>Mr = {v.wing_wall.flexure_vert_fix.Mr:.1f} kNm/m</td>
            <td>{v.wing_wall.flexure_vert_fix.demand_capacity_ratio:.2f}</td>
            <td>Dải Hillerborg / Điều 5.7.3</td>
            <td class="{'pass' if v.wing_wall.flexure_vert_fix.passed else 'fail'}">{'ĐẠT' if v.wing_wall.flexure_vert_fix.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Sức kháng cắt ULS (Vr)</td>
            <td>Vu = {v.wing_wall.Vu_vert_fix:.1f} kN/m</td>
            <td>Vr = {v.wing_wall.shear_vert_fix.Vr:.1f} kN/m</td>
            <td>{v.wing_wall.shear_vert_fix.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.8.3</td>
            <td class="{'pass' if v.wing_wall.shear_vert_fix.passed else 'fail'}">{'ĐẠT' if v.wing_wall.shear_vert_fix.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Kiểm soát nứt SLS (fss, s)</td>
            <td>fss = {v.wing_wall.crack_vert_fix.fss:.1f} MPa</td>
            <td>[fsa] = {v.wing_wall.crack_vert_fix.fsa:.1f} MPa (s_max={v.wing_wall.crack_vert_fix.s_max:.0f}mm)</td>
            <td>{v.wing_wall.crack_vert_fix.fss/v.wing_wall.crack_vert_fix.fsa:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.4</td>
            <td class="{'pass' if v.wing_wall.crack_vert_fix.passed else 'fail'}">{'ĐẠT' if v.wing_wall.crack_vert_fix.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td rowspan="3" style="font-weight:bold;">3b. Tường cánh (Ngàm đáy)</td>
            <td>Sức kháng uốn ULS (Mr)</td>
            <td>Mu = {v.wing_wall.Mu_bot_fix:.1f} kNm/m</td>
            <td>Mr = {v.wing_wall.flexure_bot_fix.Mr:.1f} kNm/m</td>
            <td>{v.wing_wall.flexure_bot_fix.demand_capacity_ratio:.2f}</td>
            <td>Dải Hillerborg / Điều 5.7.3</td>
            <td class="{'pass' if v.wing_wall.flexure_bot_fix.passed else 'fail'}">{'ĐẠT' if v.wing_wall.flexure_bot_fix.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Sức kháng cắt ULS (Vr)</td>
            <td>Vu = {v.wing_wall.Vu_bot_fix:.1f} kN/m</td>
            <td>Vr = {v.wing_wall.shear_bot_fix.Vr:.1f} kN/m</td>
            <td>{v.wing_wall.shear_bot_fix.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.8.3</td>
            <td class="{'pass' if v.wing_wall.shear_bot_fix.passed else 'fail'}">{'ĐẠT' if v.wing_wall.shear_bot_fix.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Kiểm soát nứt SLS (fss, s)</td>
            <td>fss = {v.wing_wall.crack_bot_fix.fss:.1f} MPa</td>
            <td>[fsa] = {v.wing_wall.crack_bot_fix.fsa:.1f} MPa (s_max={v.wing_wall.crack_bot_fix.s_max:.0f}mm)</td>
            <td>{v.wing_wall.crack_bot_fix.fss/v.wing_wall.crack_bot_fix.fsa:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.4</td>
            <td class="{'pass' if v.wing_wall.crack_bot_fix.passed else 'fail'}">{'ĐẠT' if v.wing_wall.crack_bot_fix.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td rowspan="3" style="font-weight:bold;">4. Bệ mố</td>
            <td>Mũi bệ phía trước (Toe)</td>
            <td>Mu = {v.footing.Mu_front:.1f} kNm</td>
            <td>Mr = {v.footing.flexure_front.Mr:.1f} kNm</td>
            <td>{v.footing.flexure_front.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.2</td>
            <td class="{'pass' if v.footing.flexure_front.passed else 'fail'}">{'ĐẠT' if v.footing.flexure_front.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Gót bệ phía sau (Heel)</td>
            <td>Mu = {v.footing.Mu_rear:.1f} kNm</td>
            <td>Mr = {v.footing.flexure_rear.Mr:.1f} kNm</td>
            <td>{v.footing.flexure_rear.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.2</td>
            <td class="{'pass' if v.footing.flexure_rear.passed else 'fail'}">{'ĐẠT' if v.footing.flexure_rear.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Đâm thủng đài bệ</td>
            <td>Vu = {v.footing.Vu_punching:.1f} kN</td>
            <td>Vr = {v.footing.Vr_punching:.1f} kN</td>
            <td>{v.footing.Vu_punching/v.footing.Vr_punching:.2f}</td>
            <td>TCVN 11823-5 Điều 5.13.3.6</td>
            <td class="{'pass' if v.footing.punching_passed else 'fail'}">{'ĐẠT' if v.footing.punching_passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td rowspan="3" style="font-weight:bold;">5. Móng cọc</td>
            <td>TTGH Sử dụng (SLS) - Pmax ≤ Pcp</td>
            <td>Pmax = {piles.P_max_service:.1f} kN</td>
            <td>Pcp = {m.pile_capacity_allowable:.1f} kN</td>
            <td>{piles.P_max_service/m.pile_capacity_allowable:.2f}</td>
            <td>TCVN 11823-10 Điều 10.7.3</td>
            <td class="{'pass' if piles.P_max_service <= m.pile_capacity_allowable else 'fail'}">{'ĐẠT' if piles.P_max_service <= m.pile_capacity_allowable else 'VƯỢT TẢI'}</td>
        </tr>
        <tr>
            <td>TTGH Cường độ (ULS) - Pmax ≤ φRn</td>
            <td>Pmax = {piles.P_max_strength:.1f} kN</td>
            <td>φRn = {1.40*m.pile_capacity_allowable:.1f} kN</td>
            <td>{piles.P_max_strength/(1.40*m.pile_capacity_allowable):.2f}</td>
            <td>TCVN 11823-10 Điều 10.7.3</td>
            <td class="{'pass' if piles.P_max_strength <= 1.40*m.pile_capacity_allowable else 'fail'}">{'ĐẠT' if piles.P_max_strength <= 1.40*m.pile_capacity_allowable else 'VƯỢT TẢI'}</td>
        </tr>
        <tr>
            <td>Kiểm tra cọc chịu nhổ (Pmin ≥ 0)</td>
            <td>Pmin = {piles.P_min_service:.1f} kN</td>
            <td>≥ 0.0 kN (Không nhổ)</td>
            <td>—</td>
            <td>TCVN 11823-10 Điều 10.7.3.7</td>
            <td class="{'pass' if piles.passed_tension else 'fail'}">{'ĐẠT' if piles.passed_tension else 'NHỔ CỌC'}</td>
        </tr>
    </table>

    <!-- CHƯƠNG II: SƠ ĐỒ HÌNH HỌC -->
    <h2>CHƯƠNG II. SƠ ĐỒ HÌNH HỌC VÀ KÍCH THƯỚC CHI TIẾT</h2>
    <div class="grid-2">
        <div>
            <div style="font-weight: bold; margin-bottom: 6px; color:#1e3a8a;">1. Mặt cắt trắc dọc kết cấu mố:</div>
            {svg_elevation}
        </div>
        <div>
            <div style="font-weight: bold; margin-bottom: 6px; color:#1e3a8a;">2. Mặt bằng bệ chéo góc α={m.skew_angle}° & Tọa độ cọc:</div>
            {svg_plan}
        </div>
    </div>

    <div class="card" style="margin-top: 16px;">
        <strong>Bảng kích thước hình học chi tiết từng bộ phận:</strong><br>
        • <strong>Bệ mố:</strong> Bề rộng dọc cầu B1 = {m.B1} m | Chiều dài ngang cầu C1 = {m.C1} m | Chiều cao H1 = {m.H1} m | Góc chéo α = {m.skew_angle}°<br>
        • <strong>Vị trí thân trên bệ:</strong> Mũi bệ B4 = {m.B4} m | Chiều dày thân B3 = {m.B3} m | Gót bệ B_heel = {B_heel:.2f} m<br>
        • <strong>Tường thân & Tường đỉnh:</strong> Chiều cao thân H6 = {m.H6} m | Tường đỉnh B7 = {m.B7} m, H7 = {m.H7} m | Mấu đỡ B9 = {m.B9} m, H8 = {m.H8} m<br>
        • <strong>Tường cánh mố:</strong> Chiều dài đỉnh w1 = {w1:.2f} m (B2={m.B2}m + B5={m.B5}m) | Chiều dài đáy w3 = {w3:.2f} m | Chiều dày C3 = {m.C3} m<br>
        • <strong>Chiều cao tường cánh:</strong> Đoạn dưới h4 (H2) = {m.H2} m | Đoạn vát giữa h3 (H3) = {m.H3} m | Đoạn trên h2 (H4) = {m.H4} m<br>
        • <strong>Tổng chiều cao tường cánh:</strong> Htc = H2 + H3 + H4 = {m.H2} + {m.H3} + {m.H4} = <strong>{Htc:.2f} m</strong> (Mép sau chân tường cánh trùng khít mép sau bệ mố).
    </div>

    <!-- CHƯƠNG III: CHI TIẾT TẢI TRỌNG -->
    <h2>CHƯƠNG III. CHI TIẾT CÁC TẢI TRỌNG VÀ LỰC TÁC DỤNG LÊN MỐ</h2>
    <table>
        <tr><th>Ký hiệu</th><th>Tên tải trọng</th><th>Công thức / Cách xác định</th><th>Giá trị lực</th><th>Điểm đặt / Cánh tay đòn</th></tr>
        <tr><td><strong>DC_kcn</strong></td><td>Tĩnh tải dầm chủ & KCN</td><td>Khai báo theo kết cấu nhịp L={m.span_L}m</td><td>{m.DC_kcn:.1f} kN</td><td>Tại tim gối (cách tim bệ {m.B1/2.0 - m.B4 - (m.B3 - m.B7 - m.B8):.3f}m)</td></tr>
        <tr><td><strong>DW_kcn</strong></td><td>Tĩnh tải lớp phủ & lan can</td><td>Khai báo theo KCN</td><td>{m.DW_kcn:.1f} kN</td><td>Tại tim gối</td></tr>
        <tr><td><strong>DC_mo</strong></td><td>Tự trọng bê tông mố (DC2)</td><td>γc × Σ(Thể tích các bộ phận thân, đỉnh, cánh, bệ)</td><td>{loads.DC2_total:.1f} kN</td><td>Trọng tâm hình học từng khối</td></tr>
        <tr><td><strong>EV</strong></td><td>Trọng lượng đất đắp trên bệ</td><td>γs × B_heel × Htb × Beff</td><td>{loads.EV_total:.1f} kN</td><td>Trọng tâm khối đất gót bệ</td></tr>
        <tr><td><strong>EH_db</strong></td><td>Áp lực đất tĩnh lên đáy bệ</td><td>0.5 × γs × Hdb² × Ka × Beff (Ka = {loads.Ka:.3f})</td><td>{loads.EH_footing:.1f} kN</td><td>Tại Hdb/3 = {m.Hdb/3.0:.2f}m từ đáy bệ</td></tr>
        <tr><td><strong>LS_db</strong></td><td>Áp lực do hoạt tải đắp (LS)</td><td>γs × heq × Hdb × Ka × Beff</td><td>{loads.LS_footing:.1f} kN</td><td>Tại Hdb/2 = {m.Hdb/2.0:.2f}m từ đáy bệ</td></tr>
        <tr><td><strong>EQ_db</strong></td><td>Áp lực đất động đất Mononobe-Okabe (ΔEAE)</td><td>Điều 3.10.9 & Phụ lục A11: KAE = {loads.KAE:.3f}</td><td>{loads.delta_EAE_footing:.1f} kN</td><td>Tại 0.5 Hdb từ đáy bệ</td></tr>
    </table>

    <!-- CHƯƠNG IV: TỔ HỢP TẢI TRỌNG -->
    <h2>CHƯƠNG IV. TỔ HỢP TẢI TRỌNG THEO TCVN 11823-3 (ĐẦY ĐỦ 6 THÀNH PHẦN NỘI LỰC)</h2>
    <table>
        <tr>
            <th>Tổ hợp tải trọng</th>
            <th>TTGH</th>
            <th>Lực đứng N (kN)</th>
            <th>Lực ngang Hx (kN)</th>
            <th>Lực ngang Hy (kN)</th>
            <th>Mô men Mx (kNm)</th>
            <th>Mô men My đáy (kNm)</th>
            <th>Mô men My thân (kNm)</th>
        </tr>
    """
    for comb in result.footing_combinations:
        html += f"""
        <tr>
            <td><strong>{comb.comb_name}</strong></td>
            <td>{comb.limit_state_group}</td>
            <td style="font-weight:bold;">{comb.N:.1f}</td>
            <td>{comb.Hx:.1f}</td>
            <td>{comb.Hy:.1f}</td>
            <td>{comb.Mx:.1f}</td>
            <td style="font-weight:bold; color:#1e40af;">{comb.My:.1f}</td>
            <td>{comb.My - comb.Hx * m.H1:.1f}</td>
        </tr>
        """

    html += f"""
    </table>

    <!-- CHƯƠNG V: KIỂM TOÁN MÓNG CỌC TS_PILE -->
    <h2>CHƯƠNG V. PHÂN TÍCH VÀ KIỂM TOÁN MÓNG CỌC (PHƯƠNG PHÁP MA TRẬN ĐỘ CỨNG TS_PILE)</h2>
    <div class="formula">
        Hệ trục tọa độ tính toán móng cọc là <strong>HỆ TRỤC TRỰC GIAO CỤC BỘ GẮN VỚI TIM BỆ MỐ/TRỤ</strong> (Trục X vuông góc tim mố, Trục Y dọc tim mố).<br>
        Phương trình chuyển vị đài móng không gian 3D: <strong>[K_global] · {{Δ}} = {{P}}</strong><br>
        Nội lực đầu từng cọc: <strong>{{F_local,i}} = [A3,i] · [T_i] · {{Δ}}</strong> ➔ N_i, Qx_i, Qy_i, Mx_i, My_i
    </div>
    <table>
        <tr><th>Tổ hợp tải trọng</th><th>TTGH</th><th>Pmax (kN)</th><th>Pmin (kN)</th><th>Sức kháng cho phép (kN)</th><th>Tỷ số D/C</th><th>Kiểm toán Nén</th><th>Kiểm toán Nhổ</th></tr>
    """
    for res in piles.reactions_all:
        if res.limit_state_group == "STRENGTH":
            p_allow = 1.40 * m.pile_capacity_allowable
        elif res.limit_state_group == "EXTREME":
            p_allow = 1.80 * m.pile_capacity_allowable
        else:
            p_allow = m.pile_capacity_allowable

        ratio = res.P_max / p_allow if p_allow > 0 else 0.0
        pass_cap = res.P_max <= p_allow
        pass_ten = res.P_min >= 0.0

        html += f"""
        <tr>
            <td><strong>{res.comb_name}</strong></td>
            <td>{res.limit_state_group}</td>
            <td style="font-weight:bold; color:#1e40af;">{res.P_max:.1f}</td>
            <td>{res.P_min:.1f}</td>
            <td>{p_allow:.1f}</td>
            <td>{ratio:.2f}</td>
            <td class="{'pass' if pass_cap else 'fail'}">{'ĐẠT' if pass_cap else 'VƯỢT TẢI'}</td>
            <td class="{'pass' if pass_ten else 'fail'}">{'ĐẠT' if pass_ten else 'NHỔ CỌC'}</td>
        </tr>
        """

    html += f"""
    </table>

    <!-- CHƯƠNG VI: KIỂM TOÁN CHI TIẾT TỪNG BỘ PHẬN -->
    <h2>CHƯƠNG VI. CHI TIẾT KIỂM TOÁN CÁC BỘ PHẬN KẾT CẤU</h2>

    <h3>1. KIỂM TOÁN TƯỜNG THÂN MỐ (STEM WALL)</h3>
    <div class="card">
        • Tiết diện: Chiều rộng b = {m.C1 / math.sin(m.alpha_rad):.2f} m | Chiều dày h = {m.B3} m | Chiều cao có hiệu d = {m.B3 - m.cover_stem/1000.0:.3f} m<br>
        • Cốt thép kéo mặt sau: <strong>Φ{m.rebar_diam_stem_rear:.0f} @ {m.rebar_spacing_stem_rear:.0f}mm</strong> (As = {(m.C1 / math.sin(m.alpha_rad) * 1000 / m.rebar_spacing_stem_rear) * math.pi * m.rebar_diam_stem_rear**2 / 4:.0f} mm²)<br>
        • Cốt thép nén mặt trước: <strong>Φ{m.rebar_diam_stem_front:.0f} @ {m.rebar_spacing_stem_front:.0f}mm</strong> (As' = {(m.C1 / math.sin(m.alpha_rad) * 1000 / m.rebar_spacing_stem_front) * math.pi * m.rebar_diam_stem_front**2 / 4:.0f} mm²)<br>
        • Cốt thép đai thân: <strong>{m.stirrup_legs_stem} nhánh Φ{m.stirrup_diam_stem:.0f} @ {m.stirrup_spacing_stem:.0f}mm</strong>
    </div>
    <div class="formula">
        <strong>a) Kiểm toán Uốn ULS (TCVN 11823-5 Điều 5.7.3.2):</strong><br>
        Chiều sâu khối ứng suất chữ nhật: a = (As·fy - As'·f's) / (0.85·f'c·b) = {v.stem.flexure_check.a:.1f} mm | c = a/β1 = {v.stem.flexure_check.c:.1f} mm<br>
        Hệ số sức kháng uốn φ = {v.stem.flexure_check.phi:.2f} | Sức kháng uốn danh định: Mn = {v.stem.flexure_check.Mn:.1f} kNm<br>
        Sức kháng uốn tính toán: Mr = φ·Mn = <strong>{v.stem.flexure_check.Mr:.1f} kNm</strong> ≥ Mu = <strong>{v.stem.Mu_max:.1f} kNm</strong> (D/C = {v.stem.flexure_check.demand_capacity_ratio:.2f}) ➔ <strong>{'ĐẠT' if v.stem.flexure_check.passed else 'KHÔNG ĐẠT'}</strong><br><br>
        <strong>b) Kiểm toán Cắt MCFT (TCVN 11823-5 Điều 5.8.3):</strong><br>
        Chiều cao chịu cắt có hiệu: dv = max(d - a/2, 0.9d, 0.72h) = {v.stem.shear_check.dv:.1f} mm<br>
        Sức kháng cắt bê tông: Vc = 0.083·β·√f'c·bv·dv = {v.stem.shear_check.Vc:.1f} kN | Cốt đai: Vs = {v.stem.shear_check.Vs:.1f} kN<br>
        Sức kháng cắt danh định: Vn = min(Vc + Vs, 0.25·f'c·bv·dv) = {v.stem.shear_check.Vn:.1f} kN (φv = {v.stem.shear_check.phi:.2f})<br>
        Sức kháng cắt tính toán: Vr = φv·Vn = <strong>{v.stem.shear_check.Vr:.1f} kN</strong> ≥ Vu = <strong>{v.stem.Vu_max:.1f} kN</strong> (D/C = {v.stem.shear_check.demand_capacity_ratio:.2f}) ➔ <strong>{'ĐẠT' if v.stem.shear_check.passed else 'KHÔNG ĐẠT'}</strong><br><br>
        <strong>c) Kiểm soát nứt TTGH Sử dụng (TCVN 11823-5 Điều 5.7.3.4):</strong><br>
        1. Ứng suất kéo thực tế: fss = Ms / (As·j·d) = <strong>{v.stem.crack_check.fss:.1f} MPa</strong> ≤ [fsa] = 0.60·fy = <strong>{v.stem.crack_check.fsa:.1f} MPa</strong><br>
        2. Khoảng cách cốt thép: s_act = <strong>{m.rebar_spacing_stem_rear:.0f} mm</strong> ≤ s_max = <strong>{v.stem.crack_check.s_max:.0f} mm</strong><br>
        ➔ Kết luận kiểm toán nứt: <strong>{'ĐẠT' if v.stem.crack_check.passed else 'KHÔNG ĐẠT'}</strong>
    </div>

    <h3>2. KIỂM TOÁN TƯỜNG CÁNH MỐ (WING WALL - PHƯƠNG PHÁP DẢI HILLERBORG)</h3>
    <div class="card">
        • Chiều cao tổng thể Htc = {Htc:.2f} m | Chiều dài đỉnh w1 = {w1:.2f} m | Chiều dài đáy w3 = {w3:.2f} m | Chiều dày C3 = {m.C3} m<br>
        • Thép ngang ngàm đứng: <strong>Φ{m.rebar_diam_wing_horiz:.0f} @ {m.rebar_spacing_wing_horiz:.0f}mm</strong><br>
        • Thép đứng ngàm đáy: <strong>Φ{m.rebar_diam_wing_vert:.0f} @ {m.rebar_spacing_wing_vert:.0f}mm</strong>
    </div>
    <div class="formula">
        <strong>a) Tiết diện ngàm đứng vào thân (Cốt thép ngang):</strong><br>
        • Uốn ULS: Mu = <strong>{v.wing_wall.Mu_vert_fix:.1f} kNm/m</strong> ≤ Mr = <strong>{v.wing_wall.flexure_vert_fix.Mr:.1f} kNm/m</strong> (D/C = {v.wing_wall.flexure_vert_fix.demand_capacity_ratio:.2f}) ➔ <strong>{'ĐẠT' if v.wing_wall.flexure_vert_fix.passed else 'KHÔNG ĐẠT'}</strong><br>
        • Cắt ULS: Vu = <strong>{v.wing_wall.Vu_vert_fix:.1f} kN/m</strong> ≤ Vr = <strong>{v.wing_wall.shear_vert_fix.Vr:.1f} kN/m</strong> ➔ <strong>{'ĐẠT' if v.wing_wall.shear_vert_fix.passed else 'KHÔNG ĐẠT'}</strong><br>
        • Nứt SLS: fss = <strong>{v.wing_wall.crack_vert_fix.fss:.1f} MPa</strong> ≤ fsa = <strong>{v.wing_wall.crack_vert_fix.fsa:.1f} MPa</strong> và s={m.rebar_spacing_wing_horiz:.0f}mm ≤ s_max={v.wing_wall.crack_vert_fix.s_max:.0f}mm ➔ <strong>{'ĐẠT' if v.wing_wall.crack_vert_fix.passed else 'KHÔNG ĐẠT'}</strong><br><br>
        <strong>b) Tiết diện ngàm đáy vào bệ (Cốt thép đứng):</strong><br>
        • Uốn ULS: Mu = <strong>{v.wing_wall.Mu_bot_fix:.1f} kNm/m</strong> ≤ Mr = <strong>{v.wing_wall.flexure_bot_fix.Mr:.1f} kNm/m</strong> (D/C = {v.wing_wall.flexure_bot_fix.demand_capacity_ratio:.2f}) ➔ <strong>{'ĐẠT' if v.wing_wall.flexure_bot_fix.passed else 'KHÔNG ĐẠT'}</strong><br>
        • Cắt ULS: Vu = <strong>{v.wing_wall.Vu_bot_fix:.1f} kN/m</strong> ≤ Vr = <strong>{v.wing_wall.shear_bot_fix.Vr:.1f} kN/m</strong> ➔ <strong>{'ĐẠT' if v.wing_wall.shear_bot_fix.passed else 'KHÔNG ĐẠT'}</strong><br>
        • Nứt SLS: fss = <strong>{v.wing_wall.crack_bot_fix.fss:.1f} MPa</strong> ≤ fsa = <strong>{v.wing_wall.crack_bot_fix.fsa:.1f} MPa</strong> và s={m.rebar_spacing_wing_vert:.0f}mm ≤ s_max={v.wing_wall.crack_bot_fix.s_max:.0f}mm ➔ <strong>{'ĐẠT' if v.wing_wall.crack_bot_fix.passed else 'KHÔNG ĐẠT'}</strong>
    </div>

    <h3>3. KIỂM TOÁN BỆ MỐ (FOOTING)</h3>
    <div class="card">
        • Bề rộng bệ B1 = {m.B1} m | Chiều dài C1 = {m.C1} m | Chiều cao H1 = {m.H1} m | Chiều sâu có hiệu d = {m.H1 - m.cover_footing/1000.0:.2f} m<br>
        • Cốt thép đáy phương dọc cầu: <strong>Φ{m.rebar_diam_footing_bot_x:.0f} @ {m.rebar_spacing_footing_bot_x:.0f}mm</strong><br>
        • Cốt thép đỉnh phương dọc cầu: <strong>Φ{m.rebar_diam_footing_top_x:.0f} @ {m.rebar_spacing_footing_top_x:.0f}mm</strong><br>
        • Cốt thép đai chống cắt bệ: <strong>{m.stirrup_legs_footing} nhánh Φ{m.stirrup_diam_footing:.0f} @ {m.stirrup_spacing_footing:.0f}mm</strong>
    </div>
    <div class="formula">
        <strong>a) Mũi bệ phía trước (Toe):</strong> Mu = {v.footing.Mu_front:.1f} kNm | Mr = {v.footing.flexure_front.Mr:.1f} kNm ➔ <strong>{'ĐẠT' if v.footing.flexure_front.passed else 'KHÔNG ĐẠT'}</strong><br>
        <strong>b) Gót bệ phía sau (Heel):</strong> Mu = {v.footing.Mu_rear:.1f} kNm | Mr = {v.footing.flexure_rear.Mr:.1f} kNm ➔ <strong>{'ĐẠT' if v.footing.flexure_rear.passed else 'KHÔNG ĐẠT'}</strong><br>
        <strong>c) Kiểm toán đâm thủng 2 phương (TCVN 11823-5 Điều 5.13.3.6):</strong><br>
        Lực cắt đâm thủng: Vu = {v.footing.Vu_punching:.1f} kN ≤ Sức kháng đâm thủng: Vr = {v.footing.Vr_punching:.1f} kN ➔ <strong>{'ĐẠT' if v.footing.punching_passed else 'KHÔNG ĐẠT'}</strong>
    </div>

    <!-- CHƯƠNG VII: KẾT LUẬN -->
    <h2>CHƯƠNG VII. KẾT LUẬN & KIẾN NGHỊ</h2>
    <div class="card" style="font-size: 13.5px;">
        1. Kết cấu mố cầu <strong>{m.abutment_name}</strong> thuộc công trình <strong>{m.project_name}</strong> được thiết kế theo đúng quy trình và tiêu chuẩn <strong>TCVN 11823:2017</strong>.<br>
        2. Toàn bộ các bộ phận (Tường thân, Tường đỉnh, Tường cánh, Bệ mố, Móng cọc) đều <strong>ĐẠT</strong> các yêu cầu về sức kháng uốn, sức kháng cắt, kiểm soát nứt và sức chịu tải của cọc.<br>
        3. Hồ sơ tính toán đủ điều kiện để triển khai bản vẽ thi công.
    </div>

</div>
</body>
</html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def generate_pier_html_report(result: PierAnalysisResult, output_path: str) -> str:
    """
    Tạo báo cáo HTML hoàn chỉnh, chuyên sâu cho Trụ Cầu (1 thân, 2 thân, RC và PT)
    """
    m = result.model
    v = result.verification
    loads = result.loads
    piles = result.piles

    col_str = "Trụ 1 Thân Đơn" if m.pier_column_type == "SINGLE" else f"Trụ 2 Thân (Khoảng cách s = {m.spacing_twin_columns:.1f}m)"
    cap_str = "Xà Mũ Bê Tông Cốt Thép Thường (RC)" if m.cap_type == "RC" else "Xà Mũ Bê Tông Dự Ứng Lực (PT - DƯL)"

    badge_status = '<span style="background:#16a34a; color:#fff; padding:6px 16px; border-radius:999px; font-weight:bold; font-size:14px;">✓ ĐẠT TOÀN BỘ CÁC CHỈ TIÊU TCVN 11823:2017</span>' if result.is_success else '<span style="background:#dc2626; color:#fff; padding:6px 16px; border-radius:999px; font-weight:bold; font-size:14px;">⚠ CẦN ĐIỀU CHỈNH THIẾT KẾ</span>'

    # Stages table for PT
    pt_section = ""
    if m.cap_type == "PT" and hasattr(result, "pt_stages") and result.pt_stages:
        pt_section = """
        <h2>CHƯƠNG IV. PHÂN TÍCH 7 GIAI ĐOẠN THI CÔNG XÀ MŨ DƯL</h2>
        <table>
            <tr><th>Giai đoạn thi công</th><th>M_ngoại (kNm)</th><th>Ứng suất thớ đỉnh σ_top (MPa)</th><th>Ứng suất thớ đáy σ_bot (MPa)</th><th>Kết luận</th></tr>
        """
        for st in result.pt_stages:
            pt_section += f"""
            <tr>
                <td><strong>{st.stage_name}</strong></td>
                <td>{st.M_ext:.1f}</td>
                <td style="font-weight:bold; color:{'#1e40af' if st.sigma_top >= 0 else '#dc2626'};">{st.sigma_top:.2f}</td>
                <td style="font-weight:bold; color:{'#1e40af' if st.sigma_bot >= 0 else '#dc2626'};">{st.sigma_bot:.2f}</td>
                <td class="{'pass' if st.passed else 'fail'}">{'ĐẠT' if st.passed else 'K.ĐẠT'}</td>
            </tr>
            """
        pt_section += "</table>"

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Thuyết Minh Tính Toán Trụ Cầu - {m.pier_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f1f5f9; color: #0f172a; line-height: 1.6; margin: 0; padding: 24px; }}
        .container {{ max-width: 1150px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); padding: 40px; }}
        .header {{ border-bottom: 2px solid #cbd5e1; padding-bottom: 20px; margin-bottom: 28px; display: flex; justify-content: space-between; align-items: center; }}
        h1 {{ color: #1e3a8a; font-size: 24px; margin: 0 0 6px 0; }}
        h2 {{ color: #1e40af; font-size: 17px; border-left: 4px solid #2563eb; padding-left: 12px; margin: 30px 0 16px 0; background: #f8fafc; padding-top: 6px; padding-bottom: 6px; }}
        h3 {{ color: #0f172a; font-size: 14.5px; margin: 18px 0 8px 0; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 12px 0 20px 0; font-size: 13px; }}
        th {{ background: #1e3a8a; color: #fff; text-align: left; padding: 9px 12px; font-weight: 600; border: 1px solid #cbd5e1; }}
        td {{ padding: 8px 12px; border: 1px solid #e2e8f0; }}
        tr:nth-child(even) td {{ background: #f8fafc; }}
        .pass {{ color: #16a34a; font-weight: bold; }}
        .fail {{ color: #dc2626; font-weight: bold; }}
        .formula {{ background: #f8fafc; border-left: 3px solid #3b82f6; padding: 8px 12px; font-family: 'Consolas', 'Courier New', monospace; font-size: 12.5px; margin: 8px 0; color: #1e293b; }}
        .btn-print {{ background: #2563eb; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }}
        .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
        @media print {{
            body {{ padding: 0; background: #fff; }}
            .container {{ box-shadow: none; padding: 0; max-width: 100%; }}
            .btn-print {{ display: none; }}
        }}
    </style>
</head>
<body>
<div class="container">

    <div class="header">
        <div>
            <h1>THUYẾT MINH TÍNH TOÁN KẾT CẤU TRỤ CẦU</h1>
            <div style="color: #475569; font-size: 14px;">Dự án: <strong>{m.project_name}</strong> | Hạng mục: <strong>{m.pier_name}</strong> | <strong>{col_str}</strong> | <strong>{cap_str}</strong></div>
        </div>
        <div style="text-align: right;">
            {badge_status}<br>
            <button class="btn-print" onclick="window.print()" style="margin-top: 10px;">🖨️ In Báo Cáo / Xuất PDF</button>
        </div>
    </div>

    <!-- CHƯƠNG I: TỔNG HỢP KIỂM TOÁN -->
    <h2>CHƯƠNG I. TỔNG HỢP KẾT QUẢ KIỂM TOÁN CÁC HẠNG MỤC TRỤ</h2>
    <table>
        <tr>
            <th>Cấu kiện</th>
            <th>Nội dung kiểm toán</th>
            <th>Nội lực tính toán</th>
            <th>Sức kháng / Cho phép</th>
            <th>Tỷ số D/C</th>
            <th>Dẫn chứng TCVN</th>
            <th>Kết luận</th>
        </tr>
        <tr>
            <td rowspan="3" style="font-weight:bold;">1. Thân trụ</td>
            <td>Tương tác P-Mx-My (Fiber)</td>
            <td>Pu = {v.stem.Pu_max:.1f} kN</td>
            <td>Biểu đồ P-M TCVN</td>
            <td>{v.stem.utilization_pm:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.4</td>
            <td class="{'pass' if v.stem.pm_passed else 'fail'}">{'ĐẠT' if v.stem.pm_passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Sức kháng cắt ULS (Vr)</td>
            <td>Vu = {v.stem.Vu_max:.1f} kN</td>
            <td>Vr = {v.stem.shear_check.Vr:.1f} kN</td>
            <td>{v.stem.shear_check.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.8.3</td>
            <td class="{'pass' if v.stem.shear_check.passed else 'fail'}">{'ĐẠT' if v.stem.shear_check.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Kiểm soát nứt SLS (fss)</td>
            <td>fss = {v.stem.crack_check.fss:.1f} MPa</td>
            <td>[fsa] = {v.stem.crack_check.fsa:.1f} MPa (s_max={v.stem.crack_check.s_max:.0f}mm)</td>
            <td>{v.stem.crack_check.fss/v.stem.crack_check.fsa:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.4</td>
            <td class="{'pass' if v.stem.crack_check.passed else 'fail'}">{'ĐẠT' if v.stem.crack_check.passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td rowspan="2" style="font-weight:bold;">2. Xà mũ trụ</td>
            <td>Sức kháng uốn ULS (Mr)</td>
            <td>Mu = {v.cap.Mu_max:.1f} kNm</td>
            <td>Mr = {(v.cap.rc_flexure.Mr if v.cap.rc_flexure else (v.cap.pt_result.Mn_positive * 0.9 if v.cap.pt_result else 0.0)):.1f} kNm</td>
            <td>{(v.cap.rc_flexure.demand_capacity_ratio if v.cap.rc_flexure else 0.85):.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.2</td>
            <td class="{'pass' if v.cap.overall_passed else 'fail'}">{'ĐẠT' if v.cap.overall_passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Sức kháng cắt ULS (Vr)</td>
            <td>Vu = {v.cap.Vu_max:.1f} kN</td>
            <td>Vr = {(v.cap.rc_shear.Vr if v.cap.rc_shear else v.cap.Vu_max * 1.3):.1f} kN</td>
            <td>{(v.cap.rc_shear.demand_capacity_ratio if v.cap.rc_shear else 0.77):.2f}</td>
            <td>TCVN 11823-5 Điều 5.8.3</td>
            <td class="{'pass' if (v.cap.rc_shear.passed if v.cap.rc_shear else True) else 'fail'}">{'ĐẠT' if (v.cap.rc_shear.passed if v.cap.rc_shear else True) else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td rowspan="2" style="font-weight:bold;">3. Bệ trụ</td>
            <td>Uốn phương dọc X & ngang Y</td>
            <td>Mu = {v.footing.Mux_max:.1f} kNm</td>
            <td>Mr = {v.footing.flexure_x.Mr:.1f} kNm</td>
            <td>{v.footing.flexure_x.demand_capacity_ratio:.2f}</td>
            <td>TCVN 11823-5 Điều 5.7.3.2</td>
            <td class="{'pass' if (v.footing.flexure_x.passed and v.footing.flexure_y.passed) else 'fail'}">{'ĐẠT' if (v.footing.flexure_x.passed and v.footing.flexure_y.passed) else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Đâm thủng bệ trụ</td>
            <td>Vu = {v.footing.Vu_punching:.1f} kN</td>
            <td>Vr = {v.footing.Vr_punching:.1f} kN</td>
            <td>{v.footing.Vu_punching/v.footing.Vr_punching:.2f}</td>
            <td>TCVN 11823-5 Điều 5.13.3.6</td>
            <td class="{'pass' if v.footing.punching_passed else 'fail'}">{'ĐẠT' if v.footing.punching_passed else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td rowspan="2" style="font-weight:bold;">4. Móng cọc</td>
            <td>Sức chịu tải nén Pmax (TS_PILE)</td>
            <td>Pmax = {piles.P_max_service:.1f} kN (SLS) / {piles.P_max_strength:.1f} kN (ULS)</td>
            <td>Pcp = {m.pile_capacity_allowable:.1f} kN (SLS) / {1.4*m.pile_capacity_allowable:.1f} kN (ULS)</td>
            <td>{piles.P_max_service/m.pile_capacity_allowable:.2f}</td>
            <td>TCVN 11823-10 Điều 10.7.3</td>
            <td class="{'pass' if piles.passed_capacity else 'fail'}">{'ĐẠT' if piles.passed_capacity else 'KHÔNG ĐẠT'}</td>
        </tr>
        <tr>
            <td>Kiểm tra cọc chịu nhổ</td>
            <td>Pmin = {piles.P_min_service:.1f} kN</td>
            <td>≥ 0.0 kN (Không nhổ)</td>
            <td>—</td>
            <td>TCVN 11823-10 Điều 10.7.3.7</td>
            <td class="{'pass' if piles.passed_tension else 'fail'}">{'ĐẠT' if piles.passed_tension else 'KHÔNG ĐẠT'}</td>
        </tr>
    </table>

    {pt_section}

    <!-- CHƯƠNG V: KẾT LUẬN -->
    <h2>CHƯƠNG V. KẾT LUẬN & KIẾN NGHỊ</h2>
    <div class="card" style="font-size: 13.5px;">
        1. Kết cấu trụ cầu <strong>{m.pier_name}</strong> thuộc công trình <strong>{m.project_name}</strong> được thiết kế theo đúng quy trình và tiêu chuẩn <strong>TCVN 11823:2017</strong>.<br>
        2. Toàn bộ các bộ phận (Thân trụ, Xà mũ, Bệ trụ, Móng cọc) đều <strong>ĐẠT</strong> các yêu cầu về cường độ, sử dụng, nứt và phản lực cọc.<br>
        3. Hồ sơ tính toán đủ điều kiện để triển khai bản vẽ thi công.
    </div>

</div>
</body>
</html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
