"""
Module: pier.solver
Bộ điều phối tính toán toàn bộ kết cấu Trụ cầu
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from .model import PierModel, PierPileRow
from .loads import calculate_pier_loads, PierLoadsSummary
from .combinations import generate_pier_combinations
from ..abutment.combinations import CombinationResult
from .pile_analysis import analyze_pier_piles, PierPileAnalysisSummary
from .checks import verify_entire_pier, PierVerificationSummary


@dataclass
class PierAnalysisResult:
    """Kết quả phân tích toàn bộ trụ cầu"""
    model: PierModel
    loads: PierLoadsSummary
    cap_combinations: List[CombinationResult]
    stem_combinations: List[CombinationResult]
    footing_combinations: List[CombinationResult]
    piles: PierPileAnalysisSummary
    verification: PierVerificationSummary
    is_success: bool


class PierSolver:
    """
    Solver chính cho bài toán tính toán trụ cầu
    """
    def __init__(self, model: PierModel):
        self.model = model

    def solve(self) -> PierAnalysisResult:
        """
        Chạy toàn bộ quy trình tính toán và kiểm toán trụ
        """
        # 1. Tính toán tải trọng tiêu chuẩn
        loads_summary = calculate_pier_loads(self.model)

        # 2. Tổ hợp tải trọng tại Chân xà mũ, Đỉnh bệ, Đáy bệ
        cap_combs = generate_pier_combinations(loads_summary.loads_cap_base, self.model.num_lanes)
        stem_combs = generate_pier_combinations(loads_summary.loads_stem_base, self.model.num_lanes)
        footing_combs = generate_pier_combinations(loads_summary.loads_footing_base, self.model.num_lanes)

        # 3. Phân tích phản lực cọc
        piles_summary = analyze_pier_piles(self.model, footing_combs)

        # 4. Kiểm toán toàn diện 3 bộ phận
        verification_summary = verify_entire_pier(
            self.model, loads_summary, stem_combs, piles_summary
        )

        return PierAnalysisResult(
            model=self.model,
            loads=loads_summary,
            cap_combinations=cap_combs,
            stem_combinations=stem_combs,
            footing_combinations=footing_combs,
            piles=piles_summary,
            verification=verification_summary,
            is_success=verification_summary.all_passed
        )
