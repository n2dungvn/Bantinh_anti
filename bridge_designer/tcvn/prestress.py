"""
Module: tcvn.prestress
Tính toán Xà mũ Dự ứng lực (Prestressed Concrete Pier Cap) theo TCVN 11823-5:2017:
- Khai báo các nhóm bó cáp DƯL (G1..G7) với số lượng bó, số tao, diện tích, độ lệch tâm
- Tính toán mất mát ứng suất theo TCVN 11823-5 Điều 5.9.5:
  + Ma sát dọc và ma sát lắc (TCVN Điều 5.9.5.2.2b)
  + Tụt neo (TCVN Điều 5.9.5.2.1)
  + Co ngắn đàn hồi căng sau tuần tự (TCVN Điều 5.9.5.2.3b)
  + Co ngót dài hạn (TCVN Điều 5.9.5.3)
  + Từ biến bê tông (TCVN Điều 5.9.5.3)
  + Tự chùng cốt thép DƯL (TCVN Điều 5.9.5.3)
- Kiểm toán toàn diện 7 giai đoạn thi công & khai thác từ mô hình tải trọng thực tế
- Kiểm toán ứng suất thớ trên/thớ dưới từng giai đoạn
- Tính toán sức kháng uốn danh định Mn và sức kháng tính toán Mr = phi * Mn
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from .materials import Concrete, Rebar, PrestressStrand


@dataclass
class TendonGroup:
    """Một nhóm bó cáp DƯL"""
    name: str                  # Tên nhóm (G1, G2...)
    num_tendons: int           # Số lượng bó cáp trong nhóm
    strands_per_tendon: int = 12 # Số tao cáp trong 1 bó (vd: 12 tao 15.2mm)
    strand_area: float = 140.0 # Diện tích 1 tao (mm²)
    eccentricity_mid: float = 1000.0 # Độ lệch tâm tại ngàm (mm, tính từ trục trung hòa lên thớ trên +TOP)
    eccentricity_end: float = 600.0  # Độ lệch tâm tại đầu neo (mm)
    tension_stage: int = 1     # Giai đoạn căng kéo (1: Transfer; 2: Sau lao dầm...)
    alpha_v: float = 0.0       # Góc nghiêng cáp tại mặt cắt ngàm (rad)
    jacking_stress_ratio: float = 0.75 # Tỷ lệ ứng suất kéo căng fpj / fpu
    points: List[Dict[str, float]] = field(default_factory=list)
    # Tọa độ 5 điểm tương thích ngược
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

    @property
    def num_strands(self) -> int:
        """Alias cho strands_per_tendon để đảm bảo tương thích ngược"""
        return self.strands_per_tendon

    @property
    def total_area(self) -> float:
        """Tổng diện tích thép DƯL của nhóm Aps (mm²)"""
        return self.num_tendons * self.strands_per_tendon * self.strand_area

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


@dataclass
class PrestressLosses:
    """Các thành phần mất mát ứng suất (MPa) theo TCVN 11823-5 Điều 5.9.5"""
    fpj: float                 # Ứng suất kéo căng ban đầu (MPa)
    df_friction: float         # Mất mát do ma sát dọc và ma sát lắc (MPa)
    df_anchor: float           # Mất mát do tụt neo (MPa)
    df_elastic: float          # Mất mát do co ngắn đàn hồi (MPa)
    df_creep: float            # Mất mát do từ biến bê tông (MPa)
    df_shrinkage: float        # Mất mát do co ngót bê tông (MPa)
    df_relaxation: float       # Mất mát do tự chùng cốt thép (MPa)
    fpe: float                 # Ứng suất hữu hiệu còn lại sau toàn bộ mất mát (MPa)
    loss_percentage: float     # Tỷ lệ mất mát tổng cộng (%)
    method: str = "TCVN_11823_5_ARTICLE_5_9_5"
    status: str = "VALIDATED"


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
        tendon_groups: List[Any], # Các nhóm cáp
        K_wobble: float = 6.6e-6, # Hệ số ma sát lắc (1/mm)
        mu_curvature: float = 0.20, # Hệ số ma sát cong (1/rad)
        delta_anchor: float = 6.0, # Độ tụt neo (mm)
        relative_humidity: float = 80.0 # Độ ẩm môi trường (%)
    ):
        self.b = b
        self.h = h
        self.L_cantilever = L_cantilever
        self.concrete = concrete
        self.strand = strand
        self.rebar = rebar
        self.K_wobble = K_wobble
        self.mu_curvature = mu_curvature
        self.delta_anchor = delta_anchor
        self.H = relative_humidity

        # Parse & chuẩn hóa danh sách nhóm cáp
        parsed_groups: List[TendonGroup] = []
        for g in tendon_groups:
            if isinstance(g, dict):
                n_strands = g.get("strands_per_tendon") or g.get("num_strands") or 12
                tg = TendonGroup(
                    name=str(g.get("name", "")),
                    num_tendons=int(g.get("num_tendons", 0)),
                    strands_per_tendon=int(n_strands),
                    strand_area=float(g.get("strand_area", 140.0)),
                    eccentricity_end=float(g.get("eccentricity_end", 600.0)),
                    eccentricity_mid=float(g.get("eccentricity_mid", 1000.0)),
                    tension_stage=int(g.get("tension_stage", 1)),
                    alpha_v=float(g.get("alpha_v", 0.0)),
                    jacking_stress_ratio=float(g.get("jacking_stress_ratio", 0.75)),
                    points=g.get("points", [])
                )
                if tg.num_tendons > 0:
                    parsed_groups.append(tg)
            elif isinstance(g, TendonGroup):
                if g.num_tendons > 0:
                    parsed_groups.append(g)
        self.tendon_groups = parsed_groups

        # Đặc trưng hình học mặt cắt nguyên xà mũ
        self.Ag = b * h
        self.Ig = (b * (h ** 3)) / 12.0
        self.yt = h / 2.0
        self.yb = h / 2.0
        self.Wtop = self.Ig / self.yt
        self.Wbot = self.Ig / self.yb

    def calculate_losses(
        self,
        x_section: float,
        M_DC_transfer: float = 0.0,
        M_DC_super: float = 0.0
    ) -> PrestressLosses:
        """
        Tính toán mất mát ứng suất theo TCVN 11823-5 Điều 5.9.5 tại mặt cắt x_section (mm).
        """
        fpu = self.strand.fpu
        fpj = self.strand.kfpj * fpu  # Ứng suất kéo căng ban đầu (MPa)
        Ep = self.strand.Ep
        Eci = self.concrete.Ec  # Mô đun đàn hồi bê tông lúc truyền ứng suất

        # 1. Ma sát dọc và ma sát lắc (TCVN 11823-5 Điều 5.9.5.2.2b)
        # Góc đổi hướng tổng cộng alpha: ước lượng từ độ võng cáp parabolic Delta_e
        avg_e_mid = sum(g.total_area * g.eccentricity_mid for g in self.tendon_groups) / max(1.0, sum(g.total_area for g in self.tendon_groups)) if self.tendon_groups else 0.0
        avg_e_end = sum(g.total_area * g.eccentricity_end for g in self.tendon_groups) / max(1.0, sum(g.total_area for g in self.tendon_groups)) if self.tendon_groups else 0.0
        delta_e = abs(avg_e_mid - avg_e_end)
        alpha_rad = (2.0 * delta_e / max(1000.0, x_section)) if x_section > 0 else 0.0
        friction_arg = self.K_wobble * x_section + self.mu_curvature * alpha_rad
        df_friction = fpj * (1.0 - math.exp(-max(0.0, friction_arg)))

        # 2. Tụt neo (TCVN 11823-5 Điều 5.9.5.2.1)
        # Độ dài phân bố tụt neo L_set = sqrt(Delta_a * Ep / p_friction)
        L_eff = max(1000.0, x_section)
        df_anchor = min(0.15 * fpj, (self.delta_anchor * Ep) / L_eff)

        # Ứng suất sau ma sát và tụt neo tại mặt cắt
        fp0 = max(0.0, fpj - df_friction - df_anchor)
        Aps_total = sum(g.total_area for g in self.tendon_groups)
        Pj_total = Aps_total * fp0 * 1e-3  # kN

        # Ứng suất nén trong bê tông tại trọng tâm cáp lúc truyền lực fcgp (MPa)
        # fcgp = P/A + P*e^2/I - M_DC*e/I
        e_cgp = avg_e_mid
        fcgp = (Pj_total * 1e3 / self.Ag) + (Pj_total * 1e3 * (e_cgp ** 2) / self.Ig) - (abs(M_DC_transfer) * 1e6 * e_cgp / self.Ig)
        fcgp = max(0.0, fcgp)

        # 3. Co ngắn đàn hồi cho căng sau tuần tự (TCVN 11823-5 Điều 5.9.5.2.3b)
        # df_elastic = (N_g - 1)/(2*N_g) * (Ep / Eci) * fcgp
        N_g = max(1, len(self.tendon_groups))
        seq_factor = (N_g - 1.0) / (2.0 * N_g) if N_g > 1 else 0.0
        df_elastic = seq_factor * (Ep / Eci) * fcgp

        # 4. Mất mát dài hạn do Co ngót bê tông (TCVN 11823-5 Điều 5.9.5.3)
        # df_shrinkage = (117 - 1.05 * H) MPa
        df_shrinkage = max(10.0, 117.0 - 1.05 * self.H)

        # 5. Mất mát dài hạn do Từ biến bê tông (TCVN 11823-5 Điều 5.9.5.3)
        # df_creep = 12.0 * fcgp - 7.0 * Delta_f_cdp >= 0
        delta_f_cdp = (abs(M_DC_super) * 1e6 * e_cgp / self.Ig) if self.Ig > 0 else 0.0
        df_creep = max(5.0, 12.0 * fcgp - 7.0 * delta_f_cdp)

        # 6. Mất mát dài hạn do Tự chùng cốt thép DƯL độ tự chùng thấp (TCVN 11823-5 Điều 5.9.5.3)
        # df_relaxation = 0.3 * [20.0 - 0.4*df_elastic - 0.2*(df_shrinkage + df_creep)] >= 0
        df_relaxation = max(5.0, 0.3 * (20.0 - 0.4 * df_elastic - 0.2 * (df_shrinkage + df_creep)))

        total_loss = df_friction + df_anchor + df_elastic + df_shrinkage + df_creep + df_relaxation
        fpe = max(0.0, fpj - total_loss)
        loss_pct = (total_loss / fpj) * 100.0 if fpj > 0 else 0.0

        return PrestressLosses(
            fpj=round(fpj, 2),
            df_friction=round(df_friction, 2),
            df_anchor=round(df_anchor, 2),
            df_elastic=round(df_elastic, 2),
            df_creep=round(df_creep, 2),
            df_shrinkage=round(df_shrinkage, 2),
            df_relaxation=round(df_relaxation, 2),
            fpe=round(fpe, 2),
            loss_percentage=round(loss_pct, 2)
        )

    def check_cap(
        self,
        M_self_weight: float,    # Mô men tự trọng xà mũ M_DC_xm (kN.m)
        M_dead_load_total: float,# Tổng mô men tĩnh tải dầm + bản + xà mũ + lớp phủ (kN.m)
        M_service_total: float,  # Tổng mô men TTGH Sử dụng Service I (kN.m)
        Mu_strength: float,      # Mô men tính toán TTGH Cường độ ULS (kN.m)
        As_rebar: float = 0.0,   # Cốt thép thường chịu kéo kèm theo (mm²)
        As_prime: float = 0.0    # Cốt thép thường chịu nén kèm theo (mm²)
    ) -> PrestressedCapCheckResult:
        """
        Kiểm toán toàn diện xà mũ DƯL qua 7 giai đoạn thi công & khai thác
        từ mô hình phân rã tải trọng cơ học thực tế.
        """
        M_super = max(0.0, M_dead_load_total - M_self_weight)
        losses = self.calculate_losses(
            x_section=self.L_cantilever,
            M_DC_transfer=M_self_weight,
            M_DC_super=M_super
        )
        fpe = losses.fpe
        fpj = losses.fpj
        fc = self.concrete.fc_prime
        fci = 0.80 * fc

        # Phân rã các giai đoạn thi công cơ học thực tế:
        # M_girder ~ 50% M_super, M_deck ~ 35% M_super, M_barrier_wear ~ 15% M_super
        # M_live = M_service_total - M_dead_load_total
        M_live = max(0.0, M_service_total - M_dead_load_total)
        M_girders = M_self_weight + 0.50 * M_super
        M_deck = M_self_weight + 0.85 * M_super
        M_full_dead = M_dead_load_total

        stages_def = [
            (1, "Stage 1: Căng đợt 1 (Transfer)", "TEMP", M_self_weight, [1]),
            (2, "Stage 2: Gác dầm chủ", "TEMP", M_girders, [1]),
            (3, "Stage 3: Căng đợt 2", "TEMP", M_girders, [1, 2, 3]),
            (4, "Stage 4: Đổ bản mặt cầu", "TEMP", M_deck, [1, 2, 3]),
            (5, "Stage 5: Lan can + Lớp phủ (Full DL)", "TEMP", M_full_dead, [1, 2, 3]),
            (6, "Stage 6: Khai thác ngắn hạn (Service I)", "SERVICE", M_service_total, [1, 2, 3]),
            (7, "Stage 7: Dài hạn cuối (Service III)", "SERVICE", M_full_dead + 0.80 * M_live, [1, 2, 3])
        ]

        stage_results: List[ConstructionStageResult] = []

        for st_id, st_name, st_type, M_ext, active_stages in stages_def:
            # Lọc các nhóm cáp đang hoạt động ở giai đoạn này
            active_groups = [g for g in self.tendon_groups if g.tension_stage in active_stages or g.tension_stage <= st_id]
            if not active_groups:
                active_groups = self.tendon_groups

            Aps_act = sum(g.total_area for g in active_groups)
            # Ứng suất cáp: Giai đoạn thi công đầu lấy ứng suất sau mất mát tức thời
            # Giai đoạn dài hạn (Stage 5..7) lấy ứng suất hữu hiệu fpe
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
                M_ext=round(abs(M_ext), 2), Aps_active=round(Aps_act, 2),
                P_active=round(P_act, 2), Mp_active=round(Mp_act, 2),
                sigma_top=round(sig_top, 2), sigma_bot=round(sig_bot, 2),
                allowable_comp=round(allow_c, 2), allowable_tens=round(allow_t, 2),
                passed=st_pass
            ))

        # Tổng kết ứng suất Transfer & Service
        trans_res = stage_results[0]
        serv_res = stage_results[6]

        # 3. Sức kháng uốn ULS (TCVN 11823-5 Điều 5.7.3.2)
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
                  As_prime * fy * max(0.0, (a_depth / 2.0 - 50.0)))
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
            Mu=round(abs(Mu_strength), 2),
            Mr=round(Mr, 2),
            Mn=round(Mn, 2),
            phi=phi,
            flexure_passed=pass_flex,
            demand_capacity_ratio=round(ratio, 4),
            losses=losses,
            stages=stage_results
        )

