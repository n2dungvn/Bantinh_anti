from dataclasses import dataclass
import math
from typing import List, Dict, Tuple, Optional, Any
from .model import PierModel
from ..abutment.combinations import CombinationResult
from ..tcvn.ts_pile_solver import TSPile, TSPileGroupSolver, TSPileReactionResult, TSPileForces
from ..tcvn.piles import Pile
from ..tcvn.ts_cap_engine import PileInput, SoilLayer, SCTCalculator, CapacityResult


@dataclass
class PierPileAnalysisSummary:
    """Tổng hợp kết quả phản lực cọc trụ"""
    piles: List[Pile]
    reactions_all: List[TSPileReactionResult]
    P_max_strength: float
    P_min_strength: float
    P_max_service: float
    P_min_service: float
    P_max_extreme: float
    P_min_extreme: float
    H_max_all: float
    controlling_comb_max: str
    controlling_comb_min: str
    passed_capacity: bool
    passed_tension: bool
    capacity_result: Optional[CapacityResult] = None  # Kết quả tính sức chịu tải đất nền TS-CAP
    P_allow_service: float = 4800.0
    P_allow_strength: float = 6720.0
    P_allow_extreme: float = 8640.0
    P_allow_uplift: float = 1500.0


def analyze_pier_piles(
    model: PierModel,
    combinations: List[CombinationResult]
) -> PierPileAnalysisSummary:
    """
    Sinh lưới tọa độ cọc trụ và giải phản lực cọc theo phương pháp ma trận độ cứng TS_PILE,
    đồng thời tính toán sức chịu tải đất nền chuẩn TS_CAP.
    """
    ts_piles: List[TSPile] = []
    piles_simple: List[Pile] = []
    pile_id = 1

    if model.custom_piles and len(model.custom_piles) > 0:
        for idx, cp in enumerate(model.custom_piles, 1):
            pid = cp.get("id", idx)
            pname = f"P{pid}"
            px = float(cp.get("x", 0.0))
            py = float(cp.get("y", 0.0))
            pd = float(cp.get("diameter", model.pile_diameter))
            ts_piles.append(TSPile(id=pid, name=pname, x=px, y=py, diameter=pd))
            piles_simple.append(Pile(id=pid, x=px, y=py, diameter=pd))
    else:
        # Tạo tọa độ các cọc từ danh sách hàng cọc đổi về hệ tọa độ vuông góc (Orthogonal)
        skew_deg = getattr(model, "skew_angle", 90.0)
        alpha_rad = math.radians(skew_deg)
        tan_alpha = math.tan(alpha_rad) if abs(skew_deg - 90.0) > 0.01 else 0.0

        for row in model.pile_rows:
            r_count = row.get("count", 0) if isinstance(row, dict) else getattr(row, "count", 0)
            r_spacing = row.get("spacing", 1.0) if isinstance(row, dict) else getattr(row, "spacing", 1.0)
            r_x = row.get("x", 0.0) if isinstance(row, dict) else getattr(row, "x", 0.0)
            if r_count <= 0:
                continue
            total_width = (r_count - 1) * r_spacing
            start_y = -total_width / 2.0
            for j in range(r_count):
                y_pos = start_y + j * r_spacing
                # Chuyển đổi tọa độ sang hệ trục vuông góc của TS-Pile:
                # X_ortho = r_x - y_pos / tan(alpha)
                x_ortho = r_x - (y_pos / tan_alpha) if tan_alpha != 0.0 else r_x
                pname = f"P{pile_id}"
                ts_piles.append(TSPile(
                    id=pile_id,
                    name=pname,
                    x=round(x_ortho, 4),
                    y=round(y_pos, 4),
                    diameter=model.pile_diameter
                ))
                piles_simple.append(Pile(
                    id=pile_id,
                    x=round(x_ortho, 4),
                    y=round(y_pos, 4),
                    diameter=model.pile_diameter
                ))
                pile_id += 1

    # 1. Tính toán sức chịu tải đất nền bằng TS_CAP nếu có địa tầng
    cap_res: Optional[CapacityResult] = None
    p_allow_ser = model.pile_capacity_allowable
    p_allow_str = 1.40 * model.pile_capacity_allowable
    p_allow_ext = 1.80 * model.pile_capacity_allowable
    p_allow_up = 1500.0

    if getattr(model, "auto_calculate_capacity", True) and getattr(model, "soil_layers", None) and len(model.soil_layers) > 0:
        try:
            cap_layers = []
            for sly in model.soil_layers:
                cap_layers.append(SoilLayer(
                    name=sly.get("name", ""),
                    bottom_elev_m=float(sly.get("bottom_elev_m", 0.0)),
                    soil_type=int(sly.get("soil_type", 1)),
                    n_spt=float(sly.get("n_spt", 0.0)),
                    gamma_kN_m3=float(sly.get("gamma_kN_m3", 18.0)),
                    c_mpa=float(sly.get("c_mpa", 0.0)),
                    phi_deg=float(sly.get("phi_deg", 0.0)),
                    qu_mpa=float(sly.get("qu_mpa", 0.0)),
                    rqd=float(sly.get("rqd", 0.0)),
                    comment=sly.get("comment", "")
                ))

            pile_inp = PileInput(
                project=model.project_name,
                item=model.pier_name,
                mode=getattr(model, "pile_mode_ts_cap", "Cọc khoan trong đất"),
                pile_type=getattr(model, "pile_type_ts_cap", "Cọc khoan nhồi"),
                diameter_mm=model.pile_diameter * 1000.0,
                ground_elev_m=getattr(model, "ground_elev_m", 5.0),
                cap_bottom_elev_m=getattr(model, "cap_bottom_elev_m", 0.0),
                pile_tip_elev_m=getattr(model, "pile_tip_elev_m", -35.0),
                water_elev_m=getattr(model, "water_elev_m", 2.0),
                fc_mpa=model.fc_prime,
                fy_mpa=model.fy,
                n_rebars=getattr(model, "n_rebars_pile", 24),
                rebar_dia_mm=getattr(model, "rebar_dia_pile", 25.0),
                spacing_m=4.5,
                pile_count_in_group=len(piles_simple),
                group_layout="2",
                layers=cap_layers
            )
            cap_res = SCTCalculator.calculate(pile_inp)
            p_allow_str = cap_res.strength.governing_kn
            p_allow_ext = cap_res.extreme.governing_kn
            p_allow_ser = cap_res.extreme.governing_kn  # Ở TTGH Sử dụng, hệ số sức kháng phi = 1.0 (TCVN 11823-10 Điều 10.5.5.1)
            p_allow_up = cap_res.strength.uplift_single_magnitude_kn
        except Exception as err:
            print(f"Lỗi tính toán TS-CAP cho trụ: {err}")

    # 2. Giải phản lực đầu cọc bằng TS_PILE
    solver = TSPileGroupSolver(ts_piles, Bx=model.Bbe, By=model.Cbe, Cz=model.Hbe)
    reactions: List[TSPileReactionResult] = []

    p_max_str = -1e9
    p_min_str = 1e9
    p_max_ser = -1e9
    p_min_ser = 1e9
    p_max_ext = -1e9
    p_min_ext = 1e9
    h_max = 0.0

    comb_max = ""
    comb_min = ""

    all_passed_cap = True

    for comb in combinations:
        res = solver.calculate_reaction(
            comb_name=comb.comb_name,
            limit_state_group=comb.limit_state_group,
            N=comb.N,
            Mx=comb.Mx,
            My=comb.My,
            Hx=comb.Hx,
            Hy=comb.Hy,
            Mz=0.0
        )
        reactions.append(res)

        # Kiểm tra sức chịu tải từng tổ hợp theo đúng TTGH TCVN 11823-10
        if comb.limit_state_group == "STRENGTH":
            if res.P_max > p_allow_str:
                all_passed_cap = False
            if res.P_max > p_max_str:
                p_max_str = res.P_max
                comb_max = comb.comb_name
            if res.P_min < p_min_str:
                p_min_str = res.P_min
                comb_min = comb.comb_name
        elif comb.limit_state_group == "SERVICE":
            if res.P_max > p_allow_ser:
                all_passed_cap = False
            p_max_ser = max(p_max_ser, res.P_max)
            p_min_ser = min(p_min_ser, res.P_min)
        elif comb.limit_state_group == "EXTREME":
            if res.P_max > p_allow_ext:
                all_passed_cap = False
            p_max_ext = max(p_max_ext, res.P_max)
            p_min_ext = min(p_min_ext, res.P_min)

        h_max = max(h_max, res.H_max)

    pass_ten = (p_min_ser >= 0.0)

    return PierPileAnalysisSummary(
        piles=piles_simple,
        reactions_all=reactions,
        P_max_strength=p_max_str,
        P_min_strength=p_min_str,
        P_max_service=p_max_ser,
        P_min_service=p_min_ser,
        P_max_extreme=p_max_ext,
        P_min_extreme=p_min_ext,
        H_max_all=h_max,
        controlling_comb_max=comb_max,
        controlling_comb_min=comb_min,
        passed_capacity=all_passed_cap,
        passed_tension=pass_ten,
        capacity_result=cap_res,
        P_allow_service=p_allow_ser,
        P_allow_strength=p_allow_str,
        P_allow_extreme=p_allow_ext,
        P_allow_uplift=p_allow_up
    )
