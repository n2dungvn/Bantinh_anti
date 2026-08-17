"""
Module: ui.app
FastAPI Web Application phục vụ giao diện người dùng tính toán Mố và Trụ Cầu.
Hỗ trợ tương tác thời gian thực, nhập liệu trực quan, vẽ biểu đồ P-M và tải báo cáo DOCX/HTML/PDF.
"""
import os
import json
import dataclasses
import urllib.parse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..abutment import AbutmentModel, AbutmentSolver
from ..pier import PierModel, PierSolver
from ..reporting import (
    generate_abutment_docx_report, generate_pier_docx_report,
    generate_abutment_html_report, generate_pier_html_report,
    generate_abutment_pdf_report, generate_pier_pdf_report
)

app = FastAPI(title="Phần mềm Tính toán Mố / Trụ Cầu TCVN 11823-2017", version="1.0.0")

OUTPUT_DIR = os.path.join(os.getcwd(), "output_reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Giao diện web chính"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Giao diện web đang khởi tạo...</h1>"


@app.get("/api/presets/{preset_name}")
async def get_preset(preset_name: str):
    """Lấy dữ liệu mẫu dự án JSON"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    file_path = os.path.join(data_dir, f"{preset_name}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Preset not found")


@app.post("/api/calculate/abutment")
async def calculate_abutment(data: Dict[str, Any]):
    """Tính toán Mố cầu từ dữ liệu form"""
    try:
        from ..abutment.model import AbutmentPileRow
        model_fields = {f.name for f in dataclasses.fields(AbutmentModel)}
        filtered_data = {k: v for k, v in data.items() if k in model_fields}
        if "pile_rows" in filtered_data and isinstance(filtered_data["pile_rows"], list):
            filtered_data["pile_rows"] = [
                AbutmentPileRow(**r) if isinstance(r, dict) else r for r in filtered_data["pile_rows"]
            ]
        model = AbutmentModel(**filtered_data)
        solver = AbutmentSolver(model)
        result = solver.solve()

        # Tạo file báo cáo
        docx_path = os.path.join(OUTPUT_DIR, f"{model.abutment_name}_Bao_cao.docx")
        html_path = os.path.join(OUTPUT_DIR, f"{model.abutment_name}_Bao_cao.html")
        pdf_path = os.path.join(OUTPUT_DIR, f"{model.abutment_name}_Bao_cao.pdf")

        generate_abutment_docx_report(result, docx_path)
        generate_abutment_html_report(result, html_path)
        generate_abutment_pdf_report(result, pdf_path)

        # Trả về kết quả JSON rút gọn cho UI
        v = result.verification
        p = result.piles
        
        cap_info = None
        if p.capacity_result:
            cr = p.capacity_result
            cap_info = {
                "qshaft_nominal": cr.qshaft_nominal_kn,
                "qtip_nominal": cr.qtip_nominal_kn,
                "Rn_nominal": cr.qshaft_nominal_kn + cr.qtip_nominal_kn,
                "phi_Rn": p.P_allow_strength,
                "Pcp": p.P_allow_service,
                "Pext": p.P_allow_extreme,
                "uplift": p.P_allow_uplift,
                "material_Pr": cr.strength.material_pr_kn,
                "layers": [
                    {
                        "name": l.name,
                        "thickness": l.thickness_m,
                        "soil_type": l.soil_type,
                        "soil_label": l.soil_label,
                        "spt": l.n_spt,
                        "qs_nominal": l.qs_nominal_kn,
                        "qs_factored": l.qs_factored_kn
                    } for l in cr.layers if l.skin_length_m > 0
                ]
            }

        return {
            "success": result.is_success,
            "abutment_name": model.abutment_name,
            "project_name": model.project_name,
            "skew_angle": model.skew_angle,
            "summary": {
                "stem_flexure": {"pass": v.stem.flexure_check.passed, "Mu": v.stem.Mu_max, "Mr": v.stem.flexure_check.Mr, "ratio": v.stem.flexure_check.demand_capacity_ratio},
                "stem_shear": {"pass": v.stem.shear_check.passed, "Vu": v.stem.Vu_max, "Vr": v.stem.shear_check.Vr, "ratio": v.stem.shear_check.demand_capacity_ratio},
                "stem_crack": {"pass": v.stem.crack_check.passed, "fss": v.stem.crack_check.fss, "fsa": v.stem.crack_check.fsa},
                "backwall_flexure": {"pass": v.backwall.flexure_check.passed, "Mu": v.backwall.Mu, "Mr": v.backwall.flexure_check.Mr, "ratio": v.backwall.flexure_check.demand_capacity_ratio},
                "backwall_shear": {"pass": v.backwall.shear_check.passed, "Vu": v.backwall.Vu, "Vr": v.backwall.shear_check.Vr, "ratio": v.backwall.shear_check.demand_capacity_ratio},
                "backwall_crack": {"pass": v.backwall.crack_check.passed, "fss": v.backwall.crack_check.fss, "fsa": v.backwall.crack_check.fsa},
                "wing_vert": {"pass": v.wing_wall.flexure_vert_fix.passed, "Mu": v.wing_wall.Mu_vert_fix, "Mr": v.wing_wall.flexure_vert_fix.Mr, "ratio": v.wing_wall.flexure_vert_fix.demand_capacity_ratio},
                "wing_bot": {"pass": v.wing_wall.flexure_bot_fix.passed, "Mu": v.wing_wall.Mu_bot_fix, "Mr": v.wing_wall.flexure_bot_fix.Mr, "ratio": v.wing_wall.flexure_bot_fix.demand_capacity_ratio},
                "wing_shear": {"pass": v.wing_wall.shear_vert_fix.passed and v.wing_wall.shear_bot_fix.passed, "Vu": v.wing_wall.Vu_vert_fix, "Vr": v.wing_wall.shear_vert_fix.Vr, "ratio": v.wing_wall.shear_vert_fix.demand_capacity_ratio},
                "wing_crack": {"pass": v.wing_wall.crack_vert_fix.passed and v.wing_wall.crack_bot_fix.passed, "fss": v.wing_wall.crack_vert_fix.fss, "fsa": v.wing_wall.crack_vert_fix.fsa},
                "footing_front": {"pass": v.footing.flexure_front.passed, "Mu": v.footing.Mu_front, "Mr": v.footing.flexure_front.Mr, "ratio": v.footing.flexure_front.demand_capacity_ratio},
                "footing_rear": {"pass": v.footing.flexure_rear.passed, "Mu": v.footing.Mu_rear, "Mr": v.footing.flexure_rear.Mr, "ratio": v.footing.flexure_rear.demand_capacity_ratio},
                "footing_shear": {"pass": v.footing.shear_front.passed and v.footing.shear_rear.passed, "Vu": v.footing.Vu_front, "Vr": v.footing.shear_front.Vr, "ratio": v.footing.shear_front.demand_capacity_ratio},
                "footing_crack": {"pass": v.footing.crack_front.passed and v.footing.crack_rear.passed, "fss": v.footing.crack_front.fss, "fsa": v.footing.crack_front.fsa},
                "footing_punching": {"pass": v.footing.punching_passed, "Vu": v.footing.Vu_punching, "Vr": v.footing.Vr_punching},
                "pile_capacity_service": {"pass": p.P_max_service <= p.P_allow_service, "Pmax": p.P_max_service, "Pcp": p.P_allow_service, "ratio": p.P_max_service / p.P_allow_service if p.P_allow_service else 0},
                "pile_capacity_strength": {"pass": p.P_max_strength <= p.P_allow_strength, "Pmax": p.P_max_strength, "Pgh": p.P_allow_strength, "ratio": p.P_max_strength / p.P_allow_strength if p.P_allow_strength else 0},
                "pile_capacity_extreme": {"pass": p.P_max_extreme <= p.P_allow_extreme, "Pmax": p.P_max_extreme, "Pgh": p.P_allow_extreme, "ratio": p.P_max_extreme / p.P_allow_extreme if p.P_allow_extreme else 0},
                "pile_capacity": {"pass": p.passed_capacity, "Pmax_str": p.P_max_strength, "Pgh": p.P_allow_strength, "Pmax_ext": p.P_max_extreme, "Pgh_ext": p.P_allow_extreme},
                "pile_tension": {"pass": p.passed_tension, "Pmin": p.P_min_service}
            },
            "capacity_result": cap_info,
            "piles": [{"id": p.id, "x": p.x, "y": p.y} for p in p.piles],
            "reports": {
                "docx": f"/api/download/{urllib.parse.quote(os.path.basename(docx_path))}",
                "html": f"/api/download/{urllib.parse.quote(os.path.basename(html_path))}",
                "pdf": f"/api/download/{urllib.parse.quote(os.path.basename(pdf_path))}"
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/calculate/pier")
async def calculate_pier(data: Dict[str, Any]):
    """Tính toán Trụ cầu từ dữ liệu form"""
    try:
        from ..pier.model import PierPileRow
        from ..tcvn.prestress import TendonGroup
        model_fields = {f.name for f in dataclasses.fields(PierModel)}
        filtered_data = {k: v for k, v in data.items() if k in model_fields}
        if "pile_rows" in filtered_data and isinstance(filtered_data["pile_rows"], list):
            filtered_data["pile_rows"] = [
                PierPileRow(**r) if isinstance(r, dict) else r for r in filtered_data["pile_rows"]
            ]
        if "tendon_groups" in filtered_data and isinstance(filtered_data["tendon_groups"], list):
            filtered_data["tendon_groups"] = [
                TendonGroup(**t) if isinstance(t, dict) else t for t in filtered_data["tendon_groups"]
            ]
        model = PierModel(**filtered_data)
        solver = PierSolver(model)
        result = solver.solve()

        # Tạo file báo cáo
        docx_path = os.path.join(OUTPUT_DIR, f"{model.pier_name}_Bao_cao.docx")
        html_path = os.path.join(OUTPUT_DIR, f"{model.pier_name}_Bao_cao.html")
        pdf_path = os.path.join(OUTPUT_DIR, f"{model.pier_name}_Bao_cao.pdf")

        generate_pier_docx_report(result, docx_path)
        generate_pier_html_report(result, html_path)
        generate_pier_pdf_report(result, pdf_path)

        v = result.verification
        p = result.piles
        stem = v.stem
        cap = v.cap

        cap_mr = cap.rc_flexure.Mr if model.cap_type == "RC" else (cap.pt_result.Mr if cap.pt_result else 0)
        cap_ratio = cap.rc_flexure.demand_capacity_ratio if model.cap_type == "RC" else (cap.pt_result.demand_capacity_ratio if cap.pt_result else 0)

        # Trích xuất đường cong P-M
        pm_pts = [{"phiPn": round(pt.phiPn, 1), "phiMn": round(pt.phiMn, 1)} for pt in stem.pm_curve_y]

        pt_stages = [
            {
                "stage_id": st.stage_id,
                "stage_name": st.stage_name,
                "stage_type": st.stage_type,
                "M_ext": round(st.M_ext, 1),
                "P_active": round(st.P_active, 1),
                "Mp_active": round(st.Mp_active, 1),
                "sigma_top": round(st.sigma_top, 2),
                "sigma_bot": round(st.sigma_bot, 2),
                "allowable_comp": round(st.allowable_comp, 2),
                "allowable_tens": round(st.allowable_tens, 2),
                "passed": st.passed
            } for st in cap.pt_result.stages
        ] if cap.pt_result and cap.pt_result.stages else []

        cap_info = None
        if p.capacity_result:
            cr = p.capacity_result
            cap_info = {
                "qshaft_nominal": cr.qshaft_nominal_kn,
                "qtip_nominal": cr.qtip_nominal_kn,
                "Rn_nominal": cr.qshaft_nominal_kn + cr.qtip_nominal_kn,
                "phi_Rn": p.P_allow_strength,
                "Pcp": p.P_allow_service,
                "Pext": p.P_allow_extreme,
                "uplift": p.P_allow_uplift,
                "material_Pr": cr.strength.material_pr_kn,
                "layers": [
                    {
                        "name": l.name,
                        "thickness": l.thickness_m,
                        "soil_type": l.soil_type,
                        "soil_label": l.soil_label,
                        "spt": l.n_spt,
                        "qs_nominal": l.qs_nominal_kn,
                        "qs_factored": l.qs_factored_kn
                    } for l in cr.layers if l.skin_length_m > 0
                ]
            }

        return {
            "success": result.is_success,
            "pier_name": model.pier_name,
            "project_name": model.project_name,
            "pier_type": model.pier_column_type,
            "cap_type": model.cap_type,
            "skew_angle": model.skew_angle,
            "summary": {
                "stem_pm": {"pass": stem.pm_passed, "utilization": stem.utilization_pm, "Pu": stem.Pu_max, "Muy": stem.Muy_max_magnified, "Mux": stem.Mux_max_magnified},
                "stem_shear": {"pass": stem.shear_check.passed, "Vu": stem.Vu_max, "Vr": stem.shear_check.Vr, "ratio": stem.shear_check.demand_capacity_ratio},
                "stem_crack": {"pass": stem.crack_check.passed, "fss": stem.crack_check.fss, "fsa": stem.crack_check.fsa},
                "stem_rebar_ratio": {"pass": stem.rebar_ratio_passed, "rho": stem.rebar_ratio},
                "cap_flexure": {"pass": cap.overall_passed, "Mu": cap.Mu_max, "Mr": cap_mr, "ratio": cap_ratio},
                "cap_shear": {"pass": cap.rc_shear.passed if model.cap_type == "RC" else True, "Vu": cap.Vu_max, "Vr": cap.rc_shear.Vr if cap.rc_shear else 0},
                "cap_crack": {"pass": cap.rc_crack.passed if model.cap_type == "RC" else True, "fss": cap.rc_crack.fss if cap.rc_crack else 0, "fsa": cap.rc_crack.fsa if cap.rc_crack else 0},
                "footing_flexure": {"pass": v.footing.flexure_x.passed and v.footing.flexure_y.passed, "Muy": v.footing.Muy_max, "Mr": v.footing.flexure_x.Mr, "ratio": v.footing.flexure_x.demand_capacity_ratio},
                "footing_shear": {"pass": v.footing.shear_beam.passed, "Vu": v.footing.Vu_max, "Vr": v.footing.shear_beam.Vr, "ratio": v.footing.shear_beam.demand_capacity_ratio},
                "footing_crack": {"pass": v.footing.crack_x.passed and v.footing.crack_y.passed, "fss": v.footing.crack_x.fss, "fsa": v.footing.crack_x.fsa},
                "footing_punching": {"pass": v.footing.punching_passed, "Vu": v.footing.Vu_punching, "Vr": v.footing.Vr_punching},
                "pile_capacity_service": {"pass": p.P_max_service <= p.P_allow_service, "Pmax": p.P_max_service, "Pcp": p.P_allow_service, "ratio": p.P_max_service / p.P_allow_service if p.P_allow_service else 0},
                "pile_capacity_strength": {"pass": p.P_max_strength <= p.P_allow_strength, "Pmax": p.P_max_strength, "Pgh": p.P_allow_strength, "ratio": p.P_max_strength / p.P_allow_strength if p.P_allow_strength else 0},
                "pile_capacity_extreme": {"pass": p.P_max_extreme <= p.P_allow_extreme, "Pmax": p.P_max_extreme, "Pgh": p.P_allow_extreme, "ratio": p.P_max_extreme / p.P_allow_extreme if p.P_allow_extreme else 0},
                "pile_capacity": {"pass": p.passed_capacity, "Pmax_str": p.P_max_strength, "Pgh": p.P_allow_strength, "Pmax_ext": p.P_max_extreme, "Pgh_ext": p.P_allow_extreme},
                "pile_tension": {"pass": p.passed_tension, "Pmin": p.P_min_service}
            },
            "capacity_result": cap_info,
            "bearing_forces": {
                "H_TU_pos": result.loads.bearing_forces.get("H_TU_pos", 0.0) if isinstance(result.loads.bearing_forces, dict) else getattr(result.loads.bearing_forces, "H_TU_pos", 0.0),
                "H_TU_neg": result.loads.bearing_forces.get("H_TU_neg", 0.0) if isinstance(result.loads.bearing_forces, dict) else getattr(result.loads.bearing_forces, "H_TU_neg", 0.0),
                "H_CR": result.loads.bearing_forces.get("H_CR", 0.0) if isinstance(result.loads.bearing_forces, dict) else getattr(result.loads.bearing_forces, "H_CR", 0.0),
                "H_SH": result.loads.bearing_forces.get("H_SH", 0.0) if isinstance(result.loads.bearing_forces, dict) else getattr(result.loads.bearing_forces, "H_SH", 0.0),
                "H_FR": result.loads.bearing_forces.get("H_FR", 0.0) if isinstance(result.loads.bearing_forces, dict) else getattr(result.loads.bearing_forces, "H_FR", 0.0),
                "F_bearing_left_TU": result.loads.bearing_forces.get("F_bearing_left_TU", 0.0) if isinstance(result.loads.bearing_forces, dict) else getattr(result.loads.bearing_forces, "F_bearing_left_TU", 0.0),
                "F_bearing_right_TU": result.loads.bearing_forces.get("F_bearing_right_TU", 0.0) if isinstance(result.loads.bearing_forces, dict) else getattr(result.loads.bearing_forces, "F_bearing_right_TU", 0.0),
            },
            "loads_stem": [
                {"name": lv.name, "Hx": round(lv.Hx, 1), "Hy": round(lv.Hy, 1), "N": round(lv.N, 1), "Mx": round(lv.Mx, 1), "My": round(lv.My, 1)}
                for lv in result.loads.loads_stem_base.values()
            ],
            "loads_footing": [
                {"name": lv.name, "Hx": round(lv.Hx, 1), "Hy": round(lv.Hy, 1), "N": round(lv.N, 1), "Mx": round(lv.Mx, 1), "My": round(lv.My, 1)}
                for lv in result.loads.loads_footing_base.values()
            ],
            "pt_stages": pt_stages,
            "pm_curve": pm_pts,
            "demand_point": {"Pu": stem.Pu_max, "Muy": stem.Muy_max_magnified},
            "piles": [{"id": p.id, "x": p.x, "y": p.y} for p in p.piles],
            "reports": {
                "docx": f"/api/download/{urllib.parse.quote(os.path.basename(docx_path))}",
                "html": f"/api/download/{urllib.parse.quote(os.path.basename(html_path))}",
                "pdf": f"/api/download/{urllib.parse.quote(os.path.basename(pdf_path))}"
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/download/{filename}")
async def download_report(filename: str):
    """Tải file báo cáo DOCX, HTML, PDF"""
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    raise HTTPException(status_code=404, detail="File not found")
