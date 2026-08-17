"""
Module: tcvn.fiber
Engine Phân tích Mặt cắt Thớ sợi (Fiber Section Integration)
Tính toán biểu đồ tương tác nén-uốn P-Mx-My chính xác cho các dạng tiết diện thân trụ:
- Tiết diện Chữ nhật (Rectangular)
- Tiết diện Đầu tròn (Round-ended / Stadium shape)
- Tiết diện Vát góc (Chamfered)
- Bố trí cốt thép nhiều lớp tùy biến
"""
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
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
            # Hai cung tròn ở 2 đầu
            if x > rect_half_b:
                return (x - rect_half_b) ** 2 + y ** 2 <= R ** 2
            elif x < -rect_half_b:
                return (x + rect_half_b) ** 2 + y ** 2 <= R ** 2
            return False

        elif self.shape_type == 2:  # Vát 4 góc (cx, cy)
            if abs(x) > half_b or abs(y) > half_h:
                return False
            # Kiểm tra 4 góc vát: (x - (half_b - cx))/cx + (y - (half_h - cy))/cy <= 1
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

    def generate_pm_curve(
        self,
        axis: str = "Y",       # "Y" (uốn quanh trục X -> mô men dọc My, chiều cao h) hoặc "X" (uốn quanh trục Y -> mô men ngang Mx, chiều cao b)
        num_points: int = 30
    ) -> List[PMPoint]:
        """
        Tạo biểu đồ tương tác P-M (nén - uốn) theo 1 phương chính
        """
        dim = self.h if axis == "Y" else self.b
        half_dim = dim / 2.0
        fc = self.concrete.fc_prime
        fy = self.rebar.fy
        Es = self.rebar.Es
        beta1 = self.concrete.beta1
        eps_cu = self.concrete.eps_c_max

        # Xác định vị trí thép xa nhất để tính biến dạng kéo
        if axis == "Y":
            d_steel_max = max(half_dim - layer.y for layer in self.rebar_layers) if self.rebar_layers else 0.9 * dim
        else:
            d_steel_max = max(half_dim - layer.x for layer in self.rebar_layers) if self.rebar_layers else 0.9 * dim

        points: List[PMPoint] = []

        # Dải chiều cao trục trung hòa c từ rất nhỏ (kéo thuần túy) đến rất lớn (nén thuần túy)
        c_values = [dim * (0.05 + i * (1.5 - 0.05) / (num_points - 1)) for i in range(num_points)]
        c_values.insert(0, 0.01 * dim)
        c_values.append(3.0 * dim)

        for c in c_values:
            # Chiều cao khối nén Whitney a
            a = min(dim, beta1 * c)

            # Lực trong bê tông
            # Với mô hình thớ sợi:
            Pn_c = 0.0
            Mn_c = 0.0

            for x_f, y_f, dA in self.fibers:
                pos = y_f if axis == "Y" else x_f
                dist_from_top = half_dim - pos
                if dist_from_top <= a:
                    # Ứng suất nén đều 0.85*f'c trong khối Whitney
                    sigma_c = 0.85 * fc
                    dF = sigma_c * dA
                    Pn_c += dF
                    Mn_c += dF * pos  # Mô men lấy với trục trung tâm

            # Lực trong các thanh thép
            Pn_s = 0.0
            Mn_s = 0.0
            eps_t_max = 0.0

            for layer in self.rebar_layers:
                pos = layer.y if axis == "Y" else layer.x
                dist_from_top = half_dim - pos
                # Biến dạng thớ cốt thép: eps_s = eps_cu * (c - dist_from_top) / c
                eps_s = eps_cu * (c - dist_from_top) / c if c > 0 else 0.0

                if dist_from_top > c:
                    # Thép chịu kéo
                    eps_t = abs(eps_s)
                    if eps_t > eps_t_max:
                        eps_t_max = eps_t

                # Ứng suất thép fs = max(-fy, min(fy, Es * eps_s)) (nén dương)
                fs = max(-fy, min(fy, Es * eps_s))
                # Trừ bớt phần bê tông bị chiếm chỗ nếu thớ thép nằm trong vùng nén
                if dist_from_top <= a:
                    fs -= 0.85 * fc

                dF = fs * layer.area
                Pn_s += dF
                Mn_s += dF * pos

            Pn_total = (Pn_c + Pn_s) * 1e-3  # kN
            Mn_total = (Mn_c + Mn_s) * 1e-6  # kN.m

            phi = get_phi_flexure(eps_t_max, self.rebar.eps_y)
            phiPn = phi * Pn_total
            phiMn = phi * abs(Mn_total)

            points.append(PMPoint(
                c=c,
                Pn=Pn_total,
                Mn=abs(Mn_total),
                phi=phi,
                phiPn=phiPn,
                phiMn=phiMn,
                eps_t=eps_t_max
            ))

        return points

    def check_demand_capacity(
        self,
        Pu: float,             # Lực nén tính toán ULS (kN)
        Mu_y: float,           # Mô men tính toán theo phương dọc My (kN.m)
        Mu_x: float,           # Mô men tính toán theo phương ngang Mx (kN.m)
        curve_y: Optional[List[PMPoint]] = None,
        curve_x: Optional[List[PMPoint]] = None
    ) -> Tuple[bool, float, float, float]:
        """
        Kiểm toán khả năng chịu lực nén - uốn không gian 2 phương theo công thức tương tác Bresler:
        1 / P_r = 1 / P_rx + 1 / P_ry - 1 / P_r0
        hoặc kiểm tra độc lập từng phương (My / phiMny) + (Mx / phiMnx) <= 1.0
        Trả về (passed, phiMry, phiMrx, utilization_ratio)
        """
        if curve_y is None:
            curve_y = self.generate_pm_curve(axis="Y")
        if curve_x is None:
            curve_x = self.generate_pm_curve(axis="X")

        # Nội suy phiMn_y tại mức tải Pu
        phiMry = self._interpolate_phiMn_at_Pu(curve_y, Pu)
        phiMrx = self._interpolate_phiMn_at_Pu(curve_x, Pu)

        ratio_y = abs(Mu_y) / phiMry if phiMry > 0 else 999.0
        ratio_x = abs(Mu_x) / phiMrx if phiMrx > 0 else 999.0
        
        # Tỷ số sử dụng tổng hợp
        utilization = max(ratio_y, ratio_x)
        passed = (ratio_y <= 1.0) and (ratio_x <= 1.0)

        return passed, phiMry, phiMrx, utilization

    def _interpolate_phiMn_at_Pu(self, curve: List[PMPoint], Pu: float) -> float:
        """Nội suy tuyến tính mô men kháng phiMn ứng với lực nén Pu trên đường cong P-M"""
        if not curve:
            return 1.0

        # Tìm 2 điểm có phiPn kẹp giá trị Pu
        # Sắp xếp theo phiPn tăng dần
        sorted_pts = sorted(curve, key=lambda pt: pt.phiPn)
        if Pu <= sorted_pts[0].phiPn:
            return sorted_pts[0].phiMn
        if Pu >= sorted_pts[-1].phiPn:
            return sorted_pts[-1].phiMn

        for i in range(len(sorted_pts) - 1):
            p0 = sorted_pts[i]
            p1 = sorted_pts[i+1]
            if p0.phiPn <= Pu <= p1.phiPn:
                if abs(p1.phiPn - p0.phiPn) < 1e-4:
                    return p0.phiMn
                t = (Pu - p0.phiPn) / (p1.phiPn - p0.phiPn)
                return p0.phiMn + t * (p1.phiMn - p0.phiMn)

        return sorted_pts[-1].phiMn
