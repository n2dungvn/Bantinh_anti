"""
Module: tcvn.fiber
Engine Phân tích Mặt cắt Thớ sợi (Fiber Section Integration) & Biaxial Column Solver (TCVN 11823-5:2017)

Hỗ trợ 2 phương pháp kiểm toán nén - uốn không gian 2 phương (P-Mx-My):
1. FIBER_3D (Exact Angle-Radial Fiber Integration):
   - Tích phân biến dạng thớ sợi thực tế cho bê tông và từng thanh cốt thép
   - Xác định góc mô men tác dụng theta = atan2(Muy, Mux) và bán kính ngoại lực r_demand = sqrt(Mux^2 + Muy^2)
   - Quét trục trung hòa theo góc theta để tìm bán kính sức kháng thực tế r_capacity(Pu, theta)
   - Đảm bảo tỷ số sử dụng utilization = r_demand / r_capacity phản ánh đúng tương tác uốn xiên 2 phương.
2. APPROX_BIAXIAL (Bresler Load Reciprocal / Parme Equation):
   - Phương pháp giải tích xấp xỉ theo đường bao tương tác bề mặt Bresler (TCVN 11823-5 Điều 5.7.4.5)
"""
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
import numpy as np
from .materials import Concrete, Rebar
from .concrete import get_phi_flexure


@dataclass
class RebarLayer:
    """Một lớp cốt thép dọc trong thân trụ"""
    name: str                  # Tên lớp (vd: L1, L2...)
    count: int                 # Số thanh
    diameter: float            # Đường kính thanh (mm)
    area: float                # Tổng diện tích lớp (mm²)
    y: float                   # Tọa độ trọng tâm theo phương Y (dọc cầu) từ tim (mm)
    x: float = 0.0             # Tọa độ trọng tâm theo phương X (ngang cầu) từ tim (mm)


@dataclass
class PMPoint:
    """Một điểm trên biểu đồ tương tác P-M"""
    c: float                   # Chiều cao trục trung hòa (mm)
    Pn: float                  # Sức kháng dọc danh định (kN, nén dương)
    Mn: float                  # Sức kháng mô men danh định (kN.m)
    phi: float                 # Hệ số sức kháng phi
    phiPn: float               # Sức kháng dọc tính toán (kN)
    phiMn: float               # Sức kháng mô men tính toán (kN.m)
    eps_t: float               # Biến dạng thớ thép kéo xa nhất


@dataclass
class BiaxialCheckResult:
    """Kết quả kiểm toán nén - uốn không gian 2 phương (P-Mx-My)"""
    Pu: float                  # Lực nén tính toán ULS (kN)
    Mux: float                 # Mô men tính toán quanh trục X (ngang cầu) (kN.m)
    Muy: float                 # Mô men tính toán quanh trục Y (dọc cầu) (kN.m)
    phiMrx: float              # Sức kháng uốn 1 phương quanh X tại Pu (kN.m)
    phiMry: float              # Sức kháng uốn 1 phương quanh Y tại Pu (kN.m)
    demand_angle_deg: float    # Góc của vector mô men ngoại lực (độ)
    demand_radius: float       # Độ lớn mô men ngoại lực tổng hợp sqrt(Mux^2 + Muy^2) (kN.m)
    capacity_radius: float     # Sức kháng mô men tổng hợp theo phương góc tác dụng (kN.m)
    utilization: float         # Tỷ số sử dụng = demand_radius / capacity_radius
    passed: bool               # Đạt (utilization <= 1.0)
    method: str = "FIBER_3D"   # "FIBER_3D" hoặc "APPROX_BIAXIAL"
    convergence_status: str = "CONVERGED" # "CONVERGED", "BLOCKED", "FAILED"
    assumptions: str = "TCVN 11823-5 Điều 5.7.4 (Strain compatibility fiber integration)"


class FiberSection:
    """
    Mặt cắt bê tông cốt thép phân mảnh thớ sợi (Fiber section)
    """
    def __init__(
        self,
        shape_type: int,       # 0: Chữ nhật; 1: Đầu tròn; 2: Vát góc
        b: float,              # Kích thước phương ngang (mm)
        h: float,              # Kích thước phương dọc (mm)
        concrete: Concrete,    # Bê tông
        rebar: Rebar,          # Thép
        cx: float = 0.0,       # Cạnh vát ngang (mm, cho shape=2)
        cy: float = 0.0,       # Cạnh vát dọc (mm, cho shape=2)
        nx: int = 40,          # Số lượng phân mảnh thớ theo X
        ny: int = 40           # Số lượng phân mảnh thớ theo Y
    ):
        self.shape_type = shape_type
        self.b = b
        self.h = h
        self.concrete = concrete
        self.rebar = rebar
        self.cx = cx
        self.cy = cy
        self.nx = nx
        self.ny = ny

        self.fibers: List[Tuple[float, float, float]] = [] # (x, y, dA)
        self.rebar_layers: List[RebarLayer] = []
        self._discretize_section()

    def _is_inside(self, x: float, y: float) -> bool:
        """Kiểm tra điểm (x, y) nằm trong tiết diện"""
        half_b = self.b / 2.0
        half_h = self.h / 2.0

        if self.shape_type == 0:  # Chữ nhật
            return abs(x) <= half_b and abs(y) <= half_h

        elif self.shape_type == 1:  # Đầu tròn (2 đầu bán nguyệt bán kính R = h/2)
            R = half_h
            rect_half_b = max(0.0, half_b - R)
            if abs(x) <= rect_half_b and abs(y) <= half_h:
                return True
            if x > rect_half_b:
                return (x - rect_half_b) ** 2 + y ** 2 <= R ** 2
            elif x < -rect_half_b:
                return (x + rect_half_b) ** 2 + y ** 2 <= R ** 2
            return False

        elif self.shape_type == 2:  # Vát 4 góc (cx, cy)
            if abs(x) > half_b or abs(y) > half_h:
                return False
            if self.cx > 0 and self.cy > 0:
                dx = abs(x) - (half_b - self.cx)
                dy = abs(y) - (half_h - self.cy)
                if dx > 0 and dy > 0:
                    return (dx / self.cx + dy / self.cy) <= 1.0
            return True

        return abs(x) <= half_b and abs(y) <= half_h

    def _discretize_section(self):
        """Tạo lưới thớ sợi bê tông"""
        self.fibers.clear()
        dx = self.b / self.nx
        dy = self.h / self.ny
        dA_cell = dx * dy

        half_b = self.b / 2.0
        half_h = self.h / 2.0

        for i in range(self.nx):
            x = -half_b + (i + 0.5) * dx
            for j in range(self.ny):
                y = -half_h + (j + 0.5) * dy
                if self._is_inside(x, y):
                    self.fibers.append((x, y, dA_cell))

    def get_gross_area(self) -> float:
        """Diện tích nguyên của mặt cắt Ag (mm²)"""
        if self.shape_type == 0:
            return self.b * self.h
        elif self.shape_type == 1:
            R = self.h / 2.0
            L_mid = max(0.0, self.b - 2.0 * R)
            return L_mid * self.h + math.pi * (R ** 2)
        elif self.shape_type == 2:
            return self.b * self.h - 2.0 * self.cx * self.cy
        return sum(dA for _, _, dA in self.fibers)

    def add_rebar_layer(self, layer: RebarLayer):
        """Thêm một lớp cốt thép"""
        self.rebar_layers.append(layer)

    def generate_pm_curve_at_angle(
        self,
        theta_rad: float,      # Góc phương hướng uốn (rad): 0 = uốn quanh Y (Mx), pi/2 = uốn quanh X (My)
        num_points: int = 30
    ) -> List[PMPoint]:
        """
        Tạo biểu đồ tương tác P-M tổng quát theo một phương góc bất kỳ theta
        bằng phương pháp tích phân thớ sợi 2D.
        """
        fc = self.concrete.fc_prime
        fy = self.rebar.fy
        Es = self.rebar.Es
        beta1 = self.concrete.beta1
        eps_cu = self.concrete.eps_c_max

        cos_t = math.cos(theta_rad)
        sin_t = math.sin(theta_rad)

        # Tính hình chiếu tọa độ các thớ sợi theo phương pháp tuyến trục trung hòa
        p_fibers = [x * cos_t + y * sin_t for x, y, _ in self.fibers]
        p_max = max(p_fibers) if p_fibers else 1000.0
        p_min = min(p_fibers) if p_fibers else -1000.0
        D_theta = max(100.0, p_max - p_min)

        points: List[PMPoint] = []
        c_values = [D_theta * (0.02 + i * (1.8 - 0.02) / (num_points - 1)) for i in range(num_points)]
        c_values.insert(0, 0.005 * D_theta)
        c_values.append(3.5 * D_theta)

        for c in c_values:
            a = min(D_theta, beta1 * c)
            Pn_c = 0.0
            Mn_cx = 0.0
            Mn_cy = 0.0

            for (x_f, y_f, dA), p_f in zip(self.fibers, p_fibers):
                dist_comp = p_max - p_f
                if dist_comp <= a:
                    dF = 0.85 * fc * dA
                    Pn_c += dF
                    Mn_cx += dF * y_f  # Uốn quanh X do lực ở tọa độ y
                    Mn_cy += dF * x_f  # Uốn quanh Y do lực ở tọa độ x

            Pn_s = 0.0
            Mn_sx = 0.0
            Mn_sy = 0.0
            eps_t_max = 0.0

            for layer in self.rebar_layers:
                p_s = layer.x * cos_t + layer.y * sin_t
                dist_comp_s = p_max - p_s
                eps_s = eps_cu * (c - dist_comp_s) / c if c > 0 else 0.0

                if dist_comp_s > c:
                    eps_t = abs(eps_s)
                    if eps_t > eps_t_max:
                        eps_t_max = eps_t

                fs = max(-fy, min(fy, Es * eps_s))
                if dist_comp_s <= a:
                    fs -= 0.85 * fc

                dF_s = fs * layer.area
                Pn_s += dF_s
                Mn_sx += dF_s * layer.y
                Mn_sy += dF_s * layer.x

            Pn_total = (Pn_c + Pn_s) * 1e-3  # kN
            Mn_x_total = (Mn_cx + Mn_sx) * 1e-6  # kN.m
            Mn_y_total = (Mn_cy + Mn_sy) * 1e-6  # kN.m
            Mn_res = math.sqrt(Mn_x_total ** 2 + Mn_y_total ** 2)

            phi = get_phi_flexure(eps_t_max, self.rebar.eps_y)
            phiPn = phi * Pn_total
            phiMn = phi * Mn_res

            points.append(PMPoint(
                c=c,
                Pn=Pn_total,
                Mn=Mn_res,
                phi=phi,
                phiPn=phiPn,
                phiMn=phiMn,
                eps_t=eps_t_max
            ))

        return points

    def generate_pm_curve(
        self,
        axis: str = "Y",       # "Y" (uốn quanh trục X -> mô men dọc My, chiều cao h) hoặc "X" (uốn quanh trục Y -> mô men ngang Mx, chiều cao b)
        num_points: int = 30
    ) -> List[PMPoint]:
        """
        Tạo biểu đồ tương tác P-M 1 phương chính (Tương thích ngược)
        """
        theta = math.pi / 2.0 if axis == "Y" else 0.0
        return self.generate_pm_curve_at_angle(theta_rad=theta, num_points=num_points)

    def _interpolate_phiMn_at_Pu(self, curve: List[PMPoint], Pu: float) -> float:
        """Nội suy tuyến tính mô men kháng phiMn ứng với lực nén Pu trên đường cong P-M"""
        if not curve:
            return 1.0

        sorted_pts = sorted(curve, key=lambda pt: pt.phiPn)
        if Pu <= sorted_pts[0].phiPn:
            return max(0.1, sorted_pts[0].phiMn)
        if Pu >= sorted_pts[-1].phiPn:
            return max(0.1, sorted_pts[-1].phiMn)

        for i in range(len(sorted_pts) - 1):
            p0 = sorted_pts[i]
            p1 = sorted_pts[i+1]
            if p0.phiPn <= Pu <= p1.phiPn:
                if abs(p1.phiPn - p0.phiPn) < 1e-4:
                    return max(0.1, p0.phiMn)
                t = (Pu - p0.phiPn) / (p1.phiPn - p0.phiPn)
                return max(0.1, p0.phiMn + t * (p1.phiMn - p0.phiMn))

        return max(0.1, sorted_pts[-1].phiMn)

    def check_biaxial(
        self,
        Pu: float,             # Lực nén tính toán ULS (kN)
        Mu_x: float,           # Mô men tính toán quanh trục X (ngang cầu) (kN.m)
        Mu_y: float,           # Mô men tính toán quanh trục Y (dọc cầu) (kN.m)
        method: str = "FIBER_3D",
        curve_y: Optional[List[PMPoint]] = None,
        curve_x: Optional[List[PMPoint]] = None
    ) -> BiaxialCheckResult:
        """
        Kiểm toán khả năng chịu lực nén - uốn không gian 2 phương (P-Mx-My) theo FIBER_3D hoặc APPROX_BIAXIAL.
        """
        if curve_y is None:
            curve_y = self.generate_pm_curve(axis="Y")
        if curve_x is None:
            curve_x = self.generate_pm_curve(axis="X")

        phiMry = self._interpolate_phiMn_at_Pu(curve_y, Pu)
        phiMrx = self._interpolate_phiMn_at_Pu(curve_x, Pu)

        demand_radius = math.sqrt(Mu_x ** 2 + Mu_y ** 2)
        theta_demand = math.atan2(abs(Mu_x), abs(Mu_y)) if demand_radius > 1e-4 else 0.0
        theta_deg = math.degrees(theta_demand)

        if demand_radius < 1e-4:
            # Tải nén đúng tâm thuần túy
            return BiaxialCheckResult(
                Pu=Pu, Mux=Mu_x, Muy=Mu_y, phiMrx=phiMrx, phiMry=phiMry,
                demand_angle_deg=0.0, demand_radius=0.0, capacity_radius=max(phiMrx, phiMry),
                utilization=0.0, passed=True, method=method, convergence_status="CONVERGED"
            )

        if method == "FIBER_3D":
            # 1. Phương pháp tích phân thớ sợi trực tiếp theo góc tác dụng theta
            # theta_demand: góc so với trục Y (dọc cầu) -> trong hệ tọa độ: x = r*sin(t), y = r*cos(t)
            # theta trong generate_pm_curve_at_angle: 0 = uốn quanh Y (x), pi/2 = uốn quanh X (y)
            theta_angle = math.atan2(abs(Mu_y), abs(Mu_x))
            curve_theta = self.generate_pm_curve_at_angle(theta_rad=theta_angle, num_points=25)
            capacity_radius = self._interpolate_phiMn_at_Pu(curve_theta, Pu)
            utilization = demand_radius / capacity_radius if capacity_radius > 0 else 999.0
            passed = (utilization <= 1.0)

            return BiaxialCheckResult(
                Pu=Pu, Mux=Mu_x, Muy=Mu_y, phiMrx=phiMrx, phiMry=phiMry,
                demand_angle_deg=round(theta_deg, 2),
                demand_radius=round(demand_radius, 2),
                capacity_radius=round(capacity_radius, 2),
                utilization=round(utilization, 4),
                passed=passed,
                method="FIBER_3D",
                convergence_status="CONVERGED",
                assumptions="Direct fiber-mesh strain compatibility at theta = atan2(Muy, Mux)"
            )
        else:
            # 2. Phương pháp giải tích tương tác bề mặt Bresler (TCVN 11823-5 Điều 5.7.4.5)
            alpha_exp = 1.20
            rx = abs(Mu_x) / phiMrx if phiMrx > 0 else 999.0
            ry = abs(Mu_y) / phiMry if phiMry > 0 else 999.0
            bresler_val = (rx ** alpha_exp) + (ry ** alpha_exp)
            utilization = bresler_val ** (1.0 / alpha_exp)
            passed = (utilization <= 1.0)
            capacity_r = demand_radius / max(1e-4, utilization)

            return BiaxialCheckResult(
                Pu=Pu, Mux=Mu_x, Muy=Mu_y, phiMrx=phiMrx, phiMry=phiMry,
                demand_angle_deg=round(theta_deg, 2),
                demand_radius=round(demand_radius, 2),
                capacity_radius=round(capacity_r, 2),
                utilization=round(utilization, 4),
                passed=passed,
                method="APPROX_BIAXIAL",
                convergence_status="CONVERGED",
                assumptions="Bresler interaction contour equation (alpha = 1.20)"
            )

    def check_demand_capacity(
        self,
        Pu: float,             # Lực nén tính toán ULS (kN)
        Mu_y: float,           # Mô men tính toán theo phương dọc My (kN.m)
        Mu_x: float,           # Mô men tính toán theo phương ngang Mx (kN.m)
        curve_y: Optional[List[PMPoint]] = None,
        curve_x: Optional[List[PMPoint]] = None
    ) -> Tuple[bool, float, float, float]:
        """
        Kiểm toán tương thích ngược: Gọi FIBER_3D Biaxial Solver
        Trả về (passed, phiMry, phiMrx, utilization_ratio)
        """
        res = self.check_biaxial(
            Pu=Pu, Mu_x=Mu_x, Mu_y=Mu_y, method="FIBER_3D",
            curve_y=curve_y, curve_x=curve_x
        )
        return res.passed, res.phiMry, res.phiMrx, res.utilization
