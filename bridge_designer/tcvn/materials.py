"""
Module: tcvn.materials
Đặc trưng vật liệu Bê tông, Cốt thép, Cáp dự ứng lực, Đất đắp và Nước
theo tiêu chuẩn TCVN 11823-2017 (Phần 5: Kết cấu Bê tông, Phần 10: Nền móng).
"""
import math
from dataclasses import dataclass


@dataclass
class Concrete:
    """Đặc trưng vật liệu Bê tông (TCVN 11823-5 Điều 4.2)"""
    fc_prime: float = 30.0     # Cường độ chịu nén f'c (MPa)
    gamma_c: float = 24.5      # Trọng lượng thể tích BTCT (kN/m³)
    K1: float = 1.0            # Hệ số nguồn cốt liệu (Điều 4.2.4: 1.0 cho cốt liệu thông thường)

    @property
    def Ec(self) -> float:
        """
        Mô đun đàn hồi của bê tông Ec (MPa)
        Theo TCVN 11823-5 Điều 4.2.4:
        Ec = 0.043 * gamma_c^1.5 * K1 * sqrt(f'c) (với gamma_c tính bằng kg/m3)
        Theo file Excel: Ec = 0.043 * (gamma_c * 100)^1.5 * K1 * sqrt(f'c)
        với gamma_c = 24.5 kN/m3 -> gamma = 2450 kg/m3 -> Ec ~ 31349.5 MPa
        """
        wc = self.gamma_c * 100.0
        return 0.043 * (wc ** 1.5) * self.K1 * math.sqrt(self.fc_prime)

    @property
    def fr(self) -> float:
        """
        Cường độ chịu kéo khi uốn fr (MPa)
        Theo TCVN 11823-5 Điều 4.2.6: fr = 0.63 * sqrt(f'c)
        """
        return 0.63 * math.sqrt(self.fc_prime)

    @property
    def beta1(self) -> float:
        """
        Hệ số phân bố ứng suất nén beta1 (TCVN 11823-5 Điều 7.2.2)
        beta1 = 0.85 với f'c <= 28 MPa, giảm 0.05 cho mỗi 7 MPa vượt quá 28 MPa, beta1 >= 0.65
        """
        if self.fc_prime <= 28.0:
            return 0.85
        b1 = 0.85 - 0.05 * (self.fc_prime - 28.0) / 7.0
        return max(0.65, min(0.85, b1))

    @property
    def eps_c_max(self) -> float:
        """Biến dạng nén giới hạn của bê tông eps_cu = 0.003 (Điều 7.2.1)"""
        return 0.003

    @property
    def eps_cu(self) -> float:
        """Biến dạng nén giới hạn của bê tông eps_cu = 0.003 (Điều 7.2.1)"""
        return 0.003


@dataclass
class Rebar:
    """Đặc trưng Cốt thép thường (TCVN 11823-5 Điều 4.3)"""
    fy: float = 400.0          # Giới hạn chảy fy (MPa)
    Es: float = 200000.0       # Mô đun đàn hồi Es (MPa)

    @property
    def eps_y(self) -> float:
        """Biến dạng chảy của cốt thép eps_y = fy / Es"""
        return self.fy / self.Es


@dataclass
class PrestressStrand:
    """Đặc trưng Cáp DƯL (TCVN 11823-5 Điều 4.4)"""
    fpu: float = 1860.0        # Giới hạn bền kéo tiêu chuẩn của cáp fpu (MPa)
    fpy: float = 1674.0        # Giới hạn chảy fpy = 0.90 * fpu (MPa)
    Ep: float = 197000.0       # Mô đun đàn hồi Ep (MPa)
    area_per_strand: float = 140.0 # Diện tích 1 tao cáp 15.2mm / 12.7mm (mm²)
    kfpj: float = 0.75         # Ứng suất kéo căng danh định f_pj = kfpj * fpu


@dataclass
class Soil:
    """Đặc trưng Đất đắp sau mố (TCVN 11823-3 Điều 5 & Phần 11)"""
    gamma_s: float = 19.25     # Trọng lượng thể tích đất đắp (kN/m³)
    phi: float = 30.0          # Góc ma sát trong hữu hiệu phi' (độ)
    delta: float = 0.0         # Góc ma sát đất - lưng tường (độ, delta=0 thiên về an toàn)
    beta: float = 0.0          # Góc dốc mặt đất sau tường (độ)
    theta: float = 90.0        # Góc nghiêng lưng tường so với phương ngang (độ, 90 = tường đứng)

    @property
    def Ka(self) -> float:
        """
        Hệ số áp lực đất chủ động Ka theo Coulomb (TCVN 11823-3 Điều 5.5.1)
        Ka = sin²(theta + phi) / [ sin²(theta) * sin(theta - delta) * (1 + sqrt( sin(phi+delta)*sin(phi-beta)/(sin(theta-delta)*sin(theta+beta)) ))² ]
        Khi theta=90, delta=0, beta=0: Ka = (1 - sin phi)/(1 + sin phi) = tan²(45 - phi/2)
        """
        phi_r = math.radians(self.phi)
        delta_r = math.radians(self.delta)
        beta_r = math.radians(self.beta)
        theta_r = math.radians(self.theta)

        num = math.sin(theta_r + phi_r) ** 2
        den1 = (math.sin(theta_r) ** 2) * math.sin(theta_r - delta_r)
        
        term = math.sin(phi_r + delta_r) * math.sin(phi_r - beta_r) / (math.sin(theta_r - delta_r) * math.sin(theta_r + beta_r))
        if term < 0:
            term = 0
        den2 = (1.0 + math.sqrt(term)) ** 2

        return num / (den1 * den2)

    @property
    def Kp(self) -> float:
        """Hệ số áp lực đất bị động Kp theo Rankine / Coulomb"""
        phi_r = math.radians(self.phi)
        return (1.0 + math.sin(phi_r)) / (1.0 - math.sin(phi_r))


@dataclass
class Water:
    """Đặc trưng Nước (TCVN 11823-3 Điều 7)"""
    gamma_w: float = 10.0      # Trọng lượng thể tích nước (kN/m³)
