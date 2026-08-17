from __future__ import annotations
import math
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

PA_MPA = 0.101
GAMMA_W_KN_M3 = 9.81
# QA fix P4: trọng lượng bản thân là tải CÓ LỢI khi kiểm nhổ -> nhân γDC = 0.9 theo LRFD.
GAMMA_DC_UPLIFT = 0.90

# Hệ số sức kháng mặc định, lấy theo các giá trị đang dùng trong bảng Excel mẫu và Bảng hệ số TCVN/AASHTO.
PHI_BORE_SHAFT_CLAY = 0.45
PHI_BORE_SHAFT_SAND = 0.55
PHI_BORE_SHAFT_IGM = 0.60
PHI_BORE_SHAFT_IGM_SPT_LT100 = 0.70
PHI_BORE_SHAFT_IGM_SPT_GE100 = 0.60
PHI_BORE_TIP_CLAY = 0.40
PHI_BORE_TIP_SAND = 0.50
PHI_BORE_TIP_IGM = PHI_BORE_SHAFT_IGM_SPT_GE100  # legacy/default; mũi IGM thực tế lấy theo N60 như thân: N<100=0.70, N>=100=0.60
PHI_ROCK_SIDE = 0.55
PHI_ROCK_TIP = 0.50
PHI_DRIVEN_SHAFT_CLAY = 0.35
PHI_DRIVEN_SHAFT_SAND = 0.30
PHI_DRIVEN_TIP_CLAY = 0.35
PHI_DRIVEN_TIP_SAND = 0.30

# Hệ số sức kháng nhổ tách riêng, không dùng nhầm hệ số nén.
# Các giá trị mặc định đặt theo hướng bảo thủ để đối chiếu TVQT/TCVN/AASHTO theo từng dự án.
PHI_UPLIFT_BORE_CLAY = 0.35
PHI_UPLIFT_BORE_SAND = 0.45
PHI_UPLIFT_BORE_IGM = 0.45
PHI_UPLIFT_ROCK_SIDE = 0.40
PHI_UPLIFT_DRIVEN_CLAY = 0.25
PHI_UPLIFT_DRIVEN_SAND = 0.25
PHI_EXTREME_UPLIFT_DEFAULT = 0.80

# Cọc đóng đất rời - Meyerhof SPT theo TCVN 11823-10:2017.
# qp = 0.038*N160*(Db/D) MPa, qλ = 0.4*N160 MPa đối với cát, 0.3*N160 MPa đối với cát bột không pha sét.
DRIVEN_SAND_SIDE_DISPLACEMENT_KPA_PER_N = 1.9
DRIVEN_SAND_SIDE_NONDISPLACEMENT_KPA_PER_N = 0.96

# Hệ số tải trọng ma sát âm DD theo TCVN 11823-3, Bảng 4.
# Dùng giá trị lớn nhất khi DD là tác dụng bất lợi trong kiểm toán nén cọc.
GAMMA_DD_TOMLINSON = 1.40
GAMMA_DD_LAMBDA = 1.05
GAMMA_DD_ONEILL_REESE = 1.25

LIMIT_STATE_STRENGTH = "CĐ"
LIMIT_STATE_EXTREME = "ĐB"
LIMIT_STATE_LABELS = {
    LIMIT_STATE_STRENGTH: "TTGHCĐ - Cường độ",
    LIMIT_STATE_EXTREME: "TTGHĐB - Đặc biệt",
}

# Hệ số TTGHĐB trong file TVQT đang lấy 1.0 cho sức kháng bên/mũi đất sét, đất cát và đá.
# Với IGM/cọc đóng, V0.1.4 cũng tách trạng thái riêng và mặc định TTGHĐB = 1.0 để tránh dùng nhầm hệ số TTGHCĐ.
PHI_EXTREME_DEFAULT = 1.00

SOIL_TYPE_LABELS = {
    0: "Không khí/Hang karst",
    1: "Cát/đất rời",
    2: "Sét/đất dính",
    3: "Đá nguyên khối",
    4: "Đá nứt vỡ/phong hóa",
    5: "IGM/đá mềm",
    6: "Cuội sỏi/đất rời",
}

PILE_MODE_CHOICES = [
    "Cọc khoan trong đất",
    "Cọc đóng",
    "Cọc khoan trong đá",
]

# Theme fallback, đồng bộ key với n2d_theme_library.py nếu file đó đặt cùng thư mục.
DEFAULT_THEME = {
    "bg": "#F6FBFF", "panel": "#FFFFFF", "sidebar": "#1D4ED8", "sidebar2": "#93C5FD",
    "accent": "#2563EB", "accent_dark": "#1D4ED8", "text": "#0F172A", "muted": "#475569",
    "button": "#E0F2FE", "button_active": "#BAE6FD", "big_button": "#DBEAFE",
    "tree_head": "#E0F2FE", "tree_row": "#FFFFFF", "tree_alt": "#F8FAFC", "tree_fg": "#0F172A",
    "progress": "#22C55E", "trough": "#DCFCE7", "border": "#93C5FD", "entry_bg": "white", "entry_fg": "black", "note": "#EFF6FF",
}

try:
    from n2d_theme_library import THEME_PRESETS as _N2D_THEME_PRESETS, UI_THEME_LABELS as _N2D_THEME_LABELS, normalize_ui_theme as _normalize_ui_theme
except Exception:
    _N2D_THEME_PRESETS = {"CLEAN_LIGHT": DEFAULT_THEME}
    _N2D_THEME_LABELS = {"CLEAN_LIGHT": "Clean Light / Material - sáng tối giản"}
    def _normalize_ui_theme(value: Any = "") -> str:
        return "CLEAN_LIGHT"


BOREHOLE_OCR_ENGINE_LABELS = {
    "TESSERACT": "Tesseract/OpenCV (mặc định)",
    # QA-OCR v4: RapidOCR đọc chữ nhỏ tốt hơn Tesseract nhưng CHẬM trên CPU khi gọi đại trà
    # theo từng crop. Chỉ nên bật thử nghiệm/cứu ảnh khó; pipeline chính mặc định là Tesseract.
    "RAPID": "RapidOCR (thử nghiệm - chậm, chỉ dùng cứu ảnh khó)",
    "PADDLE": "PaddleOCR/OpenCV (thử nghiệm)",
}

def _normalize_borehole_ocr_engine(value: Any = "") -> str:
    txt = str(value or "").strip().upper()
    if "RAPID" in txt:
        return "RAPID"
    if "PADDLE" in txt:
        return "PADDLE"
    return "TESSERACT"


def _normalize_item_name(value: Any) -> str:
    """Chuẩn hóa tên hạng mục để khớp giữa bảng thông tin riêng và bảng địa chất.

    Mục tiêu là tránh lỗi do dấu tiếng Việt, khoảng trắng kép, dấu gạch, ký tự NBSP...
    Ví dụ: "Trụ T2", "Tru  T2", "TRỤ-T2" đều có cùng key "trut2".
    Không tự map T2 sang Trụ T2 nếu không trùng key để tránh dùng nhầm địa chất.
    """
    text = str(value or "").strip().replace("\u00a0", " ")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def safe_filename(name: Any, default: str = "HANG_MUC") -> str:
    """Làm sạch tên file Windows/Linux để dùng cho báo cáo, tránh lỗi ký tự cấm."""
    s = str(name or default).strip()
    bad = '<>:"/\\|?*\n\r\t'
    for ch in bad:
        s = s.replace(ch, "_")
    s = "_".join(s.split())
    return (s[:120] or default)


PILE_TYPE_CODE_LABELS = {
    "1": "Cọc khoan nhồi",
    "2": "Cọc đóng",
    "3": "Cọc ép",
    # QA fix P1: thêm lựa chọn tiết diện cọc đóng/ép. Mã 2/3 giữ nguyên nghĩa cũ = cọc VUÔNG đặc.
    "2T": "Cọc đóng tròn",
    "3T": "Cọc ép tròn",
    "2O": "Cọc đóng ống",
    "3O": "Cọc ép ống",
}


def normalize_pile_type_choice(value: Any) -> str:
    """Đọc loại cọc từ mã ngắn hoặc chuỗi cũ.

    Bảng nhập liệu dùng mã để gõ nhanh:
    1 = Cọc khoan nhồi; 2 = Cọc đóng vuông; 3 = Cọc ép vuông;
    2T/3T = Cọc đóng/ép tròn đặc; 2O/3O = Cọc đóng/ép ống (PHC), cột Ds = đường kính trong.
    Vẫn hỗ trợ template cũ ghi nguyên cụm chữ để không làm hỏng dữ liệu cũ.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    key = raw.replace(",", ".")
    try:
        f = float(key)
        if abs(f - round(f)) < 1e-9:
            key = str(int(round(f)))
    except Exception:
        pass
    key = key.strip().upper()
    if key in PILE_TYPE_CODE_LABELS:
        return PILE_TYPE_CODE_LABELS[key]
    low = _strip_accents(raw).lower()
    is_ong = (" ong" in f" {low}") or ("phc" in low)
    is_tron = "tron" in low
    if "ep" in low:
        if is_ong:
            return "Cọc ép ống"
        if is_tron:
            return "Cọc ép tròn"
        return "Cọc ép"
    if "dong" in low:
        if is_ong:
            return "Cọc đóng ống"
        if is_tron:
            return "Cọc đóng tròn"
        return "Cọc đóng"
    if "khoan" in low or "nhồi" in raw.lower() or "nhoi" in low:
        return "Cọc khoan nhồi"
    return raw


def pile_type_to_input_code(value: Any) -> str:
    """Đổi loại cọc về mã 1/2/3 để ghi vào bảng nhập liệu khi biết chắc loại cọc."""
    label = normalize_pile_type_choice(value)
    for code, name in PILE_TYPE_CODE_LABELS.items():
        if _normalize_item_name(label) == _normalize_item_name(name):
            return code
    return str(value or "").strip()



# ==========================================
# LICENSE DÙNG CHUNG TS-PILE / TS-COL / TS-CAP
# ==========================================
SECRET_SALT = "Dung_Dev_Security_Key_2026!@#"
API_URL = "https://script.google.com/macros/s/AKfycbyzL6t1TROfT5LqTkZ_D0LkMZ4K50aKNBzfHg3-_XIYddToVyjGkBc_WfU7gaa0wuzMbA/exec"

LICENSE_RUNTIME_INFO = {
    "machine_id": "",
    "is_active": False,
    "days_left": None,
    "checked_at": "",
    "message": "",
    "reason": "",
}

def _format_days_left(days_left: Any) -> str:
    try:
        d = int(float(days_left))
        if d < 0:
            return "0 ngày"
        return f"{d} ngày"
    except Exception:
        return "Không xác định"

# ==========================================
# QA fix R1/R3: cache kích hoạt để chạy offline có thời hạn + ổn định machine-id
# ==========================================
LICENSE_OFFLINE_GRACE_DAYS = 14

def _n2d_license_dir() -> str:
    base = os.path.join(os.path.expanduser("~"), ".n2d_license")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return base

def _license_cache_path() -> str:
    return os.path.join(_n2d_license_dir(), "ts_suite_license.json")

def _machine_id_store_path() -> str:
    return os.path.join(_n2d_license_dir(), "machine_id.txt")

def _offline_trial_path():
    return os.path.join(_n2d_license_dir(), "ts_suite_offline_trial.json")

def _offline_trial_sig(machine_id, day):
    return hashlib.sha256(f"{machine_id}|{day}|OFFLINE_TRIAL|{SECRET_SALT}".encode("utf-8")).hexdigest()

def _offline_trial_save(machine_id, day=None):
    try:
        if day is None:
            day = datetime.now().strftime("%Y-%m-%d")
        data = {"machine_id": str(machine_id), "start_day": str(day),
                "sig": _offline_trial_sig(machine_id, day)}
        with open(_offline_trial_path(), "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return True
    except Exception:
        return False

def _offline_trial_load(machine_id):
    try:
        with open(_offline_trial_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if str(data.get("machine_id", "")) != str(machine_id):
            return None
        day = str(data.get("start_day", ""))
        if str(data.get("sig", "")) != _offline_trial_sig(machine_id, day):
            return None
        return day
    except Exception:
        return None

def _offline_trial_check(machine_id):
    """Trả (được chạy?, ngày offline còn lại). Nếu chưa có file trial thì tạo mới."""
    day = _offline_trial_load(machine_id)
    if not day:
        today = datetime.now().strftime("%Y-%m-%d")
        if _offline_trial_save(machine_id, today):
            return True, LICENSE_OFFLINE_GRACE_DAYS
        return False, 0
    try:
        start = datetime.strptime(day, "%Y-%m-%d")
        delta = (datetime.now() - start).days
        if delta < 0:
            return False, 0
        remain = max(LICENSE_OFFLINE_GRACE_DAYS - delta, 0)
        return remain > 0, remain
    except Exception:
        return False, 0

def _license_cache_sig(machine_id: str, day: str, days_left: Any) -> str:
    return hashlib.sha256(f"{machine_id}|{day}|{days_left}|{SECRET_SALT}".encode("utf-8")).hexdigest()

def _license_cache_save(machine_id: str, days_left: Any) -> None:
    try:
        day = datetime.now().strftime("%Y-%m-%d")
        data = {"machine_id": str(machine_id), "last_ok": day, "days_left": days_left,
                "sig": _license_cache_sig(machine_id, day, days_left)}
        with open(_license_cache_path(), "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except Exception:
        pass

def _license_cache_clear() -> None:
    try:
        os.remove(_license_cache_path())
    except Exception:
        pass

def _license_offline_check(machine_id):
    """Trả (được chạy offline?, ngày bản quyền còn lại, ngày offline còn lại).

    14 ngày chỉ là giới hạn chạy offline. Giá trị trả về cho GUI/app vẫn là
    số ngày bản quyền ước tính còn lại từ lần server xác nhận gần nhất.
    """
    try:
        with open(_license_cache_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if str(data.get("machine_id", "")) != str(machine_id):
            return False, 0, 0
        day = str(data.get("last_ok", ""))
        if str(data.get("sig", "")) != _license_cache_sig(machine_id, day, data.get("days_left")):
            return False, 0, 0
        last = datetime.strptime(day, "%Y-%m-%d")
        delta = (datetime.now() - last).days
        if delta < 0:
            return False, 0, 0
        cached_days = int(float(data.get("days_left")))
        license_remaining = max(cached_days - delta, 0)
        offline_remaining = max(LICENSE_OFFLINE_GRACE_DAYS - delta, 0)
        ok = (cached_days - delta) > 0 and offline_remaining > 0
        return ok, license_remaining, offline_remaining
    except Exception:
        return False, 0, 0

def get_machine_id() -> str:
    'Lấy mã máy theo đúng cách TS-PILE/TS-COL để dùng chung license.'
    hwid = ""
    errors = []
    if platform.system() == "Windows":
        for cmd in (
            'powershell "(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID"',
            'wmic csproduct get uuid',
        ):
            try:
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, **_no_window_kwargs()).decode(errors="ignore").strip()
                if "wmic" in cmd.lower():
                    parts = [line.strip() for line in out.splitlines() if line.strip() and "uuid" not in line.lower()]
                    out = parts[0] if parts else ""
                if out:
                    hwid = out
                    break
            except Exception as exc:
                errors.append(str(exc))
    if hwid:
        mid = hashlib.sha256((str(hwid) + SECRET_SALT).encode()).hexdigest()
        try:
            with open(_machine_id_store_path(), "w", encoding="utf-8") as fh:
                fh.write(mid)
        except Exception:
            pass
        return mid
    # QA fix R3: dùng machine-id đã lưu trước khi rơi về fallback MAC, tránh lệch máy đã kích hoạt.
    try:
        with open(_machine_id_store_path(), "r", encoding="utf-8") as fh:
            stored = fh.read().strip()
        if stored:
            return stored
    except Exception:
        pass
    node = platform.node() or "unknown-node"
    mac = uuid.getnode()
    hwid = f"{platform.system()}|{node}|{mac}|{platform.machine()}"
    return hashlib.sha256((str(hwid) + SECRET_SALT).encode()).hexdigest()

def check_server_trial() -> Tuple[bool, Any]:
    machine_id = get_machine_id()
    LICENSE_RUNTIME_INFO["machine_id"] = machine_id
    LICENSE_RUNTIME_INFO["checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        import requests
        response = requests.post(API_URL, json={"machine_id": machine_id}, timeout=8)
        data = response.json()
        status = str(data.get("status", "")).strip().lower()
        if status == "active":
            days_left = data.get("days_left")
            _license_cache_save(machine_id, days_left)
            LICENSE_RUNTIME_INFO.update({
                "is_active": True,
                "days_left": days_left,
                "reason": "active",
                "message": str(data.get("message", "License active") or "License active"),
            })
            return True, days_left
        inactive_statuses = {"expired", "inactive", "revoked", "not_found", "blocked", "disabled", "not_active", "not-active", "unregistered"}
        if status in inactive_statuses:
            _license_cache_clear()
            LICENSE_RUNTIME_INFO.update({
                "is_active": False,
                "days_left": 0,
                "reason": "expired",
                "message": str(data.get("message", "Hết hạn hoặc chưa kích hoạt") or "Hết hạn hoặc chưa kích hoạt"),
            })
            return False, 0
        raise RuntimeError(f"Phản hồi license không hợp lệ: status={status or 'missing'}")
    except Exception:
        ok_offline, license_days, offline_days = _license_offline_check(machine_id)
        if ok_offline:
            LICENSE_RUNTIME_INFO.update({
                "is_active": True,
                "days_left": license_days,
                "reason": "offline",
                "message": f"Không kết nối được máy chủ bản quyền; đang chạy chế độ offline (còn {offline_days} ngày offline).",
            })
            return True, license_days
        ok_trial, trial_days = _offline_trial_check(machine_id)
        if ok_trial:
            LICENSE_RUNTIME_INFO.update({
                "is_active": True,
                "days_left": trial_days,
                "reason": "offline_trial",
                "message": f"Không kiểm tra được online; đang chạy offline lần đầu (còn {trial_days} ngày).",
            })
            return True, trial_days
        LICENSE_RUNTIME_INFO.update({
            "is_active": False,
            "days_left": 0,
            "reason": "offline_trial_expired",
            "message": "Không kiểm tra được bản quyền online và đã quá 14 ngày dùng offline kể từ lần mở đầu tiên. Vui lòng kết nối mạng rồi mở lại phần mềm.",
        })
        return False, 0

def _notify_license_blocked() -> None:
    """Hiện thông báo chặn theo đúng lý do (hết hạn vs lỗi mạng) trong LICENSE_RUNTIME_INFO."""
    if str(LICENSE_RUNTIME_INFO.get("reason", "")) in ("network", "offline_trial_expired"):
        title = "Không kiểm tra được bản quyền"
        body = (LICENSE_RUNTIME_INFO.get("message") or
                "Không kết nối được máy chủ bản quyền. Vui lòng kết nối mạng rồi mở lại phần mềm.")
    else:
        title = "Hết hạn"
        body = "Hết thời gian sử dụng hoặc chưa kích hoạt bản quyền."
    try:
        root_hidden = tk.Tk()
        root_hidden.withdraw()
        messagebox.showerror(title, body)
        root_hidden.destroy()
    except Exception:
        pass


def security_check_or_exit() -> Any:
    'Chặn TS-CAP nếu license chung không còn hợp lệ.'
    ok, days_left = check_server_trial()
    if not ok:
        _notify_license_blocked()
        sys.exit()
    return days_left

def _strip_accents(value: Any) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")

def _display_item_name(value: Any) -> str:
    return str(value or "").strip().replace("\u00a0", " ")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        s = str(value).strip().replace("\u00a0", "").replace(",", ".")
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(_safe_float(value, default)))
    except Exception:
        return default


def _fmt(x: Any, nd: int = 3) -> str:
    try:
        if x is None:
            return ""
        v = float(x)
        if abs(v) < 1e-12:
            v = 0.0
        if int(nd) <= 0:
            return f"{v:.0f}"
        return f"{v:.{nd}f}".rstrip("0").rstrip(".")
    except Exception:
        return str(x or "")


def linear_interp(x: float, xs: List[float], ys: List[float], clamp: bool = True) -> float:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0
    pairs = sorted((float(a), float(b)) for a, b in zip(xs, ys))
    xs2 = [p[0] for p in pairs]
    ys2 = [p[1] for p in pairs]
    x = float(x)
    if x <= xs2[0]:
        if clamp or len(xs2) == 1:
            return ys2[0]
    if x >= xs2[-1]:
        if clamp or len(xs2) == 1:
            return ys2[-1]
    for i in range(len(xs2) - 1):
        if xs2[i] <= x <= xs2[i + 1]:
            den = xs2[i + 1] - xs2[i]
            if abs(den) < 1e-12:
                return ys2[i]
            t = (x - xs2[i]) / den
            return ys2[i] + t * (ys2[i + 1] - ys2[i])
    # extrapolate if requested
    if x < xs2[0]:
        den = xs2[1] - xs2[0]
        return ys2[0] + (x - xs2[0]) * (ys2[1] - ys2[0]) / den if abs(den) > 1e-12 else ys2[0]
    den = xs2[-1] - xs2[-2]
    return ys2[-1] + (x - xs2[-1]) * (ys2[-1] - ys2[-2]) / den if abs(den) > 1e-12 else ys2[-1]


def bilinear_interp(x: float, y: float, xs: List[float], ys: List[float], grid: List[List[float]]) -> float:
    """Nội suy song tuyến tính cho các bảng dạng Excel NoisuyMatran."""
    if not xs or not ys or not grid:
        return 0.0
    xs = [float(v) for v in xs]
    ys = [float(v) for v in ys]
    x = max(min(float(x), max(xs)), min(xs))
    y = max(min(float(y), max(ys)), min(ys))

    def bracket(v, arr):
        arr2 = sorted(arr)
        if v <= arr2[0]:
            return arr.index(arr2[0]), arr.index(arr2[0])
        if v >= arr2[-1]:
            return arr.index(arr2[-1]), arr.index(arr2[-1])
        for i in range(len(arr2) - 1):
            if arr2[i] <= v <= arr2[i + 1]:
                return arr.index(arr2[i]), arr.index(arr2[i + 1])
        return 0, 0

    ix0, ix1 = bracket(x, xs)
    iy0, iy1 = bracket(y, ys)
    x0, x1 = xs[ix0], xs[ix1]
    y0, y1 = ys[iy0], ys[iy1]
    q11 = float(grid[iy0][ix0])
    q21 = float(grid[iy0][ix1])
    q12 = float(grid[iy1][ix0])
    q22 = float(grid[iy1][ix1])
    if ix0 == ix1 and iy0 == iy1:
        return q11
    if ix0 == ix1:
        return linear_interp(y, [y0, y1], [q11, q12])
    if iy0 == iy1:
        return linear_interp(x, [x0, x1], [q11, q21])
    tx = (x - x0) / max(x1 - x0, 1e-12)
    ty = (y - y0) / max(y1 - y0, 1e-12)
    return (q11 * (1 - tx) * (1 - ty) + q21 * tx * (1 - ty) + q12 * (1 - tx) * ty + q22 * tx * ty)


def alpha_clay_bored(su_mpa: float) -> float:
    """Hệ số alpha cho cọc khoan trong đất dính theo Excel TVQT/TCVN.

    TVQT dùng:
    - alpha = 0.55 khi Su/pa <= 1.5
    - alpha = 0.55 - 0.1*(Su/pa - 1.5) khi 1.5 < Su/pa <= 2.5
    - ngoài miền này bảng Excel trả "unknown"; trong tool vẫn kẹp alpha=0.45
      và sinh cảnh báo ở bước tính lớp để không làm gián đoạn batch.
    """
    su = max(float(su_mpa), 0.0)
    ratio = su / PA_MPA if PA_MPA > 0 else 0.0
    if ratio <= 1.5:
        return 0.55
    return max(0.45, 0.55 - 0.1 * (ratio - 1.5))


def clay_alpha_domain_warning(layer_name: str, su_mpa: float) -> str:
    """Trả cảnh báo nếu Su/pa vượt miền bảng TVQT."""
    ratio = max(float(su_mpa), 0.0) / PA_MPA if PA_MPA > 0 else 0.0
    if ratio > 2.5:
        return f"Lớp {layer_name}: Su/pa={ratio:.2f} > 2.5; ngoài miền bảng α, lấy α=0.45."
    return ""


# Bảng α Tomlinson cho cọc đóng/ép trong đất dính theo quy trình TCVN/AASHTO.
# Hàng là Su (MPa), cột là Db/D. Dữ liệu nhập từ bảng quy trình người dùng cung cấp.
_TOMLINSON_DB_OVER_D = [0.0, 10.0, 20.0, 40.0, 100.0]
_TOMLINSON_SU_MPA = [0.0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20, 1.0]
_TOMLINSON_ALPHA_TABLES = {
    "sand_gravel": [
        [1.00, 1.00, 1.00, 1.00, 1.00],
        [1.00, 1.00, 1.00, 1.00, 1.00],
        [1.00, 1.00, 1.00, 0.95, 0.95],
        [1.00, 1.00, 1.00, 0.84, 0.84],
        [1.00, 1.00, 0.94, 0.67, 0.67],
        [1.00, 1.00, 0.82, 0.50, 0.50],
        [1.00, 1.00, 0.74, 0.40, 0.40],
        [1.00, 1.00, 0.74, 0.40, 0.40],
        [1.00, 1.00, 0.74, 0.40, 0.40],
        [1.00, 1.00, 0.74, 0.40, 0.40],
    ],
    "soft_clay": [
        [0.55, 0.55, 0.85, 0.85, 0.85],
        [0.55, 0.55, 0.85, 0.85, 0.85],
        [0.40, 0.40, 0.76, 0.76, 0.76],
        [0.34, 0.34, 0.71, 0.71, 0.71],
        [0.29, 0.29, 0.69, 0.69, 0.69],
        [0.26, 0.26, 0.66, 0.66, 0.66],
        [0.25, 0.25, 0.64, 0.64, 0.64],
        [0.23, 0.23, 0.61, 0.61, 0.61],
        [0.20, 0.20, 0.57, 0.57, 0.57],
        [0.15, 0.15, 0.50, 0.50, 0.50],
    ],
    "stiff_clay": [
        [1.00, 1.00, 1.00, 1.00, 1.00],
        [1.00, 1.00, 1.00, 1.00, 1.00],
        [0.94, 0.94, 0.97, 1.00, 1.00],
        [0.85, 0.85, 0.925, 1.00, 1.00],
        [0.66, 0.66, 0.77, 0.88, 0.88],
        [0.42, 0.42, 0.555, 0.69, 0.69],
        [0.29, 0.29, 0.375, 0.46, 0.46],
        [0.24, 0.24, 0.295, 0.35, 0.35],
        [0.20, 0.20, 0.25, 0.30, 0.30],
        [0.20, 0.20, 0.24, 0.28, 0.28],
    ],
}
_TOMLINSON_CASE_LABELS = {
    "sand_gravel": "lớp trên là cát/cát cuội",
    "soft_clay": "lớp trên là sét mềm",
    "stiff_clay": "lớp trên là sét nửa cứng đến cứng",
    "clay_worst": "lớp trên là sét; chọn bảng bất lợi theo SPT/Su",
}


def alpha_clay_driven_tomlinson(su_mpa: float, db_over_d: float = 0.0, cover_case: str = "stiff_clay") -> float:
    """Hệ số α Tomlinson cho cọc đóng/ép trong đất dính."""
    case = str(cover_case or "stiff_clay").strip().lower()
    su = max(float(su_mpa or 0.0), 0.0)
    x = max(float(db_over_d or 0.0), 0.0)
    if case == "clay_worst":
        a_soft = bilinear_interp(x, su, _TOMLINSON_DB_OVER_D, _TOMLINSON_SU_MPA, _TOMLINSON_ALPHA_TABLES["soft_clay"])
        a_stiff = bilinear_interp(x, su, _TOMLINSON_DB_OVER_D, _TOMLINSON_SU_MPA, _TOMLINSON_ALPHA_TABLES["stiff_clay"])
        return min(a_soft, a_stiff)
    if case not in _TOMLINSON_ALPHA_TABLES:
        case = "stiff_clay"
    return bilinear_interp(x, su, _TOMLINSON_DB_OVER_D, _TOMLINSON_SU_MPA, _TOMLINSON_ALPHA_TABLES[case])


def _is_nondisplacement_driven_pile(pile_type: str = "") -> bool:
    """Cọc không chiếm chỗ: cọc H, cọc ống mũi hở/thành mỏng không tạo nút đất."""
    txt = _strip_accents(pile_type).lower()
    keys = ["khong chiem cho", "khong tao nut", "mui ho", "open end", "open-end", "non-displacement", "nondisplacement"]
    return any(k in txt for k in keys) or re.search(r"\bcoc\s*h\b", txt) is not None


def driven_sand_side_nominal_kpa(n160: float, pile_type: str = "") -> Tuple[float, str]:
    """Ma sát bên danh định cọc đóng/ép trong đất rời theo Meyerhof SPT."""
    factor = DRIVEN_SAND_SIDE_NONDISPLACEMENT_KPA_PER_N if _is_nondisplacement_driven_pile(pile_type) else DRIVEN_SAND_SIDE_DISPLACEMENT_KPA_PER_N
    return max(factor * max(float(n160), 0.0), 0.0), f"Cọc đóng/ép đất rời Meyerhof: qs={factor:.2f}·N160 kPa"


def _driven_sand_tip_limit_case(text: Any = "") -> str:
    plain = _strip_accents(text).lower()
    if any(k in plain for k in ("cat bot", "cat bui", "bui", "bot", "silt", "silty", "ml")):
        return "silty_sand"
    return "sand"


def driven_sand_tip_nominal_kpa(n160: float, db_over_d: float, soil_text: Any = "") -> Tuple[float, Dict[str, float], str]:
    """Sức kháng mũi danh định cọc đóng/ép trong đất rời theo Meyerhof SPT."""
    n = max(float(n160), 0.0)
    ratio = max(float(db_over_d or 0.0), 0.0)
    limit_case = _driven_sand_tip_limit_case(soil_text)
    qlambda_mpa = (0.30 if limit_case == "silty_sand" else 0.40) * n
    qp_mpa_raw = 0.038 * n * ratio
    qp_mpa = min(qp_mpa_raw, qlambda_mpa)
    note = f"Cọc đóng/ép đất rời Meyerhof: qp=0.038·N160·Db/D={qp_mpa_raw:.3f} MPa; qλ={qlambda_mpa:.3f} MPa"
    return qp_mpa * 1000.0, {"N160": n, "Db_over_D": ratio, "qp_mpa_raw": qp_mpa_raw, "qp_mpa_limit": qlambda_mpa, "sand_tip_limit_case": limit_case}, note


def _interval_overlap_len(top1: float, bottom1: float, top2: float, bottom2: float) -> float:
    """Chiều dài giao nhau của hai đoạn cao độ [bottom, top]."""
    a_top, a_bot = max(float(top1), float(bottom1)), min(float(top1), float(bottom1))
    b_top, b_bot = max(float(top2), float(bottom2)), min(float(top2), float(bottom2))
    return max(min(a_top, b_top) - max(a_bot, b_bot), 0.0)


def clay_c_phi_side_nominal_kpa(c_mpa: float, phi_deg: float, sigma_v_eff_mpa: float) -> Tuple[float, float, str]:
    """Sức kháng bên danh định đất dính theo lựa chọn C,φ.

    Đây là nhánh tùy chọn thực dụng để dùng bộ chỉ tiêu c,φ trong bảng địa chất:
    qs = c + σ'v*tanφ, đổi MPa -> kPa. Mặc định module vẫn dùng SPT -> Su.
    """
    c = max(float(c_mpa), 0.0)
    phi = max(float(phi_deg), 0.0)
    sig = max(float(sigma_v_eff_mpa), 0.0)
    qs_mpa = c + sig * math.tan(math.radians(phi))
    return max(qs_mpa * 1000.0, 0.0), phi, "Đất dính C,φ: qs=c+σ'v·tanφ"


def clay_c_phi_tip_nominal_kpa(c_mpa: float, phi_deg: float, sigma_v_eff_mpa: float) -> Tuple[float, Dict[str, float], str]:
    """Sức kháng mũi danh định đất dính theo C,φ, dạng sức chịu tải tổng quát.

    qp = c*Nc + σ'v*Nq. Khi φ≈0, lấy Nc=9, Nq=1.
    """
    c = max(float(c_mpa), 0.0)
    phi = max(float(phi_deg), 0.0)
    sig = max(float(sigma_v_eff_mpa), 0.0)
    if phi <= 1e-6:
        Nq, Nc = 1.0, 9.0
    else:
        tanphi = math.tan(math.radians(phi))
        Nq = math.exp(math.pi * tanphi) * (math.tan(math.radians(45.0 + phi / 2.0)) ** 2.0)
        Nc = (Nq - 1.0) / max(tanphi, 1e-12)
    qp_mpa = c * Nc + sig * Nq
    return max(qp_mpa * 1000.0, 0.0), {"Nc": Nc, "Nq": Nq, "c_mpa": c, "phi_deg": phi}, "Đất dính C,φ: qp=cNc+σ'vNq"


def beta_sand_bored(n60: float, n1_60: float, sigma_v_eff_mpa: float, mode: str = "sand", m_sand: float = 0.6) -> Tuple[float, float, float]:
    """Trả về beta, phi_deg, sigma_p_eff cho cọc khoan trong đất rời.

    Theo bảng Excel/TCVN 11823-10 đang dùng:
    - góc ma sát tính toán: phi_f = 27.5 + 9.2*log10((N1)60)
    - ứng suất tiền cố kết hiệu quả: sigma'p = 0.47*N60^m*pa cho cát
      hoặc sigma'p = 0.15*N60*pa cho sỏi.

    Vì vậy KHÔNG được dùng (N1)60 cho sigma'p. V0.1.1 đã truyền nhầm
    một biến vào cả hai vị trí; V0.1.2 tách rõ N60 và (N1)60.
    """
    n60_val = max(float(n60), 1e-6)
    n160_val = max(float(n1_60), 1e-6)
    sv = max(float(sigma_v_eff_mpa), 1e-5)
    phi_deg = 27.5 + 9.2 * math.log10(n160_val)
    sin_phi = math.sin(math.radians(phi_deg))
    tan_phi = math.tan(math.radians(phi_deg))
    if str(mode).strip().lower().startswith("gravel") or "sỏi" in str(mode).lower():
        sigma_p = 0.15 * n60_val * PA_MPA
    else:
        sigma_p = 0.47 * (n60_val ** float(m_sand)) * PA_MPA
    sigma_p = max(sigma_p, 1e-9)
    beta = (1.0 - sin_phi) * tan_phi * ((sigma_p / sv) ** sin_phi)
    return max(beta, 0.0), phi_deg, sigma_p


def cn_overburden_tcvn(sigma_v_eff_mpa: float) -> float:
    """Hệ số hiệu chỉnh áp lực phủ CN theo TVQT/TCVN.

    CN = 0.77*log10(1.92/sigma'v), giới hạn CN <= 2.0.
    Không ép (N1)60 <= N60, vì TVQT tính N160 = CN*N60.
    """
    sv = max(float(sigma_v_eff_mpa), 1e-5)
    cn = 0.77 * math.log10(1.92 / sv)
    return max(min(cn, 2.0), 0.0)


def n1_60_corrected(n_spt: float, sigma_v_eff_mpa: float, cap_to_n: bool = False) -> float:
    n = max(float(n_spt), 0.0)
    corr = n * cn_overburden_tcvn(sigma_v_eff_mpa)
    if cap_to_n:
        corr = min(corr, n)
    return max(corr, 0.0)


def rock_alpha_e_from_rqd(rqd: float, open_joint: bool = True) -> float:
    """Nội suy hệ số alpha_E theo RQD và tình trạng khe nứt đá.

    Bảng TCVN 11823-10:2017/O'Neill & Reese:
    RQD = 20,30,50,70,100%;
    khe nứt khép kín: 0.45,0.50,0.60,0.85,1.00;
    khe nứt hở hoặc có trét mùn: 0.45,0.50,0.55,0.55,0.85.
    open_joint=True nghĩa là khe nứt hở/có mùn.
    """
    xs = [20, 30, 50, 70, 100]
    closed = [0.45, 0.50, 0.60, 0.85, 1.00]
    openj = [0.45, 0.50, 0.55, 0.55, 0.85]
    return linear_interp(float(rqd), xs, openj if open_joint else closed, clamp=True)


def ksp_factor(spacing_crack_mm: float, width_crack_mm: float, diameter_m: float) -> float:
    """Hệ số Ksp cho mũi IGM/đá mềm theo khe nứt.

    spacing_crack_mm = sd: khoảng cách trung bình giữa các khe nứt, mm.
    width_crack_mm = td: chiều rộng/độ mở khe nứt, mm.
    Giá trị mặc định GUI: sd=50 mm, td=5 mm để thiên về bất lợi khi thiếu số liệu chi tiết.
    """
    sd = max(float(spacing_crack_mm), 1e-6)
    td = max(float(width_crack_mm), 0.0)
    d_mm = max(float(diameter_m) * 1000.0, 1e-6)
    return (3.0 + sd / d_mm) / (10.0 * math.sqrt(1.0 + 300.0 * td / sd))


def depth_factor_socket(socket_depth_m: float, diameter_m: float) -> float:
    return min(1.0 + 0.4 * max(socket_depth_m, 0.0) / max(diameter_m, 1e-9), 3.4)


def rock_side_nominal_kpa(qu_mpa: float, fc_mpa: float, rqd: float, supported: bool = True, open_joint: bool = True) -> Tuple[float, float, str]:
    """Sức kháng thành bên danh định trong đá theo TVQT/TCVN, trả kPa.

    - Thi công có chống đỡ thành hố / điều kiện bảo thủ theo Eq.97:
      qs = 0.65*αE*pa*sqrt(min(qu,f'c)/pa). Không bỏ αE khi giới hạn theo f'c.
    - Thi công không chống đỡ / thành hố tự ổn định theo Eq.96:
      qs = C*pa*sqrt(min(qu,f'c)/pa), C=1.0 cho thiết bị khoan thông thường.

    V0.2.33: rà lại theo TCVN 11823-10; cả Eq.96 và Eq.97 đều dùng qu_eff=min(qu,f'c) khi qu>f'c.
    Điều kiện khe nứt đá dùng để xác định αE theo RQD: khe nứt khép kín hoặc khe nứt hở/có mùn.
    qu và f'c nhập MPa; kết quả đổi sang kPa.
    """
    qu = max(float(qu_mpa), 0.0)
    fc = max(float(fc_mpa), 0.0)
    if qu <= 0:
        return 0.0, 0.0, "Thiếu qu đá"
    ae = rock_alpha_e_from_rqd(rqd, open_joint)
    qu_eff = min(qu, fc) if fc > 0 else qu
    lim_note = "; dùng min(qu,f'c)" if fc > 0 and qu > fc else ""
    if supported:
        qs_mpa = 0.65 * ae * PA_MPA * math.sqrt(max(qu_eff, 0.0) / PA_MPA)
        return qs_mpa * 1000.0, ae, "Đá - thi công có chống đỡ: 0.65*αE*pa*sqrt(min(qu,f'c)/pa)" + lim_note
    qs_mpa = PA_MPA * math.sqrt(max(qu_eff, 0.0) / PA_MPA)
    return qs_mpa * 1000.0, 1.0, "Đá - thi công không chống đỡ: C*pa*sqrt(min(qu,f'c)/pa), C=1.0" + lim_note


def igm_side_nominal_kpa(n60: float, qu_mpa: float, alpha: float, joint_factor: float, use_spt_when_missing_qu: bool = False) -> Tuple[float, str]:
    """Sức kháng thành bên danh định IGM.

    Quy trình mặc định:
    - Loại 1: SPT < 100 -> fsn = 0.0036*N (MPa).
    - Loại 2: SPT >= 100 và qu < 4.7 MPa -> fsn = 0.098*sqrt(qu) (MPa).
    - Loại 3: 4.7 <= qu < 23.9 MPa -> fsn = 0.81*qu^0.51 (MPa).
    - Nếu SPT >= 100 nhưng thiếu qu: chỉ dùng công thức SPT khi người dùng chọn rõ trong GUI.

    alpha và joint_factor được giữ trong chữ ký hàm để tương thích GUI/các bản cũ, nhưng không dùng
    trong quy trình IGM này.
    """
    n = max(float(n60), 0.0)
    qu = max(float(qu_mpa), 0.0)
    if n < 100.0:
        return 0.0036 * n * 1000.0, "IGM loại 1: SPT<100 -> fsn=0.0036N MPa"
    if qu <= 0.0:
        if use_spt_when_missing_qu:
            return 0.0036 * n * 1000.0, "IGM thiếu qu: người dùng chọn tính theo SPT -> fsn=0.0036N MPa"
        return 0.0, "IGM SPT>=100 nhưng thiếu qu -> chưa tính fsn"
    if qu < 4.7:
        return 0.098 * math.sqrt(qu) * 1000.0, "IGM loại 2: SPT>=100, qu<4.7MPa -> fsn=0.098√qu MPa"
    if qu < 23.9:
        return 0.81 * (qu ** 0.51) * 1000.0, "IGM loại 3: 4.7<=qu<23.9MPa -> fsn=0.81qu^0.51 MPa"
    return 0.81 * (qu ** 0.51) * 1000.0, "IGM qu>=23.9MPa ngoài miền khuyến nghị; fsn=0.81qu^0.51 MPa"


def igm_tip_nominal_kpa(n60: float, qu_mpa: float, crack_spacing_mm: float, crack_width_mm: float, diameter_m: float, socket_depth_m: float, use_spt_when_missing_qu: bool = False) -> Tuple[float, Dict[str, float], str]:
    """Sức kháng mũi danh định IGM.

    - Loại 1: SPT < 100 -> qBN = 0.0439*N (MPa).
    - Loại 2: SPT >= 100 và qu < 4.7 MPa -> qBN = 0.057*(1+Ld/D)*sqrt(qu) (MPa).
    - Nếu SPT >= 100 nhưng thiếu qu: chỉ dùng công thức SPT khi người dùng chọn rõ trong GUI.
    - Với qu >= 4.7 MPa, giữ nhánh mũi theo qu/Ksp của bản trước do bảng ảnh không nêu công thức mũi riêng.
    """
    n = max(float(n60), 0.0)
    qu = max(float(qu_mpa), 0.0)
    D = max(float(diameter_m), 1e-9)
    Ld = max(float(socket_depth_m), 0.0)
    if n < 100.0:
        return 0.0439 * n * 1000.0, {"N60": n}, "IGM loại 1: SPT<100 -> qBN=0.0439N MPa"
    if qu <= 0.0:
        if use_spt_when_missing_qu:
            return 0.0439 * n * 1000.0, {"N60": n, "igm_missing_qu_policy": "use_spt"}, "IGM thiếu qu: người dùng chọn tính theo SPT -> qBN=0.0439N MPa"
        return 0.0, {"N60": n}, "IGM SPT>=100 nhưng thiếu qu -> chưa tính qBN"
    if qu < 4.7:
        qp_mpa = 0.057 * (1.0 + Ld / D) * math.sqrt(qu)
        return qp_mpa * 1000.0, {"N60": n, "qu_mpa": qu, "socket_depth_m": Ld, "Ld_over_D": Ld / D}, "IGM loại 2: SPT>=100, qu<4.7MPa -> qBN=0.057(1+Ld/D)√qu MPa"
    ksp = ksp_factor(crack_spacing_mm, crack_width_mm, D)
    df = depth_factor_socket(Ld, D)
    qp_kpa = 3.0 * qu * ksp * df * 1000.0
    return qp_kpa, {"ksp": ksp, "depth_factor": df, "N60": n, "qu_mpa": qu, "socket_depth_m": Ld}, "IGM qu>=4.7MPa -> qBN=3quKsp*d"


def hoek_brown_qp(sigma_vb_mpa: float, qu_mpa: float, mi: float, gsi: float, disturbance: float) -> Tuple[float, Dict[str, float]]:
    """Sức kháng mũi đá nứt vỡ theo Hoek-Brown/GSI, trả MPa.

    Theo TCVN 11823-10 Eq.99-Eq.100:
        A  = σ'vb + qu * [mb*(σ'vb/qu)]^a
        qp = A    + qu * [mb*(A/qu) + s]^a
    Lưu ý: theo Eq.100 của TCVN, bước tính A không có +s.
    Trả thêm qp_uncapped_mpa; giới hạn 2.5qu được áp ở _tip_resistance theo lựa chọn người dùng.
    """
    qu = max(float(qu_mpa), 1e-6)
    sig = max(float(sigma_vb_mpa), 0.0)
    D = max(min(float(disturbance), 1.0), 0.0)
    gsi = float(gsi)
    mi = float(mi)
    s = math.exp((gsi - 100.0) / max(9.0 - 3.0 * D, 1e-9))
    a = 0.5 + (1.0 / 6.0) * (math.exp(-gsi / 15.0) - math.exp(-20.0 / 3.0))
    mb = mi * math.exp((gsi - 100.0) / max(28.0 - 14.0 * D, 1e-9))
    A = sig + qu * max(mb * (sig / qu), 0.0) ** a
    qp = A + qu * max(mb * (A / qu) + s, 0.0) ** a
    return qp, {"s": s, "a": a, "mb": mb, "A_mpa": A, "qb_mpa": A, "qp_uncapped_mpa": qp}


def _is_one_row_group_layout(value: Any) -> bool:
    """Xác định bệ 1 hàng cọc.

    V0.2.6: cột nhập liệu đổi thành Số hàng cọc, người dùng nhập số cho ngắn gọn.
    Vẫn giữ tương thích với chuỗi cũ "1 hàng cọc" / "Nhiều hàng cọc".
    """
    s = str(value or "").strip().lower()
    s_plain = s.replace("đ", "d")
    try:
        # Chỉ xem là 1 hàng khi giá trị số thực sự <= 1.5; tránh lỗi "10" bị nhận là 1 hàng.
        return float(s_plain.replace(",", ".")) <= 1.5
    except Exception:
        pass
    return ("1" in s and "hàng" in s) or ("1" in s_plain and "hang" in s_plain) or "mot hang" in s_plain or "một hàng" in s


def group_factor_one_row(spacing_over_d: float) -> float:
    """Hệ số nhóm cho bệ 1 hàng cọc.

    Nội suy theo S/D = khoảng cách cọc / đường kính cọc.
    Không dùng 2.72D làm mốc bảng; 2.72D chỉ là một giá trị S/D thực tế do người dùng nhập.
    Theo yêu cầu bảng tính hiện hành: 2.5D -> 0.90, 4.0D -> 1.00.
    """
    return linear_interp(spacing_over_d, [2.5, 4.0], [0.90, 1.00], clamp=True)


def group_factor_clay(spacing_over_d: float, layout: str = "Nhiều hàng cọc") -> float:
    """Hệ số nhóm đất dính theo S/D.

    Bệ 1 hàng dùng bảng riêng. Bệ nhiều hàng: 2.5D -> 0.65, 6.0D -> 1.00.
    """
    if _is_one_row_group_layout(layout):
        return group_factor_one_row(spacing_over_d)
    return linear_interp(spacing_over_d, [2.5, 6.0], [0.65, 1.00], clamp=True)


def group_factor_sand(spacing_over_d: float, layout: str = "Nhiều hàng cọc") -> float:
    """Hệ số nhóm đất rời/IGM/đá mềm theo S/D.

    Bệ 1 hàng dùng bảng riêng. Bệ nhiều hàng: 2.5D -> 0.67, 4.0D -> 1.00.
    """
    if _is_one_row_group_layout(layout):
        return group_factor_one_row(spacing_over_d)
    return linear_interp(spacing_over_d, [2.5, 4.0], [0.67, 1.00], clamp=True)


def group_factor_for_soil(soil_type: int, spacing_over_d: float, row_count: Any = "2", ignore_igm_rock: bool = False) -> Tuple[float, str]:
    """Hệ số nhóm theo từng lớp đất.

    - Đất dính áp bảng đất dính.
    - Đất rời/cuội sỏi áp bảng đất rời.
    - IGM/đá dùng bảng đất rời nếu không bỏ qua theo option.
    - Hệ số được nội suy theo S/D = khoảng cách cọc / D cọc.
    """
    st = int(soil_type or 0)
    if st == 2:
        return group_factor_clay(spacing_over_d, row_count), "fg đất dính"
    if st in (1, 6):
        return group_factor_sand(spacing_over_d, row_count), "fg đất rời"
    if st in (3, 4, 5):
        if ignore_igm_rock:
            return 1.0, "fg IGM/đá bỏ qua"
        return group_factor_sand(spacing_over_d, row_count), "fg IGM/đá"
    return 1.0, "fg=1.0"


@dataclass
class SoilLayer:
    name: str = ""
    bottom_elev_m: float = 0.0
    soil_type: int = 1  # 1=sand, 2=clay, 3=IGM/rock
    n_spt: float = 0.0      # Nₕₜ/N đo hiện trường nhập trong bảng địa chất; N60 = Nₕₜ*ER/60.
    gamma_kN_m3: float = 18.0
    c_mpa: float = 0.0      # C hoặc lực dính, MPa. Giữ tên c_mpa để dùng cho phương pháp C,φ.
    su_mpa: float = 0.0     # Su tương thích file cũ; V0.2 UI không nhập trực tiếp.
    phi_deg: float = 0.0
    qu_mpa: float = 0.0
    rqd: float = 50.0
    gsi: float = 30.0
    mi: float = 9.0
    disturbance: float = 0.5
    comment: str = ""


@dataclass
class PileInput:
    project: str = ""
    item: str = ""
    mode: str = "Cọc khoan trong đất"
    pile_type: str = "Cọc khoan nhồi"  # Cọc khoan nhồi / Cọc đóng (ép)
    analysis_type_auto: str = ""
    n_piles: int = 1
    diameter_mm: float = 1200.0
    # QA fix P7: 0 = mũi bằng D. Tránh trường hợp gọi API chỉ set diameter_mm mà mũi âm thầm dùng 1200.
    tip_diameter_mm: float = 0.0
    # QA fix P1: đường kính trong cho cọc ống (2O/3O); 0 = cọc đặc.
    driven_inner_dia_mm: float = 0.0
    spacing_m: float = 3.0
    pile_count_in_group: int = 1
    group_layout: str = "2"  # V0.2.6: Số hàng cọc; 1 = bệ 1 hàng, >=2 = nhiều hàng
    cap_width_m: float = 0.0
    cap_length_m: float = 0.0
    cap_thickness_m: float = 0.0
    ground_elev_m: float = 0.0
    cap_bottom_elev_m: float = 0.0
    pile_tip_elev_m: float = -30.0
    water_elev_m: float = 0.0
    concrete_gamma_kN_m3: float = 24.5
    fc_mpa: float = 30.0
    fy_mpa: float = 400.0
    n_rebars: int = 0
    rebar_dia_mm: float = 0.0
    structural_phi: float = 0.75
    stirrup_type: int = 1
    exclude_top_bored_m: float = 1.5
    sand_preconsolidation_mode: str = "sand"
    sand_m: float = 0.6
    igm_alpha: float = 0.25
    igm_joint_factor: float = 0.45
    igm_missing_qu_policy: str = "require_qu"  # require_qu / use_spt: xử lý IGM SPT>=100 nhưng thiếu qu
    rock_socket_depth_m: Optional[float] = None
    rock_side_method: str = "fractured"  # legacy: normal/fractured/ignore, chỉ giữ để đọc file cũ
    rock_construction_condition: str = "Có chống đỡ"  # Có chống đỡ / Không chống đỡ
    rock_joint_condition: str = "Khe nứt hở hoặc có mùn"  # Khe nứt khép kín / Khe nứt hở hoặc có mùn
    rock_tip_condition: str = "fractured"  # intact/fractured
    include_rock_tip: bool = False
    allow_rock_tip_exceed_25qu: bool = False  # Chỉ bật khi có thử tải/kinh nghiệm cho phép Qp đá vượt 2.5qu
    spt_er_percent: float = 60.0   # N60 = Nₕₜ * ER/60
    spt_input_mode: str = "Nₕₜ"  # Nₕₜ: số búa hiện trường; N60: dữ liệu nhập đã hiệu chỉnh năng lượng.
    clay_use_c_phi: bool = False
    ignore_group_igm_rock: bool = False
    allow_geology_extrapolation: bool = False  # Cho phép kéo dài lớp cuối xuống mũi cọc khi thiếu chiều sâu khảo sát
    driven_sand_method: str = "Meyerhof SPT"  # Nhánh cọc đóng đất rời: Meyerhof SPT; Nordlund cần thêm tham số riêng
    driven_clay_alpha_method: str = "Tomlinson"
    include_downdrag: bool = False
    downdrag_top_elev_m: float = 0.0
    downdrag_bottom_elev_m: float = 0.0
    downdrag_factor: float = 0.0
    force_cd_kn: float = 0.0       # Pu nén lớn nhất theo cọc đơn
    force_db_kn: float = 0.0       # Pu nén lớn nhất theo cọc đơn
    uplift_cd_kn: float = 0.0      # Lực nhổ lớn nhất/cọc TTGHCĐ, lấy trị tuyệt đối của N âm
    uplift_db_kn: float = 0.0      # Lực nhổ lớn nhất/cọc TTGHĐB, lấy trị tuyệt đối của N âm
    cap_force_cd_kn: float = 0.0   # Nội lực đáy bệ TTGHCĐ để kiểm nhóm
    cap_force_db_kn: float = 0.0   # Nội lực đáy bệ TTGHĐB để kiểm nhóm
    crack_spacing_mm: float = 50.0
    crack_width_mm: float = 5.0
    rock_open_joint: bool = True
    layers: List[SoilLayer] = field(default_factory=list)

    @property
    def diameter_m(self) -> float:
        return max(self.diameter_mm / 1000.0, 1e-9)

    @property
    def tip_diameter_m(self) -> float:
        return max((self.tip_diameter_mm or self.diameter_mm) / 1000.0, 1e-9)

    @property
    def _is_driven_mode(self) -> bool:
        mode_text = (self.mode + " " + self.pile_type).lower()
        return "đóng" in mode_text or "dong" in mode_text or "ép" in mode_text or "ep" in mode_text

    @property
    def driven_shape(self) -> str:
        """QA fix P1: tiết diện cọc đóng/ép: VUONG (mặc định, mã 2/3), TRON (2T/3T), ONG (2O/3O)."""
        if not self._is_driven_mode:
            return "TRON"
        text = _strip_accents(self.pile_type).lower()
        if " ong" in f" {text}" or "phc" in text:
            return "ONG"
        if "tron" in text:
            return "TRON"
        return "VUONG"

    @property
    def inner_diameter_m(self) -> float:
        return max(float(self.driven_inner_dia_mm or 0.0), 0.0) / 1000.0

    @property
    def perimeter_m(self) -> float:
        # QA fix P1: chu vi theo tiết diện thật: vuông = 4D; tròn/ống = πD.
        # Trước đây mọi cọc đóng/ép bị coi là vuông (4D) làm ma sát thành bên
        # của cọc tròn/ống bị phóng đại ~27%.
        if self._is_driven_mode and self.driven_shape == "VUONG":
            return 4.0 * self.diameter_m
        return math.pi * self.diameter_m

    @property
    def area_m2(self) -> float:
        """Diện tích mũi cọc dùng cho sức kháng mũi.

        Cọc ống coi như bịt mũi/nút đất kín -> dùng tiết diện đặc πD²/4 (có cảnh báo trong validate).
        """
        if self._is_driven_mode:
            if self.driven_shape == "VUONG":
                return self.diameter_m ** 2
            return math.pi * self.diameter_m ** 2 / 4.0
        return math.pi * self.tip_diameter_m ** 2 / 4.0

    @property
    def shaft_area_gross_m2(self) -> float:
        """Diện tích tiết diện thực: dùng cho Pr vật liệu và trọng lượng cọc (cọc ống trừ lõi rỗng)."""
        if self._is_driven_mode:
            if self.driven_shape == "VUONG":
                return self.diameter_m ** 2
            if self.driven_shape == "ONG":
                din = min(self.inner_diameter_m, self.diameter_m)
                return math.pi * max(self.diameter_m ** 2 - din ** 2, 0.0) / 4.0
            return math.pi * self.diameter_m ** 2 / 4.0
        return math.pi * self.diameter_m ** 2 / 4.0

    @property
    def pile_length_m(self) -> float:
        return max(self.cap_bottom_elev_m - self.pile_tip_elev_m, 0.0)


@dataclass
class LayerCalc:
    name: str
    top_elev_m: float
    bottom_elev_m: float
    thickness_m: float
    skin_length_m: float
    soil_type: int
    soil_label: str
    n_spt: float      # Nₕₜ/N nhập
    n60: float         # N60 đã hiệu chỉnh năng lượng ER
    n1_60: float       # (N1)60/N160 hiệu chỉnh áp lực phủ
    gamma_eff_kN_m3: float
    sigma_v_eff_mpa: float
    c_mpa: float
    su_mpa: float
    alpha_or_beta: float
    phi_deg: float
    qs_factored_kpa: float          # TTGHCĐ - giữ tên cũ để tương thích
    qs_nominal_kpa: float
    qs_factored_kn: float           # TTGHCĐ - giữ tên cũ để tương thích
    qs_nominal_kn: float
    qs_extreme_kpa: float = 0.0     # TTGHĐB
    qs_extreme_kn: float = 0.0      # TTGHĐB
    phi_strength: float = 0.0
    phi_extreme: float = 1.0
    group_factor: float = 1.0
    qu_mpa: float = 0.0
    rqd: float = 0.0
    note: str = ""
    qs_uplift_factored_kpa: float = 0.0
    qs_uplift_factored_kn: float = 0.0
    qs_uplift_extreme_kpa: float = 0.0
    qs_uplift_extreme_kn: float = 0.0
    downdrag_length_m: float = 0.0
    downdrag_kn: float = 0.0


@dataclass
class LimitStateCapacity:
    code: str
    label: str
    qshaft_kn: float
    qtip_kn: float
    compression_single_gross_kn: float
    pile_weight_effective_kn: float
    pile_weight_dry_kn: float
    buoyancy_kn: float
    compression_single_net_kn: float
    uplift_single_magnitude_kn: float
    uplift_single_signed_kn: float
    group_factor: float
    compression_group_single_gross_kn: float
    compression_group_single_net_kn: float
    compression_group_total_kn: float
    material_pr_kn: float
    governing_kn: float
    governing_note: str
    qshaft_uplift_kn: float = 0.0
    uplift_group_total_kn: float = 0.0
    downdrag_kn: float = 0.0
    compression_single_net_before_downdrag_kn: float = 0.0
    compression_group_total_before_downdrag_kn: float = 0.0


@dataclass
class CapacityResult:
    pile_input: PileInput
    layers: List[LayerCalc]
    qshaft_nominal_kn: float
    qtip_nominal_kn: float
    strength: LimitStateCapacity
    extreme: LimitStateCapacity
    warnings: List[str] = field(default_factory=list)
    toe_info: Dict[str, Any] = field(default_factory=dict)

    # Các property sau giữ tương thích với bản cũ, lấy theo TTGHCĐ.
    @property
    def qshaft_factored_kn(self) -> float:
        return self.strength.qshaft_kn

    @property
    def qtip_factored_kn(self) -> float:
        return self.strength.qtip_kn

    @property
    def compression_single_factored_kn(self) -> float:
        return self.strength.compression_single_gross_kn

    @property
    def compression_single_net_kn(self) -> float:
        return self.strength.compression_single_net_kn

    @property
    def uplift_single_factored_kn(self) -> float:
        return self.strength.uplift_single_magnitude_kn

    @property
    def group_factor(self) -> float:
        return self.strength.group_factor

    @property
    def compression_group_single_factored_kn(self) -> float:
        return self.strength.compression_group_single_gross_kn

    @property
    def compression_group_single_net_kn(self) -> float:
        return self.strength.compression_group_single_net_kn

    @property
    def compression_group_total_kn(self) -> float:
        return self.strength.compression_group_total_kn

    @property
    def material_pr_kn(self) -> float:
        return self.strength.material_pr_kn

    @property
    def governing_geotech_kn(self) -> float:
        return self.strength.governing_kn

    @property
    def governing_note(self) -> str:
        return self.strength.governing_note


class SCTCalculator:
    @staticmethod
    def structural_capacity_nominal_kn(inp: PileInput) -> float:
        # Pn = k1*(0.85fc(Ag-Ast)+fyAst), đơn vị kN.
        Ag = inp.shaft_area_gross_m2 * 1e6
        Ast = 0.0
        if inp.n_rebars > 0 and inp.rebar_dia_mm > 0:
            Ast = inp.n_rebars * math.pi * inp.rebar_dia_mm ** 2 / 4.0
        k1 = 0.85 if int(inp.stirrup_type) == 1 else 0.80
        pn_n = k1 * (0.85 * inp.fc_mpa * max(Ag - Ast, 0.0) + inp.fy_mpa * Ast)
        return pn_n / 1000.0

    @staticmethod
    def structural_phi_for_limit_state(limit_state: str) -> float:
        # TVQT dùng 0.75 cho TTGHCĐ và 1.0 cho TTGHĐB.
        return 1.0 if str(limit_state).upper() in (LIMIT_STATE_EXTREME, "DB", "ĐB", "EXTREME") else 0.75

    @staticmethod
    def structural_capacity_kn(inp: PileInput, limit_state: str = LIMIT_STATE_STRENGTH) -> float:
        return SCTCalculator.structural_capacity_nominal_kn(inp) * SCTCalculator.structural_phi_for_limit_state(limit_state)

    @staticmethod
    def _is_driven(inp: PileInput) -> bool:
        txt = _strip_accents((inp.mode + " " + inp.pile_type)).lower()
        return ("dong" in txt) or ("ep" in txt)

    @staticmethod
    def _uplift_phi(inp: PileInput, soil_type: int, limit_state: str = LIMIT_STATE_STRENGTH) -> float:
        """Hệ số sức kháng nhổ tách riêng với hệ số nén."""
        st = int(soil_type or 0)
        ls = str(limit_state).upper()
        if ls in (LIMIT_STATE_EXTREME, "DB", "ĐB", "EXTREME"):
            return PHI_EXTREME_UPLIFT_DEFAULT
        if SCTCalculator._is_driven(inp):
            if st in (1, 6):
                return PHI_UPLIFT_DRIVEN_SAND
            if st == 2:
                return PHI_UPLIFT_DRIVEN_CLAY
            if st == 5:
                return PHI_UPLIFT_BORE_IGM
            if st in (3, 4):
                return PHI_UPLIFT_ROCK_SIDE
            return 0.0
        if st in (1, 6):
            return PHI_UPLIFT_BORE_SAND
        if st == 2:
            return PHI_UPLIFT_BORE_CLAY
        if st == 5:
            return PHI_UPLIFT_BORE_IGM
        if st in (3, 4):
            return PHI_UPLIFT_ROCK_SIDE
        return 0.0

    @staticmethod
    def default_downdrag_load_factor(inp: PileInput) -> float:
        """Hệ số tải trọng ma sát âm γDD theo TCVN 11823-3, Bảng 4.

        Dùng giá trị lớn nhất khi DD là tác dụng bất lợi trong kiểm toán nén:
        - Cọc đóng/ép theo α Tomlinson: 1.40
        - Cọc đóng/ép theo λ: 1.05
        - Cọc khoan theo O'Neill & Reese: 1.25
        """
        if SCTCalculator._is_driven(inp):
            method = _strip_accents(str(getattr(inp, "driven_clay_alpha_method", "Tomlinson") or "Tomlinson")).lower()
            if "lambda" in method or method.strip() in ("lamda", "λ"):
                return GAMMA_DD_LAMBDA
            return GAMMA_DD_TOMLINSON
        return GAMMA_DD_ONEILL_REESE

    @staticmethod
    def _downdrag_zone(inp: PileInput) -> Optional[Tuple[float, float]]:
        if not bool(getattr(inp, "include_downdrag", False)):
            return None
        top = float(getattr(inp, "downdrag_top_elev_m", inp.ground_elev_m) or inp.ground_elev_m)
        bot = float(getattr(inp, "downdrag_bottom_elev_m", inp.pile_tip_elev_m) or inp.pile_tip_elev_m)
        if abs(top - bot) < 1e-9:
            return None
        return max(top, bot), min(top, bot)

    @staticmethod
    def _preprocess_layers(inp: PileInput) -> List[str]:
        """Chuẩn hóa dữ liệu lớp trước khi tính, đặc biệt lớp 0 không khí/hang karst."""
        warnings: List[str] = []
        for ly in inp.layers:
            try:
                if int(ly.soil_type or 0) == 0:
                    changed = []
                    if abs(float(ly.gamma_kN_m3 or 0.0)) > 1e-9:
                        changed.append(f"γ {ly.gamma_kN_m3:g}->0")
                    ly.gamma_kN_m3 = 0.0
                    ly.n_spt = 0.0
                    ly.c_mpa = 0.0
                    ly.su_mpa = 0.0
                    ly.phi_deg = 0.0
                    ly.qu_mpa = 0.0
                    ly.rqd = 0.0
                    if changed:
                        warnings.append(f"Lớp {ly.name or '?'} type 0 Không khí/Hang karst: tự ép " + ", ".join(changed) + ".")
            except Exception:
                continue
        return warnings

    @staticmethod
    def _validate_input(inp: PileInput) -> List[str]:
        warnings: List[str] = []
        if _safe_float(getattr(inp, "diameter_mm", 0.0), 0.0) <= 0.0:
            warnings.append("Chưa nhập đường kính/cạnh cọc D; cần bổ sung trước khi dùng kết quả tính toán.")
        if not str(getattr(inp, "pile_type", "") or "").strip():
            warnings.append("Chưa chọn loại cọc; nhập 1 = khoan nhồi, 2/3 = đóng/ép vuông, 2T/3T = đóng/ép tròn, 2O/3O = cọc ống (Ds = D trong).")
        if SCTCalculator._is_driven(inp):
            shape = getattr(inp, "driven_shape", "VUONG")
            if shape == "ONG":
                din = _safe_float(getattr(inp, "driven_inner_dia_mm", 0.0), 0.0)
                dout = _safe_float(getattr(inp, "diameter_mm", 0.0), 0.0)
                if din <= 0.0:
                    warnings.append("Cọc ống nhưng chưa nhập đường kính trong (cột Ds); Pr vật liệu/trọng lượng tạm tính như cọc tròn đặc.")
                elif din >= dout > 0.0:
                    warnings.append("Đường kính trong cọc ống >= đường kính ngoài; kiểm tra lại cột Ds.")
                warnings.append("Cọc ống: sức kháng mũi tính với tiết diện đặc (coi như bịt mũi/nút đất kín); "
                                "Pr vật liệu tính như BTCT thường - cọc PHC ứng suất trước cần đối chiếu catalogue nhà sản xuất.")
            elif shape == "VUONG":
                warnings.append("Cọc đóng/ép mã 2/3 được tính là cọc VUÔNG đặc (chu vi 4D, diện tích D×D); "
                                "nếu thực tế là cọc tròn/ống hãy dùng mã 2T/3T hoặc 2O/3O.")
        layers = SCTCalculator._sorted_layers(inp)
        if not layers:
            return warnings
        last_bottom = min(float(ly.bottom_elev_m) for ly in layers)
        if inp.pile_tip_elev_m < last_bottom - 1e-9 and not getattr(inp, "allow_geology_extrapolation", False):
            warnings.append(f"Mũi cọc ({inp.pile_tip_elev_m:g}) nằm dưới đáy lớp khảo sát cuối ({last_bottom:g}); không ngoại suy địa tầng. Cần bổ sung lớp địa chất hoặc bật option cho phép ngoại suy.")
        if inp.pile_tip_elev_m < last_bottom - 1e-9 and getattr(inp, "allow_geology_extrapolation", False):
            warnings.append(f"Đã cho phép ngoại suy lớp cuối từ {last_bottom:g} xuống mũi cọc {inp.pile_tip_elev_m:g}; cần kiểm chứng địa chất.")
        top = inp.ground_elev_m
        prev_bottom = top
        for ly in layers:
            if ly.bottom_elev_m > prev_bottom + 1e-9:
                warnings.append(f"Cao độ đáy lớp {ly.name or '?'} không giảm dần so với lớp phía trên; kiểm tra bảng địa chất.")
            prev_bottom = ly.bottom_elev_m

        # Cảnh báo thiếu số liệu địa chất nhập từ bảng. Các cờ _missing_* được gắn ở lớp GUI
        # khi đọc raw cell để không nhầm giá trị mặc định nội bộ là dữ liệu người dùng đã nhập.
        missing_gamma_layers: List[str] = []
        missing_spt_layers: List[str] = []
        missing_rock_layers: List[str] = []
        for idx, ly in enumerate(layers):
            st = int(getattr(ly, "soil_type", 0) or 0)
            lname = str(getattr(ly, "name", "") or f"L{idx+1}").strip() or f"L{idx+1}"
            if st != 0 and bool(getattr(ly, "_missing_gamma", False)):
                missing_gamma_layers.append(lname)
            if st in (3, 4) and bool(getattr(ly, "_missing_rock_data", False)):
                missing_rock_layers.append(lname)
            # Không cảnh báo thiếu SPT cho 1-2 lớp đầu, lớp 0 và lớp đá dùng bộ chỉ tiêu đá riêng.
            if idx >= 2 and st not in (0, 3, 4) and bool(getattr(ly, "_missing_spt", False)):
                missing_spt_layers.append(lname)
        if missing_rock_layers:
            warnings.append("Thiếu số liệu lớp đá: " + ", ".join(missing_rock_layers) + ".")
        if missing_gamma_layers:
            warnings.append("Thiếu trọng lượng riêng các lớp đất: " + ", ".join(missing_gamma_layers) + ".")
        if missing_spt_layers:
            warnings.append("Thiếu SPT của lớp " + ", ".join(missing_spt_layers) + ".")

        zone = SCTCalculator._downdrag_zone(inp)
        if getattr(inp, "include_downdrag", False):
            if zone is None:
                warnings.append("Đã bật ma sát âm nhưng chưa khai báo vùng hợp lệ; không tính downdrag.")
            else:
                ztop, zbot = zone
                if ztop <= zbot:
                    warnings.append("Vùng ma sát âm không hợp lệ.")
                if ztop > inp.cap_bottom_elev_m + 1e-9:
                    warnings.append("Đỉnh vùng ma sát âm nằm phía trên đáy bệ; chỉ xét phần giao với đoạn cọc.")
                if zbot < inp.pile_tip_elev_m - 1e-9:
                    warnings.append("Đáy vùng ma sát âm nằm dưới mũi cọc; chỉ xét phần giao với đoạn cọc.")
        return warnings

    @staticmethod
    def _shaft_phi(inp: PileInput, soil_type: int, limit_state: str = LIMIT_STATE_STRENGTH, n60: Optional[float] = None) -> float:
        st = int(soil_type)
        ls = str(limit_state).upper()
        if ls in (LIMIT_STATE_EXTREME, "DB", "ĐB", "EXTREME"):
            return PHI_EXTREME_DEFAULT
        if SCTCalculator._is_driven(inp):
            if st in (1, 6):
                return PHI_DRIVEN_SHAFT_SAND
            if st == 2:
                return PHI_DRIVEN_SHAFT_CLAY
            if st == 5:
                nv = float(n60) if n60 is not None else 100.0
                return PHI_BORE_SHAFT_IGM_SPT_LT100 if nv < 100.0 else PHI_BORE_SHAFT_IGM_SPT_GE100
            return PHI_ROCK_SIDE
        if st in (1, 6):
            return PHI_BORE_SHAFT_SAND
        if st == 2:
            return PHI_BORE_SHAFT_CLAY
        if st == 5:
            nv = float(n60) if n60 is not None else 100.0
            return PHI_BORE_SHAFT_IGM_SPT_LT100 if nv < 100.0 else PHI_BORE_SHAFT_IGM_SPT_GE100
        if st in (3, 4):
            return PHI_ROCK_SIDE
        return 0.0

    @staticmethod
    def _tip_phi(inp: PileInput, soil_type: int, limit_state: str = LIMIT_STATE_STRENGTH, n60: Optional[float] = None) -> float:
        st = int(soil_type)
        ls = str(limit_state).upper()
        if ls in (LIMIT_STATE_EXTREME, "DB", "ĐB", "EXTREME"):
            return PHI_EXTREME_DEFAULT
        mode_l = (inp.mode + " " + inp.pile_type).lower()
        if SCTCalculator._is_driven(inp):
            if st in (1, 6):
                return PHI_DRIVEN_TIP_SAND
            if st == 2:
                return PHI_DRIVEN_TIP_CLAY
            if st == 5:
                nv = float(n60) if n60 is not None else 100.0
                return PHI_BORE_SHAFT_IGM_SPT_LT100 if nv < 100.0 else PHI_BORE_SHAFT_IGM_SPT_GE100
            return PHI_ROCK_TIP
        if st in (1, 6):
            return PHI_BORE_TIP_SAND
        if st == 2:
            return PHI_BORE_TIP_CLAY
        if st == 5:
            nv = float(n60) if n60 is not None else 100.0
            return PHI_BORE_SHAFT_IGM_SPT_LT100 if nv < 100.0 else PHI_BORE_SHAFT_IGM_SPT_GE100
        if st in (3, 4):
            return PHI_ROCK_TIP
        return 0.0

    @staticmethod
    def pile_weight_effective_kn(inp: PileInput) -> Tuple[float, float, float]:
        """Trả về (W khô, W hữu hiệu, lực đẩy nổi) của bản thân cọc, kN.

        W hữu hiệu tính theo mực nước ngầm:
        - đoạn trên nước: gamma_c
        - đoạn dưới nước: gamma_c - gamma_w
        """
        A = inp.shaft_area_gross_m2
        top = inp.cap_bottom_elev_m
        bot = inp.pile_tip_elev_m
        L = max(top - bot, 0.0)
        gamma_c = max(inp.concrete_gamma_kN_m3, 0.0)
        w_dry = A * L * gamma_c
        if L <= 0:
            return 0.0, 0.0, 0.0
        water = inp.water_elev_m
        if water >= top:
            L_sub = L
        elif water <= bot:
            L_sub = 0.0
        else:
            L_sub = water - bot
        L_sub = max(min(L_sub, L), 0.0)
        L_above = L - L_sub
        gamma_sub = max(gamma_c - GAMMA_W_KN_M3, 0.0)
        w_eff = A * (L_above * gamma_c + L_sub * gamma_sub)
        return w_dry, w_eff, max(w_dry - w_eff, 0.0)

    @staticmethod
    def _sorted_layers(inp: PileInput) -> List[SoilLayer]:
        layers = [ly for ly in inp.layers if str(ly.name).strip() or abs(float(ly.bottom_elev_m)) > 1e-12]
        # Cao độ giảm theo chiều sâu: top lớn, bottom nhỏ.
        layers.sort(key=lambda ly: ly.bottom_elev_m, reverse=True)
        return layers

    @staticmethod
    def _unit_weight_effective(gamma_kN_m3: float, z_mid_elev: float, water_elev: float) -> float:
        # Nếu dưới mực nước, lấy gamma' = gamma - gamma_w. Nếu trên mực nước, lấy gamma.
        if z_mid_elev <= water_elev:
            return max(gamma_kN_m3 - GAMMA_W_KN_M3, 0.1)
        return gamma_kN_m3

    @staticmethod
    def _sigma_v_eff_at(inp: PileInput, elev_m: float, layer_tops: List[Tuple[float, SoilLayer]]) -> float:
        """Tích phân ứng suất hữu hiệu từ mặt đất/cao độ bắt đầu đến elev_m, trả MPa."""
        if elev_m >= inp.ground_elev_m:
            return 0.0
        stress_kpa = 0.0
        current_top = inp.ground_elev_m
        for bottom, ly in layer_tops:
            seg_top = current_top
            seg_bot = bottom
            if seg_bot >= seg_top:
                current_top = seg_bot
                continue
            # lấy phần từ seg_top xuống max(seg_bot, elev_m)
            a = seg_top
            b = max(seg_bot, elev_m)
            if a > b:
                mid = (a + b) / 2.0
                gamma_layer = 0.0 if int(getattr(ly, "soil_type", 0) or 0) == 0 else max(float(ly.gamma_kN_m3 or 0.0), 0.0)
                gamma_eff = SCTCalculator._unit_weight_effective(gamma_layer, mid, inp.water_elev_m) if gamma_layer > 0 else 0.0
                # nếu mực nước cắt giữa đoạn, chia đôi để chính xác hơn
                if b < inp.water_elev_m < a:
                    stress_kpa += max(a - inp.water_elev_m, 0.0) * gamma_layer
                    stress_kpa += max(inp.water_elev_m - b, 0.0) * max(gamma_layer - GAMMA_W_KN_M3, 0.0)
                else:
                    stress_kpa += (a - b) * gamma_eff
            if elev_m >= seg_bot:
                break
            current_top = seg_bot
        return max(stress_kpa / 1000.0, 0.0)

    @staticmethod
    def _build_layer_segments(inp: PileInput) -> List[Tuple[float, float, SoilLayer]]:
        layers = SCTCalculator._sorted_layers(inp)
        segments: List[Tuple[float, float, SoilLayer]] = []
        if not layers:
            return segments
        top = inp.ground_elev_m
        pile_top = inp.cap_bottom_elev_m
        pile_tip = inp.pile_tip_elev_m
        # Nếu đáy bệ/cọc nằm trên mặt đất, tự tạo đoạn không khí từ đáy bệ đến mặt đất.
        if pile_top > inp.ground_elev_m + 1e-9:
            air = SoilLayer(name="Không khí", bottom_elev_m=inp.ground_elev_m, soil_type=0, n_spt=0.0, gamma_kN_m3=0.0)
            segments.append((pile_top, inp.ground_elev_m, air))
        for ly in layers:
            bottom = ly.bottom_elev_m
            seg_top = min(top, pile_top)
            seg_bottom = max(bottom, pile_tip)
            # đoạn giao giữa lớp đất và đoạn cọc
            inter_top = min(top, pile_top)
            inter_bottom = max(bottom, pile_tip)
            if inter_top > inter_bottom:
                segments.append((inter_top, inter_bottom, ly))
            top = bottom
            if bottom <= pile_tip:
                break
        # Không tự kéo lớp cuối xuống mũi nếu chưa cho phép ngoại suy.
        if segments and segments[-1][1] > pile_tip and getattr(inp, "allow_geology_extrapolation", False):
            last_top, last_bottom, last_ly = segments[-1]
            segments[-1] = (last_top, pile_tip, last_ly)
        return segments

    @staticmethod
    def _layer_tops(inp: PileInput) -> List[Tuple[float, SoilLayer]]:
        layers = SCTCalculator._sorted_layers(inp)
        return [(ly.bottom_elev_m, ly) for ly in layers]

    @staticmethod
    def _n60_from_input(inp: PileInput, layer: SoilLayer) -> float:
        """Đổi SPT nhập trong bảng địa chất sang N60.

        Mặc định bảng địa chất nhập Nₕₜ/N đo hiện trường và đổi theo ER:
            N60 = Nₕₜ * ER / 60

        Để đối chiếu với các bản cũ hoặc dữ liệu đã hiệu chỉnh, có thể chọn chế độ
        "N60" trong tab Thông số chung; khi đó số nhập ở cột SPT được dùng trực tiếp
        là N60 và không nhân lại hệ số ER.
        """
        n_in = max(float(getattr(layer, "n_spt", 0.0) or 0.0), 0.0)
        mode = str(getattr(inp, "spt_input_mode", "Nₕₜ") or "Nₕₜ").upper().replace(" ", "")
        if "N60" in mode:
            return n_in
        er = max(float(getattr(inp, "spt_er_percent", 60.0) or 60.0), 0.0)
        if er <= 0.0:
            er = 60.0
        return n_in * er / 60.0

    @staticmethod
    def _spt_note(inp: PileInput, n_input: float, n60: float) -> str:
        mode = str(getattr(inp, "spt_input_mode", "Nₕₜ") or "Nₕₜ").upper().replace(" ", "")
        if "N60" in mode:
            return f"SPT nhập đã là N60={n60:.2f}"
        return f"Nₕₜ={n_input:.2f}, ER={getattr(inp, 'spt_er_percent', 60.0):.0f}%, N60={n60:.2f}"

    @staticmethod
    def _rock_supported_construction(inp: PileInput) -> bool:
        txt = _strip_accents(str(getattr(inp, "rock_construction_condition", "") or "")).lower()
        if not txt:
            legacy = str(getattr(inp, "rock_side_method", "fractured") or "fractured").lower()
            return not legacy.startswith("normal")
        return "khong" not in txt

    @staticmethod
    def _rock_open_joint(inp: PileInput) -> bool:
        txt = _strip_accents(str(getattr(inp, "rock_joint_condition", "") or "")).lower()
        if txt:
            return not ("khep" in txt and "kin" in txt)
        return bool(getattr(inp, "rock_open_joint", True))

    @staticmethod
    def _clay_su_for_layer(inp: PileInput, ly: SoilLayer) -> float:
        """Su của lớp sét dùng cho các nhánh alpha/mũi cọc, MPa."""
        c_mpa = ly.c_mpa if ly.c_mpa > 0 else ly.su_mpa
        n60 = SCTCalculator._n60_from_input(inp, ly)
        return max(c_mpa, 0.0) if bool(getattr(inp, "clay_use_c_phi", False)) else 0.006 * max(n60, 0.0)

    @staticmethod
    def _tomlinson_cover_case(inp: PileInput, ly: SoilLayer) -> str:
        """Chọn bảng α Tomlinson theo lớp nằm ngay phía trên lớp sét đang xét."""
        layers = SCTCalculator._sorted_layers(inp)
        idx = None
        for i, item in enumerate(layers):
            if item is ly:
                idx = i
                break
        # Trường hợp đối tượng bị copy/tái tạo, dùng cao độ + tên để tìm gần đúng.
        if idx is None:
            for i, item in enumerate(layers):
                if str(item.name).strip() == str(ly.name).strip() and abs(float(item.bottom_elev_m) - float(ly.bottom_elev_m)) < 1e-7:
                    idx = i
                    break
        above = layers[idx - 1] if idx is not None and idx > 0 else None
        def clay_case_by_su_n60(layer: SoilLayer) -> str:
            su_val = SCTCalculator._clay_su_for_layer(inp, layer)
            n60_val = SCTCalculator._n60_from_input(inp, layer)
            case_su = "soft_clay" if su_val < 0.05 else "stiff_clay"
            case_n = "soft_clay" if n60_val < 8.0 else "stiff_clay"
            if case_su != case_n:
                return "clay_worst"
            return case_su

        if above is not None:
            st_above = int(getattr(above, "soil_type", 0) or 0)
            if st_above in (1, 6):
                return "sand_gravel"
            if st_above == 2:
                return clay_case_by_su_n60(above)
        # Nếu không xác định được lớp phía trên, dùng chính trạng thái lớp sét đang xét.
        return clay_case_by_su_n60(ly)

    @staticmethod
    def _tomlinson_db_over_d(inp: PileInput, elev_m: float) -> float:
        """Db/D theo độ sâu điểm xét dưới cao độ thiên nhiên/mặt đất."""
        return max(float(inp.ground_elev_m) - float(elev_m), 0.0) / max(float(inp.diameter_m), 1e-9)

    @staticmethod
    def _skin_resistance(inp: PileInput) -> Tuple[List[LayerCalc], float, float, float, List[str]]:
        warnings: List[str] = []
        driven_igm_rock_warned: set = set()
        segments = SCTCalculator._build_layer_segments(inp)
        layer_tops = SCTCalculator._layer_tops(inp)
        result_layers: List[LayerCalc] = []
        qsf = 0.0
        qsf_ex = 0.0
        qsn = 0.0
        mode_l = (inp.mode + " " + inp.pile_type).lower()
        is_driven = SCTCalculator._is_driven(inp)
        exclude_top = inp.exclude_top_bored_m if (("khoan" in mode_l) and not is_driven) else 0.0
        skin_start_elev = inp.cap_bottom_elev_m - max(exclude_top, 0.0)
        dd_zone = SCTCalculator._downdrag_zone(inp)
        dd_factor = max(float(getattr(inp, "downdrag_factor", 0.0) or SCTCalculator.default_downdrag_load_factor(inp)), 0.0)

        for top, bottom, ly in segments:
            th = max(top - bottom, 0.0)
            # Chiều dài ma sát hình học sau khi bỏ đoạn đầu cọc khoan.
            skin_top = min(top, skin_start_elev)
            skin_bottom = bottom
            skin_full_len = max(skin_top - skin_bottom, 0.0)
            dd_len = 0.0
            if dd_zone and skin_full_len > 1e-9:
                dd_top, dd_bot = dd_zone
                dd_len = _interval_overlap_len(skin_top, skin_bottom, dd_top, dd_bot)
            # Vùng ma sát âm không được tính là ma sát dương chịu nén; đồng thời không lấy vào nhổ để bảo thủ.
            skin_len = max(skin_full_len - dd_len, 0.0)
            mid_elev = (skin_top + skin_bottom) / 2.0 if skin_full_len > 0 else (top + bottom) / 2.0
            sigma_v = SCTCalculator._sigma_v_eff_at(inp, mid_elev, layer_tops)
            gamma_eff = 0.0 if int(getattr(ly, "soil_type", 0) or 0) == 0 else SCTCalculator._unit_weight_effective(ly.gamma_kN_m3, mid_elev, inp.water_elev_m)
            n1_input = max(ly.n_spt, 0.0)
            n60 = SCTCalculator._n60_from_input(inp, ly)
            st = int(ly.soil_type)
            if st == 0:
                skin_len = 0.0
                dd_len = 0.0
            is_sand = st in (1, 6)
            is_clay = st == 2
            is_intact_rock = st == 3
            is_fractured_rock = st == 4
            is_igm = st == 5
            n1 = n1_60_corrected(n60, sigma_v, cap_to_n=False) if is_sand else n60
            c_mpa = ly.c_mpa if ly.c_mpa > 0 else ly.su_mpa
            su = 0.006 * n60 if not inp.clay_use_c_phi else max(c_mpa, 0.0)
            alpha_beta = 0.0
            phi_deg = ly.phi_deg
            qs_nominal_kpa = 0.0
            note = ""

            if skin_full_len <= 1e-9 or st == 0:
                note = "Không tính ma sát thành bên"
            elif is_driven:
                if is_sand:
                    qs_nominal_kpa, note = driven_sand_side_nominal_kpa(n1, inp.pile_type)
                    alpha_beta = 0.0
                    note += f"; {SCTCalculator._spt_note(inp, n1_input, n60)}; N160={n1:.2f}"
                elif is_clay:
                    if inp.clay_use_c_phi:
                        qs_nominal_kpa, alpha_beta, note = clay_c_phi_side_nominal_kpa(c_mpa, ly.phi_deg, sigma_v)
                        note = "Cọc đóng/ép - " + note
                    else:
                        db_over_d = SCTCalculator._tomlinson_db_over_d(inp, mid_elev)
                        cover_case = SCTCalculator._tomlinson_cover_case(inp, ly)
                        alpha_beta = alpha_clay_driven_tomlinson(su, db_over_d, cover_case)
                        qs_nominal_kpa = alpha_beta * su * 1000.0
                        case_label = _TOMLINSON_CASE_LABELS.get(cover_case, cover_case)
                        note = f"Cọc đóng/ép - đất dính: qs=αSu; α Tomlinson nội suy theo {case_label}, Su={su:.3f}MPa, Db/D={db_over_d:.2f}; " + SCTCalculator._spt_note(inp, n1_input, n60)
                elif is_igm:
                    qs_nominal_kpa, note = igm_side_nominal_kpa(n60, ly.qu_mpa, inp.igm_alpha, inp.igm_joint_factor, str(getattr(inp, "igm_missing_qu_policy", "require_qu")).lower() == "use_spt")
                    alpha_beta = inp.igm_alpha
                    note = "Cọc đóng/ép - " + note
                    # QA fix P3: công thức IGM xây dựng cho cọc khoan nhồi; cảnh báo khi áp cho cọc đóng/ép.
                    if ly.name not in driven_igm_rock_warned:
                        driven_igm_rock_warned.add(ly.name)
                        warnings.append(f"Lớp {ly.name or '?'}: cọc đóng/ép trong IGM dùng công thức của cọc khoan (ngoài phạm vi phương pháp); nên kiểm soát bằng độ chối/thử động khi thi công.")
                else:
                    qs_nominal_kpa, alpha_beta, note = rock_side_nominal_kpa(ly.qu_mpa, inp.fc_mpa, ly.rqd, supported=SCTCalculator._rock_supported_construction(inp), open_joint=SCTCalculator._rock_open_joint(inp))
                    note = "Cọc đóng/ép trong đá - " + note
                    if ly.name not in driven_igm_rock_warned:
                        driven_igm_rock_warned.add(ly.name)
                        warnings.append(f"Lớp {ly.name or '?'}: cọc đóng/ép trong đá dùng công thức thành bên của cọc khoan (ngoài phạm vi phương pháp); nên kiểm soát bằng độ chối/thử động khi thi công.")
            else:
                if is_sand:
                    mode = "gravel" if st == 6 else inp.sand_preconsolidation_mode
                    alpha_beta, phi_calc, sigma_p = beta_sand_bored(n60, n1, sigma_v, mode, inp.sand_m)
                    phi_deg = phi_calc
                    qs_nominal_kpa = alpha_beta * sigma_v * 1000.0
                    note = f"Cọc khoan - đất rời: {SCTCalculator._spt_note(inp, n1_input, n60)}; σ'p dùng N60, φ dùng N160={n1:.2f}; σ'p={sigma_p:.3f} MPa"
                elif is_clay:
                    if inp.clay_use_c_phi:
                        qs_nominal_kpa, alpha_beta, note = clay_c_phi_side_nominal_kpa(c_mpa, ly.phi_deg, sigma_v)
                        note = "Cọc khoan - " + note
                    else:
                        warn = clay_alpha_domain_warning(ly.name, su)
                        if warn:
                            warnings.append(warn)
                        alpha_beta = alpha_clay_bored(su)
                        qs_nominal_kpa = alpha_beta * su * 1000.0
                        note = "Cọc khoan - đất dính: αSu, " + SCTCalculator._spt_note(inp, n1_input, n60)
                elif is_igm:
                    qs_nominal_kpa, note = igm_side_nominal_kpa(n60, ly.qu_mpa, inp.igm_alpha, inp.igm_joint_factor, str(getattr(inp, "igm_missing_qu_policy", "require_qu")).lower() == "use_spt")
                    alpha_beta = inp.igm_alpha
                    note = "Cọc khoan - " + note
                elif is_intact_rock or is_fractured_rock:
                    if ly.qu_mpa <= 0:
                        warnings.append(f"Lớp {ly.name}: chưa nhập qu đá, không tính đúng ma sát thành bên đá.")
                    qs_nominal_kpa, alpha_beta, note = rock_side_nominal_kpa(
                        ly.qu_mpa, inp.fc_mpa, ly.rqd,
                        supported=SCTCalculator._rock_supported_construction(inp),
                        open_joint=SCTCalculator._rock_open_joint(inp),
                    )
                    note = "Cọc khoan trong đá: " + note
                else:
                    note = "Loại đất chưa hỗ trợ rõ; không tính ma sát thành bên"

            phi_cd = SCTCalculator._shaft_phi(inp, st, LIMIT_STATE_STRENGTH, n60=n60)
            phi_db = SCTCalculator._shaft_phi(inp, st, LIMIT_STATE_EXTREME, n60=n60)
            phi_up_cd = SCTCalculator._uplift_phi(inp, st, LIMIT_STATE_STRENGTH)
            phi_up_db = SCTCalculator._uplift_phi(inp, st, LIMIT_STATE_EXTREME)
            qs_factored_kpa = qs_nominal_kpa * phi_cd
            qs_extreme_kpa = qs_nominal_kpa * phi_db
            # Sức kháng nhổ dùng Rs danh định và hệ số φup riêng; không thêm hệ số giảm Rs để tránh double reduction.
            qs_uplift_cd_kpa = qs_nominal_kpa * phi_up_cd
            qs_uplift_db_kpa = qs_nominal_kpa * phi_up_db
            qf = inp.perimeter_m * qs_factored_kpa * skin_len
            qex = inp.perimeter_m * qs_extreme_kpa * skin_len
            qn = inp.perimeter_m * qs_nominal_kpa * skin_len
            qup_cd = inp.perimeter_m * qs_uplift_cd_kpa * skin_len
            qup_db = inp.perimeter_m * qs_uplift_db_kpa * skin_len
            dd_kn = inp.perimeter_m * qs_nominal_kpa * dd_len * dd_factor
            qsf += qf
            qsf_ex += qex
            qsn += qn
            if dd_len > 1e-9:
                note += f"; ma sát âm L={dd_len:.2f}m, γDD={dd_factor:.2f}, DD={dd_kn:.2f}kN; không tính ma sát dương trong vùng này"
            result_layers.append(LayerCalc(
                name=ly.name, top_elev_m=top, bottom_elev_m=bottom, thickness_m=th, skin_length_m=skin_len,
                soil_type=ly.soil_type, soil_label=SOIL_TYPE_LABELS.get(ly.soil_type, "?"), n_spt=ly.n_spt,
                n60=n60, n1_60=n1, gamma_eff_kN_m3=gamma_eff, sigma_v_eff_mpa=sigma_v, c_mpa=c_mpa, su_mpa=su,
                alpha_or_beta=alpha_beta, phi_deg=phi_deg, qs_factored_kpa=qs_factored_kpa,
                qs_nominal_kpa=qs_nominal_kpa, qs_factored_kn=qf, qs_nominal_kn=qn,
                qs_extreme_kpa=qs_extreme_kpa, qs_extreme_kn=qex, phi_strength=phi_cd, phi_extreme=phi_db, qu_mpa=ly.qu_mpa, rqd=ly.rqd, note=note,
                qs_uplift_factored_kpa=qs_uplift_cd_kpa, qs_uplift_factored_kn=qup_cd,
                qs_uplift_extreme_kpa=qs_uplift_db_kpa, qs_uplift_extreme_kn=qup_db,
                downdrag_length_m=dd_len, downdrag_kn=dd_kn,
            ))
        return result_layers, qsf, qsf_ex, qsn, warnings

    @staticmethod
    def _toe_layer(inp: PileInput) -> Optional[SoilLayer]:
        layers = SCTCalculator._sorted_layers(inp)
        if not layers:
            return None
        top = inp.ground_elev_m
        for ly in layers:
            if top >= inp.pile_tip_elev_m >= ly.bottom_elev_m:
                return ly
            top = ly.bottom_elev_m
        if getattr(inp, "allow_geology_extrapolation", False):
            return layers[-1]
        return None


    @staticmethod
    def _toe_layer_top_and_embedment(inp: PileInput, toe: SoilLayer) -> Tuple[float, float]:
        """Trả về cao độ đỉnh lớp mũi và chiều dài mũi cọc ngập trong lớp đó."""
        top = float(getattr(inp, "ground_elev_m", 0.0) or 0.0)
        for ly in SCTCalculator._sorted_layers(inp):
            bottom = float(getattr(ly, "bottom_elev_m", top) or top)
            same_obj = ly is toe
            same_val = (str(getattr(ly, "name", "")).strip() == str(getattr(toe, "name", "")).strip() and abs(bottom - float(getattr(toe, "bottom_elev_m", bottom) or bottom)) < 1e-7)
            if same_obj or same_val:
                return top, max(top - float(inp.pile_tip_elev_m), 0.0)
            top = bottom
        return float(getattr(inp, "ground_elev_m", 0.0) or 0.0), 0.0


    @staticmethod
    def _rock_tip_geology_conditions(inp: PileInput) -> Tuple[Dict[str, Any], List[str]]:
        """Kiểm tra điều kiện tự động để dùng qp=2.5qu cho mũi đá tốt.

        Điều kiện dùng 2.5qu theo TCVN được quy đổi như sau:
        - mũi nằm trong lớp loại 3: Đá nguyên khối / đá tốt;
        - điều kiện khe nứt global là khe nứt khép kín;
        - điều kiện thi công global là không chống đỡ / thành hố ổn định;
        - trong phạm vi 2B dưới mũi, địa tầng đều là đá tốt loại 3;
        - chiều sâu ngàm liên tục vào lớp đá tốt tại mũi > 1.5B.
        Nếu một trong các điều kiện này không thỏa, mũi đá dùng Hoek-Brown/GSI.
        """
        warnings: List[str] = []
        D = max(float(inp.diameter_m), 1e-9)
        tip = float(inp.pile_tip_elev_m)
        check_bot = tip - 2.0 * D
        layers = SCTCalculator._sorted_layers(inp)
        ctx: Dict[str, Any] = {
            "joint_ok": not SCTCalculator._rock_open_joint(inp),
            "construction_ok": not SCTCalculator._rock_supported_construction(inp),
            "good_rock_2b": False,
            "socket_depth_good_m": 0.0,
            "socket_ok": False,
            "toe_good_rock": False,
            "coverage_2b_m": 0.0,
            "required_2b_m": 2.0 * D,
            "required_socket_m": 1.5 * D,
            "use_25qu": False,
        }
        if not layers:
            warnings.append("Không có địa tầng để kiểm tra điều kiện Qp=2.5qu cho mũi đá.")
            return ctx, warnings

        top = inp.ground_elev_m
        toe_top = None
        toe_layer = None
        for ly in layers:
            bottom = ly.bottom_elev_m
            if top >= tip >= bottom:
                toe_top = top
                toe_layer = ly
                break
            top = bottom
        if toe_layer is None and getattr(inp, "allow_geology_extrapolation", False):
            # Chỉ dùng cho cảnh báo; bản chất vẫn không đủ để khẳng định 2B dưới mũi.
            toe_layer = layers[-1]
            toe_top = layers[-2].bottom_elev_m if len(layers) >= 2 else inp.ground_elev_m
        if toe_layer is None:
            warnings.append("Không xác định được lớp đá tại mũi để kiểm tra điều kiện Qp=2.5qu.")
            return ctx, warnings

        ctx["toe_good_rock"] = int(getattr(toe_layer, "soil_type", 0) or 0) == 3
        if ctx["toe_good_rock"] and toe_top is not None:
            ctx["socket_depth_good_m"] = max(float(toe_top) - tip, 0.0)
            ctx["socket_ok"] = ctx["socket_depth_good_m"] > 1.5 * D + 1e-9

        # Kiểm tra đoạn 2B dưới mũi có phủ đủ địa tầng và toàn bộ là đá tốt loại 3 hay không.
        coverage = 0.0
        has_bad = False
        top = inp.ground_elev_m
        for ly in layers:
            bottom = ly.bottom_elev_m
            ov = _interval_overlap_len(top, bottom, tip, check_bot)
            if ov > 1e-9:
                coverage += ov
                if int(getattr(ly, "soil_type", 0) or 0) != 3:
                    has_bad = True
            top = bottom
            if bottom <= check_bot:
                break
        ctx["coverage_2b_m"] = coverage
        ctx["good_rock_2b"] = (coverage >= 2.0 * D - 1e-8) and not has_bad

        if not ctx["joint_ok"]:
            warnings.append("Không dùng Qp=2.5qu: điều kiện khe nứt đá không phải khe nứt khép kín/không chèn lấp.")
        if not ctx["construction_ok"]:
            warnings.append("Không dùng Qp=2.5qu: điều kiện thi công đang là có chống đỡ/không tương ứng thành hố đá ổn định.")
        if not ctx["toe_good_rock"]:
            warnings.append("Không dùng Qp=2.5qu: mũi không nằm trong lớp đá tốt loại 3.")
        if not ctx["good_rock_2b"]:
            warnings.append(f"Không dùng Qp=2.5qu: chưa chứng minh đá tốt liên tục trong 2B dưới mũi; cần {2.0*D:.2f} m, phủ {coverage:.2f} m.")
        if not ctx["socket_ok"]:
            warnings.append(f"Không dùng Qp=2.5qu: chiều sâu ngàm vào đá tốt {ctx['socket_depth_good_m']:.2f} m ≤ 1.5B={1.5*D:.2f} m.")

        ctx["use_25qu"] = bool(ctx["joint_ok"] and ctx["construction_ok"] and ctx["toe_good_rock"] and ctx["good_rock_2b"] and ctx["socket_ok"])
        return ctx, warnings

    @staticmethod
    def _rock_hb_tip_qp_mpa(inp: PileInput, toe: SoilLayer, sigma_tip_mpa: float) -> Tuple[float, Dict[str, Any], str, List[str]]:
        """Tính Qp mũi đá theo Hoek-Brown và giới hạn qp <= 2.5qu nếu chưa có thử tải."""
        warnings: List[str] = []
        qu = max(float(getattr(toe, "qu_mpa", 0.0) or 0.0), 0.0)
        if qu <= 0.0:
            return 0.0, {"qp_mpa": 0.0, "qp_uncapped_mpa": 0.0, "qp_limit_25qu_mpa": 0.0, "hb_capped": False}, "Thiếu qu đá; không tính Qp Hoek-Brown", ["Mũi đá thiếu qu, không tính được Qp theo Hoek-Brown."]
        qp_raw, hb = hoek_brown_qp(sigma_tip_mpa, qu, toe.mi, toe.gsi, toe.disturbance)
        qp_limit = 2.5 * qu
        allow_exceed = bool(getattr(inp, "allow_rock_tip_exceed_25qu", False))
        qp = qp_raw if allow_exceed else min(qp_raw, qp_limit)
        capped = (not allow_exceed) and qp_raw > qp_limit + 1e-9
        if capped:
            warnings.append(f"Qp Hoek-Brown={qp_raw:.3f} MPa > 2.5qu={qp_limit:.3f} MPa; đã giới hạn theo 2.5qu.")
        if allow_exceed and qp_raw > qp_limit + 1e-9:
            warnings.append("Đã bật cho phép Qp đá vượt 2.5qu; cần có thử tải/kinh nghiệm địa phương để bảo vệ giá trị này.")
        hb.update({"qp_mpa": qp, "qp_uncapped_mpa": qp_raw, "qp_limit_25qu_mpa": qp_limit, "hb_capped": capped, "allow_exceed_25qu": allow_exceed})
        note = "Mũi đá dùng Hoek-Brown/GSI"
        if capped:
            note += ", giới hạn Qp≤2.5qu"
        elif allow_exceed:
            note += ", cho phép vượt 2.5qu theo lựa chọn"
        return qp, hb, note, warnings

    @staticmethod
    def _weak_clay_below_tip_2d(inp: PileInput) -> Tuple[bool, List[str]]:
        """Kiểm tra Su<0.024 MPa trong phạm vi 2D dưới mũi cọc đất dính."""
        warnings: List[str] = []
        layers = SCTCalculator._sorted_layers(inp)
        if not layers:
            return False, warnings
        tip = inp.pile_tip_elev_m
        check_bot = tip - 2.0 * inp.diameter_m
        if min(ly.bottom_elev_m for ly in layers) > check_bot + 1e-9:
            warnings.append(f"Địa chất chưa phủ đủ 2D dưới mũi cọc đất dính: cần tới cao độ {check_bot:g} để kiểm tra Su<0.024 MPa.")
        top = inp.ground_elev_m
        weak = False
        for ly in layers:
            bottom = ly.bottom_elev_m
            if _interval_overlap_len(top, bottom, tip, check_bot) > 1e-9 and int(ly.soil_type or 0) == 2:
                c_mpa = ly.c_mpa if ly.c_mpa > 0 else ly.su_mpa
                n60 = SCTCalculator._n60_from_input(inp, ly)
                su = 0.006 * n60 if not inp.clay_use_c_phi else max(c_mpa, 0.0)
                if su < 0.024:
                    weak = True
                    warnings.append(f"Lớp {ly.name or '?'} trong phạm vi 2D dưới mũi có Su={su:.4f} MPa < 0.024 MPa; giảm Nc còn 0.67Nc.")
            top = bottom
            if bottom <= check_bot:
                break
        return weak, warnings

    @staticmethod
    def _tip_resistance(inp: PileInput, layer_results: List[LayerCalc]) -> Tuple[float, float, float, Dict[str, Any], List[str]]:
        warnings: List[str] = []
        toe = SCTCalculator._toe_layer(inp)
        if toe is None:
            return 0.0, 0.0, 0.0, {}, ["Chưa có lớp đất/đá tại mũi cọc."]
        layer_tops = SCTCalculator._layer_tops(inp)
        sigma_tip = SCTCalculator._sigma_v_eff_at(inp, inp.pile_tip_elev_m, layer_tops)
        L = inp.pile_length_m
        D = inp.diameter_m
        Ap = inp.area_m2
        c_mpa = toe.c_mpa if toe.c_mpa > 0 else toe.su_mpa
        n_toe60 = SCTCalculator._n60_from_input(inp, toe)
        n_toe160 = n1_60_corrected(n_toe60, sigma_tip, cap_to_n=False)
        su = 0.006 * n_toe60 if not inp.clay_use_c_phi else max(c_mpa, 0.0)
        st = toe.soil_type
        mode_l = (inp.mode + " " + inp.pile_type).lower()
        tip_info: Dict[str, Any] = {"toe_layer": toe.name, "soil_type": st, "sigma_tip_mpa": sigma_tip}
        qpf_kpa = 0.0
        qpn_kpa = 0.0
        note = ""

        is_sand = st in (1, 6)
        is_clay = st == 2
        is_intact_rock = st == 3
        is_fractured_rock = st == 4
        is_igm = st == 5
        if st == 0:
            warnings.append("Mũi cọc nằm trong lớp Không khí/Hang karst; không tính Qp và cần kiểm tra lại cao độ mũi/địa chất.")

        if is_intact_rock or is_fractured_rock:
            if not inp.include_rock_tip:
                qpn_kpa = 0.0
                qpf_kpa = 0.0
                note = "Mũi đặt trong đá: Bỏ qua sức kháng mũi, chỉ lấy sức kháng thân"
                tip_info.update({"rock_tip_case": "Bỏ qua sức kháng mũi đá", "qp_mpa": 0.0, "phi_qp": 0.0})
            else:
                # V0.2.32: chỉ dùng qp=2.5qu khi tự kiểm được điều kiện đá tốt/khe nứt/thi công/2B/ngàm 1.5B.
                # Nếu không thỏa, kể cả mũi đang nằm trong loại 3, chuyển sang Hoek-Brown/GSI và khống chế 2.5qu.
                if is_intact_rock:
                    rock_ctx, wctx = SCTCalculator._rock_tip_geology_conditions(inp)
                    tip_info.update({"rock_tip_conditions": rock_ctx})
                    if rock_ctx.get("use_25qu"):
                        qp_mpa = 2.5 * max(toe.qu_mpa, 0.0)
                        qpn_kpa = qp_mpa * 1000.0
                        qpf_kpa = qpn_kpa * PHI_ROCK_TIP
                        note = "Đá tốt: thỏa khe nứt/thi công/2B dưới mũi/ngàm >1.5B -> Qp=2.5qu"
                        tip_info.update({"rock_tip_case": "Đá tốt thỏa điều kiện 2.5qu", "qp_mpa": qp_mpa, "qp_limit_25qu_mpa": qp_mpa, "phi_qp": PHI_ROCK_TIP})
                    else:
                        warnings.extend(wctx)
                        qp_mpa, hb, hb_note, whb = SCTCalculator._rock_hb_tip_qp_mpa(inp, toe, sigma_tip)
                        warnings.extend(whb)
                        qpn_kpa = qp_mpa * 1000.0
                        qpf_kpa = qpn_kpa * PHI_ROCK_TIP
                        note = "Đá loại 3 nhưng không đủ điều kiện 2.5qu: " + hb_note
                        tip_info.update(hb)
                        tip_info.update({"rock_tip_case": "Hoek-Brown do không đủ điều kiện 2.5qu", "phi_qp": PHI_ROCK_TIP})
                else:
                    qp_mpa, hb, hb_note, whb = SCTCalculator._rock_hb_tip_qp_mpa(inp, toe, sigma_tip)
                    warnings.extend(whb)
                    qpn_kpa = qp_mpa * 1000.0
                    qpf_kpa = qpn_kpa * PHI_ROCK_TIP
                    note = "Đá nứt vỡ/phong hóa: " + hb_note
                    tip_info.update(hb)
                    tip_info.update({"rock_tip_case": "Đá nứt vỡ/phong hóa Hoek-Brown", "phi_qp": PHI_ROCK_TIP})
        elif is_igm:
            qu = toe.qu_mpa
            socket_depth = inp.rock_socket_depth_m if inp.rock_socket_depth_m is not None else max(0.0, inp.pile_tip_elev_m - toe.bottom_elev_m)
            qpn_kpa, extra, note = igm_tip_nominal_kpa(n_toe60, qu, inp.crack_spacing_mm, inp.crack_width_mm, inp.diameter_m, socket_depth, str(getattr(inp, "igm_missing_qu_policy", "require_qu")).lower() == "use_spt")
            phi_qp = SCTCalculator._tip_phi(inp, 5, LIMIT_STATE_STRENGTH, n_toe60)
            qpf_kpa = qpn_kpa * phi_qp
            tip_info.update(extra)
            tip_info.update({"qp_mpa": qpn_kpa / 1000.0, "phi_qp": phi_qp, "N60": n_toe60})
        elif is_sand:
            if SCTCalculator._is_driven(inp):
                toe_top, db_embed_m = SCTCalculator._toe_layer_top_and_embedment(inp, toe)
                db_over_d = db_embed_m / max(inp.diameter_m, 1e-9)
                soil_text = f"{getattr(toe, 'name', '')} {getattr(toe, 'comment', '')}"
                qpn_kpa, extra, note = driven_sand_tip_nominal_kpa(n_toe160, db_over_d, soil_text)
                phi_qp = PHI_DRIVEN_TIP_SAND
                tip_info.update(extra)
                tip_info.update({"N60": n_toe60, "N160": n_toe160, "toe_layer_top_m": toe_top, "toe_embedment_m": db_embed_m, "qp_mpa": qpn_kpa / 1000.0, "phi_qp": phi_qp})
            else:
                n_toe = n_toe60
                # Cọc khoan trong đất rời: qp=0.057N60, giới hạn 3.0MPa nếu không có thử tải.
                # QA fix P2: công thức chỉ có hiệu lực với N60 <= 50 theo TCVN 11823-10.
                if n_toe > 50.0:
                    warnings.append(f"Mũi cọc khoan trong đất rời có N60={n_toe:.0f} > 50: công thức qp=0.057N60 chỉ hiệu lực với N60<=50; xem xét khai lớp mũi là IGM (loại 5).")
                qp_mpa = min(0.057 * n_toe, 3.0)
                phi_qp = PHI_BORE_TIP_SAND
                qpn_kpa = qp_mpa * 1000.0
                note = "Cọc khoan đất rời/cuội sỏi: qp=min(0.057N60,3.0MPa)"
                tip_info.update({"N60": n_toe, "qp_mpa": qp_mpa, "phi_qp": phi_qp})
            qpf_kpa = qpn_kpa * phi_qp
        elif is_clay:
            driven_tip = SCTCalculator._is_driven(inp)
            phi_qp = PHI_DRIVEN_TIP_CLAY if driven_tip else PHI_BORE_TIP_CLAY
            if driven_tip and not inp.clay_use_c_phi:
                qp_mpa = 9.0 * su
                qpn_kpa = qp_mpa * 1000.0
                note = "Cọc đóng/ép - đất dính: qp=9Su"
                tip_info.update({"Nc": 9.0, "Su_mpa": su, "qp_uncapped_mpa": qp_mpa, "qp_mpa": qp_mpa, "phi_qp": phi_qp})
            elif inp.clay_use_c_phi:
                qpn_kpa, extra, note = clay_c_phi_tip_nominal_kpa(c_mpa, toe.phi_deg, sigma_tip)
                tip_info.update(extra)
                qp_mpa = qpn_kpa / 1000.0
            else:
                Nc0 = min(9.0, 6.0 * (1.0 + 0.2 * L / D))
                weak_2d, wweak = SCTCalculator._weak_clay_below_tip_2d(inp)
                warnings.extend(wweak)
                Nc = Nc0 * (2.0 / 3.0 if weak_2d else 1.0)
                qp_uncapped_mpa = Nc * su
                qp_mpa = min(qp_uncapped_mpa, 4.0)
                qpn_kpa = qp_mpa * 1000.0
                note = "Cọc khoan - đất dính: qp=Nc·Su ≤ 4.0MPa; kiểm Su<0.024MPa trong phạm vi 2D dưới mũi"
                tip_info.update({"Nc": Nc, "Nc0": Nc0, "Su_mpa": su, "weak_clay_2D": weak_2d, "qp_uncapped_mpa": qp_uncapped_mpa, "qp_cap_mpa": 4.0, "qp_capped": qp_uncapped_mpa > 4.0 + 1e-9})
                if qp_uncapped_mpa > 4.0 + 1e-9:
                    warnings.append(f"Qp đất dính Nc·Su={qp_uncapped_mpa:.3f} MPa > 4.0 MPa; đã giới hạn theo TCVN 11823-10.")
            qpf_kpa = qpn_kpa * phi_qp
            tip_info.update({"qp_mpa": qpn_kpa / 1000.0, "phi_qp": phi_qp})
        else:
            note = "Không có sức kháng mũi"

        phi_cd = SCTCalculator._tip_phi(inp, st, LIMIT_STATE_STRENGTH, n_toe60)
        phi_db = SCTCalculator._tip_phi(inp, st, LIMIT_STATE_EXTREME, n_toe60)
        if (is_intact_rock or is_fractured_rock) and not inp.include_rock_tip:
            phi_cd = 0.0
            phi_db = 0.0
        qpf_kpa = qpn_kpa * phi_cd
        qpf_ex_kpa = qpn_kpa * phi_db
        qpf_kn = qpf_kpa * Ap
        qpf_ex_kn = qpf_ex_kpa * Ap
        qpn_kn = qpn_kpa * Ap
        tip_info.update({
            "note": note, "qpf_kpa": qpf_kpa, "qpf_extreme_kpa": qpf_ex_kpa, "qpn_kpa": qpn_kpa,
            "Qpf_kn": qpf_kn, "Qpf_extreme_kn": qpf_ex_kn, "Qpn_kn": qpn_kn,
            "phi_qp_strength": phi_cd, "phi_qp_extreme": phi_db,
        })
        return qpf_kn, qpf_ex_kn, qpn_kn, tip_info, warnings

    @staticmethod
    def calculate(inp: PileInput) -> CapacityResult:
        warnings: List[str] = []
        if inp.pile_length_m <= 0:
            warnings.append("Chiều dài cọc <= 0. Kiểm tra cao độ đáy bệ và cao độ mũi cọc.")
        if not inp.layers:
            warnings.append("Chưa có lớp đất/đá.")
        if getattr(inp, "include_downdrag", False) and float(getattr(inp, "downdrag_factor", 0.0) or 0.0) <= 0.0:
            inp.downdrag_factor = SCTCalculator.default_downdrag_load_factor(inp)
        warnings += SCTCalculator._preprocess_layers(inp)
        warnings += SCTCalculator._validate_input(inp)
        layers, qsf_cd, qsf_db, qsn, w1 = SCTCalculator._skin_resistance(inp)
        warnings += w1
        qpf_cd, qpf_db, qpn, toe_info, w2 = SCTCalculator._tip_resistance(inp, layers)
        warnings += w2

        w_dry, w_eff, buoyancy = SCTCalculator.pile_weight_effective_kn(inp)

        # Group factor: không áp nhầm bảng cọc khoan đất rời cho cọc đóng/ép.
        # Hệ số nhóm được dùng cho sức kháng địa kỹ thuật quy đổi/cọc; W' không bị nhân fg.
        s_over_d = inp.spacing_m / max(inp.diameter_m, 1e-9)
        is_driven = SCTCalculator._is_driven(inp)
        for lr in layers:
            if inp.pile_count_in_group > 1 and lr.skin_length_m > 0:
                if is_driven and int(lr.soil_type or 0) in (1, 6):
                    fg_i, fg_note = 1.0, "fg cọc đóng/ép đất rời không dùng bảng cọc khoan"
                else:
                    fg_i, fg_note = group_factor_for_soil(lr.soil_type, s_over_d, inp.group_layout, inp.ignore_group_igm_rock)
            else:
                fg_i, fg_note = 1.0, "fg=1.0"
            lr.group_factor = fg_i
            if lr.skin_length_m > 0:
                lr.note = (lr.note + f"; {fg_note}={fg_i:.3f} theo S/D={s_over_d:.3f}").strip('; ')

        qsf_cd_group_side = sum(lr.qs_factored_kn * lr.group_factor for lr in layers)
        qsf_db_group_side = sum(lr.qs_extreme_kn * lr.group_factor for lr in layers)
        fg_cd_weighted = qsf_cd_group_side / qsf_cd if qsf_cd > 1e-9 else 1.0
        fg_db_weighted = qsf_db_group_side / qsf_db if qsf_db > 1e-9 else fg_cd_weighted
        qsup_cd = sum(lr.qs_uplift_factored_kn for lr in layers)
        qsup_db = sum(lr.qs_uplift_extreme_kn for lr in layers)
        downdrag_kn = sum(lr.downdrag_kn for lr in layers) if getattr(inp, "include_downdrag", False) else 0.0
        if downdrag_kn > 0:
            warnings.append(f"Đã tính ma sát âm DD={downdrag_kn:.2f} kN/cọc với γDD={inp.downdrag_factor:.2f}; DD được cộng vào tải nén và vùng DD bị loại khỏi ma sát dương.")

        def build_limit_state(code: str, qshaft: float, qtip: float, qshaft_uplift: float, fg_weighted: float) -> LimitStateCapacity:
            gross = qshaft + qtip
            net_before_dd = gross - w_eff
            # Áp fg cho sức kháng địa kỹ thuật của cọc đơn trong nhóm; trọng lượng cọc không nhân fg.
            group_gross = gross * fg_weighted
            group_net = group_gross - w_eff
            group_total_before_dd = group_net * max(inp.pile_count_in_group, 1)
            net = net_before_dd  # sức kháng không đổi; DD được cộng vào tải khi kiểm toán nén/FOS.
            group_total = group_total_before_dd
            # Quy ước nhổ: dùng qshaft_uplift đã nhân φup riêng; Qp không tham gia nhổ.
            # QA fix P4: trọng lượng bản thân là tải có lợi khi chống nhổ -> nhân γDC = 0.9.
            w_uplift = GAMMA_DC_UPLIFT * w_eff
            uplift_mag = qshaft_uplift + w_uplift
            uplift_signed = -uplift_mag
            uplift_group_total = (qshaft_uplift * fg_weighted + w_uplift) * max(inp.pile_count_in_group, 1)
            pr = SCTCalculator.structural_capacity_kn(inp, code)
            governing = min(net, group_net, pr) if pr > 0 else min(net, group_net)
            note = "Min([Q] cọc đơn theo đất nền, [Q] nhóm quy đổi/cọc, Pr vật liệu); tải kiểm toán nén được cộng thêm ma sát âm nếu bật option"
            return LimitStateCapacity(
                code=code, label=LIMIT_STATE_LABELS.get(code, code), qshaft_kn=qshaft, qtip_kn=qtip,
                compression_single_gross_kn=gross, pile_weight_effective_kn=w_eff, pile_weight_dry_kn=w_dry,
                buoyancy_kn=buoyancy, compression_single_net_kn=net, uplift_single_magnitude_kn=uplift_mag,
                uplift_single_signed_kn=uplift_signed, group_factor=fg_weighted, compression_group_single_gross_kn=group_gross,
                compression_group_single_net_kn=group_net, compression_group_total_kn=group_total, material_pr_kn=pr,
                governing_kn=governing, governing_note=note, qshaft_uplift_kn=qshaft_uplift,
                uplift_group_total_kn=uplift_group_total, downdrag_kn=downdrag_kn,
                compression_single_net_before_downdrag_kn=net_before_dd,
                compression_group_total_before_downdrag_kn=group_total_before_dd,
            )

        strength = build_limit_state(LIMIT_STATE_STRENGTH, qsf_cd, qpf_cd, qsup_cd, fg_cd_weighted)
        extreme = build_limit_state(LIMIT_STATE_EXTREME, qsf_db, qpf_db, qsup_db, fg_db_weighted)
        return CapacityResult(
            pile_input=inp, layers=layers, qshaft_nominal_kn=qsn, qtip_nominal_kn=qpn,
            strength=strength, extreme=extreme, warnings=warnings, toe_info=toe_info
        )


