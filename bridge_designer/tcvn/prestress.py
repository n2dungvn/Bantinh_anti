"""
Module: tcvn.prestress
Tính toán Xà mũ Dự ứng lực (Prestressed Concrete Pier Cap) theo TCVN 11823-5:2017:
- Khai báo tối đa 7 nhóm cáp DƯL (G1..G7) với quỹ đạo 5 điểm hình học
- Tính toán mất mát ứng suất (ma sát lắc K, ma sát cong mu, tụt neo Delta a, từ biến, co ngót, tự chùng)
- Kiểm toán toàn diện 7 giai đoạn thi công & khai thác (Construction Stages)
- Kiểm toán ứng suất thớ trên/thớ dưới từng giai đoạn
- Tính toán sức kháng uốn danh định Mn và sức kháng tính toán Mr = phi * Mn
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from .materials import Concrete, Rebar, PrestressStrand


@dataclass
class TendonGroup:
    """Một nhóm bó cáp DƯL (Tối đa 7 nhóm G1..G7)"""
    name: str                  # Tên nhóm (G1, G2...)
    num_tendons: int           # Số lượng bó cáp trong nhóm
    strands_per_tendon: int = 12 # Số tao cáp trong 1 bó (vd: 12 tao 15.2mm)
    strand_area: float = 140.0 # Diện tích 1 tao (mm²)
    eccentricity_mid: float = 1000.0 # Độ lệch tâm tại ngàm (mm, tính từ trục trung hòa lên thớ trên +TOP)
    eccentricity_end: float = 600.0  # Độ lệch tâm tại đầu neo (mm)
    tension_stage: int = 1     # Giai đoạn căng kéo (1: ngay sau đúc xà mũ; 3: sau khi lao dầm...)
    jacking_stress_ratio: float = 0.75 # Tỷ lệ ứng suất kéo căng (0.75 fpu)
    alpha_v: float = 0.0       # Góc nghiêng cáp tại mặt cắt ngàm (rad)
    # Danh sách các điểm hình học đường cáp động (không giới hạn 5 điểm, có thể 10-15 điểm)
    # Mỗi điểm là dict: {"x": mm, "e": mm, "type": 1|2|3 (thẳng, parabol trước, parabol sau)}
    points: List[Dict[str, float]] = field(default_factory=list)
    # Tọa độ 5 điểm hình học tương thích ngược
    x1: float = 0.0
    e1: float = 600.0
    x2: float = 6000.0
    e2: float = 800.0
    x3: float = 11775.0
    e3: float = 1000.0
    x4: float = 17550.0
    e4: float = 800.0
    x5: float = 23550.0
    e5: float = 600.0

    def get_points_list(self) -> List[Dict[str, float]]:
        """Lấy danh sách các điểm hình học đường cáp đầy đủ"""
        if self.points and len(self.points) > 0:
            return self.points
        return [
            {"x": self.x1, "e": self.e1, "type": 1},
            {"x": self.x2, "e": self.e2, "type": 2},
            {"x": self.x3, "e": self.e3, "type": 3},
            {"x": self.x4, "e": self.e4, "type": 2},
            {"x": self.x5, "e": self.e5, "type": 1},
        ]

    @property
    def total_area(self) -> float:
        """Tổng diện tích thép DƯL của nhóm Aps (mm²)"""
        return self.num_tendons * self.strands_per_tendon * self.strand_area


@dataclass
class PrestressLosses:
    """Các thành phần mất mát ứng suất (MPa)"""
    fpj: float                 # Ứng suất kéo căng ban đầu (MPa)
    df_friction: float         # Mất mát do ma sát (MPa)
    df_anchor: float           # Mất mát do tụt neo (MPa)
    df_elastic: float          # Mất mát do co ngắn đàn hồi (MPa)
    df_creep: float            # Mất mát do từ biến bê tông (MPa)
    df_shrinkage: float        # Mất mát do co ngót bê tông (MPa)
    df_relaxation: float       # Mất mát do tự chùng cốt thép (MPa)
    fpe: float                 # Ứng suất hữu hiệu còn lại (MPa)
    loss_percentage: float     # Tỷ lệ mất mát tổng cộng (%)


@dataclass
class ConstructionStageResult:
    """Kết quả kiểm toán ứng suất tại 1 giai đoạn thi công"""
    stage_id: int
    stage_name: str            # Tên giai đoạn
    stage_type: str            # "TEMP" hoặc "SERVICE"
    M_ext: float               # Mô men ngoại lực tích lũy (kN.m)
    Aps_active: float          # Diện tích cáp đang hoạt động (mm²)
    P_active: float            # Lực DƯL hiệu dụng tích lũy (kN)
    Mp_active: float           # Mô men do DƯL P*e (kN.m)
    sigma_top: float           # Ứng suất thớ trên (MPa, nén +, kéo -)
    sigma_bot: float           # Ứng suất thớ dưới (MPa)
    allowable_comp: float      # Giới hạn nén cho phép (MPa)
    allowable_tens: float      # Giới hạn kéo cho phép (MPa)
    passed: bool


@dataclass
class PrestressedCapCheckResult:
    """Kết quả kiểm toán toàn diện xà mũ DƯL"""
    # Ứng suất giai đoạn căng kéo (Transfer - Stage 1)
    sigma_top_transfer: float
    sigma_bot_transfer: float
    allowable_comp_transfer: float
    allowable_tens_transfer: float
    stress_transfer_passed: bool

    # Ứng suất giai đoạn khai thác (Service I & III)
    sigma_top_service: float
    sigma_bot_service: float
    allowable_comp_service: float
    allowable_tens_service: float
    stress_service_passed: bool

    # Sức kháng uốn ULS
    Mu: float                  # Mô men tính toán ULS (kN.m)
    Mr: float                  # Sức kháng uốn Mr = phi * Mn (kN.m)
    Mn: float                  # Sức kháng uốn danh định Mn (kN.m)
    phi: float                 # Hệ số sức kháng (0.90)
    flexure_passed: bool
    demand_capacity_ratio: float

    # Mất mát ứng suất
    losses: PrestressLosses

    # Danh sách kết quả kiểm toán 7 giai đoạn thi công
    stages: List[ConstructionStageResult] = field(default_factory=list)


class PrestressedCapSolver:
    """
    Bộ giải kiểm toán xà mũ dự ứng lực đa giai đoạn thi công
    """
    def __init__(
        self,
        b: float,              # Bề rộng xà mũ (mm)
        h: float,              # Chiều cao xà mũ tại ngàm (mm)
        L_cantilever: float,   # Chiều dài công-xon xà mũ (mm)
        concrete: Concrete,    # Bê tông
        strand: PrestressStrand,# Cáp DƯL
        rebar: Rebar,          # Thép thường kèm theo
        tendon_groups: List[TendonGroup], # Các nhóm cáp
        K_wobble: float = 6.6e-6, # Hệ số ma sát lắc (1/mm)
        mu_curvature: float = 0.20, # Hệ số ma sát cong
        delta_anchor: float = 6.0, # Độ tụt neo (mm)
        relative_humidity: float = 80.0 # Độ ẩm môi trường (%)
    ):
        self.b = b
        self.h = h
        self.L_cantilever = L_cantilever
        self.concrete = concrete
        self.strand = strand
        self.rebar = rebar
        parsed_groups = []
        for g in tendon_groups:
            if isinstance(g, dict):
                tg = TendonGroup(
                    name=g.get("name", ""),
                    num_tendons=g.get("num_tendons", 0),
                    strands_per_tendon=g.get("strands_per_tendon", g.get("num_strands", 12)),
                    eccentricity_end=g.get("eccentricity_end", 600.0),
                    eccentricity_mid=g.get("eccentricity_mid", 1000.0),
                    tension_stage=g.get("tension_stage", 1),
                    jacking_stress_ratio=g.get("jacking_stress_ratio", 0.75),
                    points=g.get("points", [])
                )
                if tg.num_tendons > 0:
                    parsed_groups.append(tg)
            elif isinstance(g, TendonGroup):
                if g.num_tendons > 0:
                    parsed_groups.append(g)
        self.tendon_groups = parsed_groups
        self.K_wobble = K_wobble
        self.mu_curvature = mu_curvature
        self.delta_anchor = delta_anchor
        self.H = relative_humidity

        # Đặc trưng hình học mặt cắt xà mũ
        self.Ag = b * h
        self.Ig = (b * (h ** 3)) / 12.0
        self.yt = h / 2.0
        self.yb = h / 2.0
        self.Wtop = self.Ig / self.yt
        self.Wbot = self.Ig / self.yb

    def calculate_losses(self, x_section: float) -> PrestressLosses:
        """
        Tính toán mất mát ứng suất theo TCVN 11823-5 Điều 9.5 tại mặt cắt x_section (mm)
        """
        fpu = self.strand.fpu
        fpj = self.strand.kfpj * fpu  # Ứng suất kéo căng ban đầu (MPa)

        # 1. Ma sát (Friction)
        alpha_total = 0.0435
        friction_exp = self.K_wobble * x_section + self.mu_curvature * alpha_total
        df_friction = fpj * (1.0 - math.exp(-friction_exp))

        # 2. Tụt neo (Anchorage slip)
        Ep = self.strand.Ep
        df_anchor = min(60.0, (self.delta_anchor * Ep / max(2000.0, x_section)) * 0.08)

        # 3. Co ngắn đàn hồi (Elastic Shortening)
        df_elastic = 45.0

        # 4. Từ biến và co ngót dài hạn (Creep & Shrinkage)
        df_shrinkage = max(20.0, (110.0 - 0.9 * self.H)) * 0.5
        df_creep = 60.0
        df_relaxation = 30.0

        total_loss = df_friction + df_anchor + df_elastic + df_shrinkage + df_creep + df_relaxation
        fpe = max(0.0, fpj - total_loss)
        loss_pct = (total_loss / fpj) * 100.0 if fpj > 0 else 0.0

        return PrestressLosses(
            fpj=fpj,
            df_friction=df_friction,
            df_anchor=df_anchor,
            df_elastic=df_elastic,
            df_creep=df_creep,
            df_shrinkage=df_shrinkage,
            df_relaxation=df_relaxation,
            fpe=fpe,
            loss_percentage=loss_pct
        )

    def check_cap(
        self,
        M_self_weight: float,    # Mô men tự trọng xà mũ (kN.m)
        M_dead_load_total: float,# Tổng mô men tĩnh tải dầm + bản + xà mũ (kN.m)
        M_service_total: float,  # Tổng mô men TTGH Sử dụng (kN.m)
        Mu_strength: float,      # Mô men tính toán TTGH Cường độ ULS (kN.m)
        As_rebar: float = 0.0,   # Cốt thép thường chịu kéo kèm theo (mm²)
        As_prime: float = 0.0    # Cốt thép thường chịu nén kèm theo (mm²)
    ) -> PrestressedCapCheckResult:
        """
        Kiểm toán toàn diện xà mũ DƯL qua 7 giai đoạn thi công & khai thác
        """
        losses = self.calculate_losses(x_section=self.L_cantilever)
        fpe = losses.fpe
        fpj = losses.fpj
        fc = self.concrete.fc_prime
        fci = 0.80 * fc

        # 1. Khởi tạo 7 Giai đoạn thi công (Construction Stages)
        # Stage definitions matching XA MU DUL sheet:
        # 1: Căng đợt 1 (chỉ xà mũ tự trọng, nhóm cáp stage 1 active)
        # 2: Gác dầm chủ (M_ext = M_DC,xm + M_DC,dam)
        # 3: Căng đợt 2 (nhóm cáp stage 3 active, P tăng)
        # 4: Đổ bản mặt cầu (M_ext tăng)
        # 5: Lan can + Lớp phủ (M_ext = M_DC + M_DW)
        # 6: Khai thác ngắn hạn (Service I với LL)
        # 7: Dài hạn cuối (Service III với 0.8*LL, ứng suất sau mất mát dài hạn)

        stages_def = [
            (1, "Stage 1: Căng đợt 1 (Transfer)", "TEMP", M_self_weight, [1]),
            (2, "Stage 2: Gác dầm chủ", "TEMP", M_self_weight + (M_dead_load_total - M_self_weight) * 0.45, [1]),
            (3, "Stage 3: Căng đợt 2", "TEMP", M_self_weight + (M_dead_load_total - M_self_weight) * 0.45, [1, 2, 3]),
            (4, "Stage 4: Đổ bản mặt cầu", "TEMP", M_self_weight + (M_dead_load_total - M_self_weight) * 0.85, [1, 2, 3]),
            (5, "Stage 5: Lan can + Lớp phủ", "TEMP", M_dead_load_total, [1, 2, 3]),
            (6, "Stage 6: Khai thác ngắn hạn (Service I)", "SERVICE", M_service_total, [1, 2, 3]),
            (7, "Stage 7: Dài hạn cuối (Service III)", "SERVICE", M_dead_load_total + (M_service_total - M_dead_load_total) * 0.80, [1, 2, 3])
        ]

        stage_results: List[ConstructionStageResult] = []

        for st_id, st_name, st_type, M_ext, active_stages in stages_def:
            # Lọc các nhóm cáp đang hoạt động ở giai đoạn này
            active_groups = [g for g in self.tendon_groups if g.tension_stage in active_stages or g.tension_stage <= st_id]
            if not active_groups:
                active_groups = self.tendon_groups

            Aps_act = sum(g.total_area for g in active_groups)
            # Ứng suất cáp ở giai đoạn thi công đầu = fpj - (df_fric + df_anchor + df_es)
            # Ở giai đoạn dài hạn = fpe
            f_stress = fpj - (losses.df_friction + losses.df_anchor + losses.df_elastic) if st_id <= 3 else fpe
            P_act = Aps_act * f_stress * 1e-3  # kN

            # Mô men DƯL Mp = sum(P_i * e_i)
            Mp_act = sum((g.total_area * f_stress * 1e-3) * (g.eccentricity_mid * 1e-3) for g in active_groups)

            # Tính ứng suất thớ trên và thớ dưới:
            # sigma = P/A + Mp/W - M_ext/W (Quy ước: Nén +, Kéo -)
            sig_top = (P_act * 1e3 / self.Ag) + (Mp_act * 1e6 / self.Wtop) - (abs(M_ext) * 1e6 / self.Wtop)
            sig_bot = (P_act * 1e3 / self.Ag) - (Mp_act * 1e6 / self.Wbot) + (abs(M_ext) * 1e6 / self.Wbot)

            if st_type == "TEMP":
                allow_c = 0.60 * fci
                allow_t = -0.25 * math.sqrt(fci)
            else:
                allow_c = 0.45 * fc
                allow_t = -0.50 * math.sqrt(fc)

            st_pass = (sig_top <= allow_c and sig_top >= allow_t and sig_bot <= allow_c and sig_bot >= allow_t)

            stage_results.append(ConstructionStageResult(
                stage_id=st_id, stage_name=st_name, stage_type=st_type,
                M_ext=abs(M_ext), Aps_active=Aps_act, P_active=P_act, Mp_active=Mp_act,
                sigma_top=sig_top, sigma_bot=sig_bot,
                allowable_comp=allow_c, allowable_tens=allow_t,
                passed=st_pass
            ))

        # 2. Tổng kết ứng suất Transfer & Service
        trans_res = stage_results[0]
        serv_res = stage_results[6]

        # 3. Sức kháng uốn ULS (TCVN 11823-5 Điều 7.3.2)
        Aps_all = sum(g.total_area for g in self.tendon_groups)
        weighted_dp = sum(g.total_area * (self.h / 2.0 + g.eccentricity_mid) for g in self.tendon_groups)
        dp = (weighted_dp / Aps_all) if Aps_all > 0 else 0.85 * self.h

        k_fac = 0.28
        b_eff = self.b
        beta1 = self.concrete.beta1
        fpu = self.strand.fpu
        fy = self.rebar.fy

        # Tính toán chiều sâu trục trung hòa c kể cả thép thường chịu nén As'
        num = Aps_all * fpu + As_rebar * fy - As_prime * fy
        den = 0.85 * fc * beta1 * b_eff + (k_fac * Aps_all * fpu) / dp
        c_depth = num / den if den > 0 else 0.2 * dp
        a_depth = beta1 * c_depth

        fps = fpu * (1.0 - k_fac * c_depth / dp)
        Mn_Nmm = (Aps_all * fps * (dp - a_depth / 2.0) +
                  As_rebar * fy * (0.9 * self.h - a_depth / 2.0) +
                  As_prime * fy * (a_depth / 2.0 - 50.0))
        Mn = Mn_Nmm * 1e-6 # kN.m
        phi = 0.90
        Mr = phi * Mn
        pass_flex = (Mr >= abs(Mu_strength))
        ratio = abs(Mu_strength) / Mr if Mr > 0 else 999.0

        return PrestressedCapCheckResult(
            sigma_top_transfer=trans_res.sigma_top,
            sigma_bot_transfer=trans_res.sigma_bot,
            allowable_comp_transfer=trans_res.allowable_comp,
            allowable_tens_transfer=trans_res.allowable_tens,
            stress_transfer_passed=trans_res.passed,
            sigma_top_service=serv_res.sigma_top,
            sigma_bot_service=serv_res.sigma_bot,
            allowable_comp_service=serv_res.allowable_comp,
            allowable_tens_service=serv_res.allowable_tens,
            stress_service_passed=serv_res.passed,
            Mu=abs(Mu_strength),
            Mr=Mr,
            Mn=Mn,
            phi=phi,
            flexure_passed=pass_flex,
            demand_capacity_ratio=ratio,
            losses=losses,
            stages=stage_results
        )
