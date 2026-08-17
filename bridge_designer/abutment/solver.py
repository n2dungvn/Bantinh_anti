"""
Module: abutment.solver
Bộ điều phối tính toán toàn bộ kết cấu Mố cầu
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from .model import AbutmentModel, AbutmentPileRow
from .loads import calculate_abutment_loads, AbutmentLoadsSummary
from .combinations import generate_abutment_combinations, CombinationResult
from .pile_analysis import analyze_abutment_piles, AbutmentPileAnalysisSummary
from .checks import verify_entire_abutment, AbutmentVerificationSummary


@dataclass
class AbutmentAnalysisResult:
    """Kết quả phân tích toàn bộ mố cầu"""
    model: AbutmentModel
    loads: AbutmentLoadsSummary
    stem_combinations: List[CombinationResult]
    footing_combinations: List[CombinationResult]
    piles: AbutmentPileAnalysisSummary
    verification: AbutmentVerificationSummary
    is_success: bool


class AbutmentSolver:
    """
    Solver chính cho bài toán tính toán mố cầu
    """
    def __init__(self, model: AbutmentModel):
        self.model = model

    def solve(self) -> AbutmentAnalysisResult:
        """
        Chạy toàn bộ quy trình tính toán và kiểm toán mố
        """
        # 1. Tính toán tải trọng tiêu chuẩn
        loads_summary = calculate_abutment_loads(self.model)

        # 2. Tổ hợp tải trọng tại Đỉnh bệ (Stem base) và Đáy bệ (Footing base)
        stem_combs = generate_abutment_combinations(loads_summary.loads_stem_base, self.model.num_lanes)
        footing_combs = generate_abutment_combinations(loads_summary.loads_footing_base, self.model.num_lanes)

        # 3. Phân tích phản lực cọc
        piles_summary = analyze_abutment_piles(self.model, footing_combs)

        # 4. Kiểm toán toàn diện 4 bộ phận
        verification_summary = verify_entire_abutment(
            self.model, loads_summary, stem_combs, piles_summary
        )

        return AbutmentAnalysisResult(
            model=self.model,
            loads=loads_summary,
            stem_combinations=stem_combs,
            footing_combinations=footing_combs,
            piles=piles_summary,
            verification=verification_summary,
            is_success=verification_summary.all_passed
        )
