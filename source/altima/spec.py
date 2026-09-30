"""Vehicle specification for a 2000 Nissan Altima (L30) 4-door sedan.

Coordinate system (Blender, Z-up):
    +X = forward (nose), -X = rear
    +Y = LEFT side of car (US driver side, LHD), -Y = RIGHT
    +Z = up, Z=0 = ground plane
    Origin = midpoint of wheelbase, on the ground.
All units are metres (1.0 = 1 m).
"""

# ----------------------------------------------------------------------------- envelope
LENGTH      = 4.720      # 185.8 in  (2000-01 model year)
WIDTH       = 1.755      # 69.1 in
HEIGHT      = 1.420      # 55.9 in
WHEELBASE   = 2.620      # 103.1 in
AXLE_F      =  1.380
AXLE_R      = -1.240
TRACK_F     = 1.506      # 59.3 in
TRACK_R     = 1.506
WHEEL_R     = 0.3135     # 205/60R15  ->  627 mm rolling diameter
WHEEL_W     = 0.205
RIM_D       = 0.381      # 15 inch
ARCH_R      = 0.400      # wheel-arch opening radius
TIRE_OEM    = "205/60R15"

# The station table is authored in "design space"; the 2000 model year is 59 mm
# longer than the 1997-99 car, so the nose and tail are pushed out while every
# station between the axles stays exactly where it is.
X_EXT = 0.030
X_EXT_A = 1.860


def xmap(x):
    """Design-space x -> world-space x (stretches only outboard of the fenders)."""
    if x > X_EXT_A:
        return x + X_EXT * min(1.0, (x - X_EXT_A) / (2.330 - X_EXT_A))
    if x < -X_EXT_A:
        return x - X_EXT * min(1.0, (-x - X_EXT_A) / (2.330 - X_EXT_A))
    return x


def dxmap(xw):
    """World-space x -> design-space x (inverse of xmap)."""
    if xw > X_EXT_A:
        return X_EXT_A + (xw - X_EXT_A) * (2.330 - X_EXT_A) / (2.330 - X_EXT_A + X_EXT)
    if xw < -X_EXT_A:
        return -X_EXT_A + (xw + X_EXT_A) * (2.330 - X_EXT_A) / (2.330 - X_EXT_A + X_EXT)
    return xw


def wmap(xd):
    """Alias used by the panel module (design space -> world space)."""
    return xmap(xd)

# ----------------------------------------------------------------------------- ring topology
RING_N   = 45            # number of points in one closed cross-section ring
TOP_I0   = 8             # first ring index of the "top arc" (right shoulder)
TOP_I1   = 36            # last  ring index of the "top arc" (left shoulder)
TOP_K    = TOP_I1 - TOP_I0 + 1          # 29
BELT_R   = 8.0           # ring index of the belt line, RIGHT side  (-Y)
BELT_L   = 36.0          # ring index of the belt line, LEFT  side  (+Y)
RAIL_L   = 33.4          # ring index of the roof-rail / side-glass top, LEFT
RAIL_R   = 44.0 - RAIL_L # 10.6  (mirror)

def mirror_i(i):
    """Ring index mirrored across the car centreline."""
    return (44.0 - i) % 45.0

# ----------------------------------------------------------------------------- longitudinal control stations
# Each station is (x, params...) with:
#   z_bot      bottom of the rocker / underbody at that station
#   hw_low     half-width at the underbody edge
#   z_rocker   sill (rocker) top height
#   hw_max     maximum half-width (widest point of the section)
#   z_low_side height of the widest point
#   z_belt     belt-line (shoulder) height
#   hw_top     half-width at the base of the top arc
#   z_top      height of the top arc at the centreline
#   n_top      super-ellipse exponent controlling how flat the top arc is
#   a_top      width exponent (1.0 = linear, <1 = wide crown)
#   m_top      vertical fullness exponent
FIELDS = ("x", "z_bot", "hw_low", "z_rocker", "hw_max", "z_low_side",
          "z_belt", "hw_top", "z_top", "n_top", "a_top", "m_top")

STATIONS_FRONT_TO_REAR = [
    ( 2.330, 0.340, 0.260, 0.500, 0.360, 0.620, 0.720, 0.300, 0.790, 2.20, 0.90, 1.50),
    ( 2.290, 0.300, 0.400, 0.510, 0.560, 0.630, 0.790, 0.450, 0.845, 2.20, 0.95, 1.50),
    ( 2.230, 0.262, 0.540, 0.522, 0.700, 0.640, 0.836, 0.600, 0.880, 2.20, 1.00, 1.50),
    ( 2.140, 0.235, 0.640, 0.535, 0.795, 0.650, 0.868, 0.722, 0.906, 2.20, 1.00, 1.50),
    ( 2.050, 0.222, 0.690, 0.548, 0.840, 0.660, 0.890, 0.800, 0.925, 2.25, 1.00, 1.55),
    ( 1.960, 0.214, 0.712, 0.560, 0.860, 0.675, 0.906, 0.838, 0.941, 2.30, 1.00, 1.55),
    ( 1.860, 0.210, 0.720, 0.575, 0.870, 0.692, 0.920, 0.852, 0.954, 2.35, 1.00, 1.55),
    ( 1.700, 0.208, 0.724, 0.592, 0.877, 0.710, 0.940, 0.862, 0.970, 2.40, 1.00, 1.55),
    ( 1.500, 0.205, 0.726, 0.604, 0.8775,0.718, 0.958, 0.866, 0.982, 2.40, 1.00, 1.55),
    ( 1.250, 0.203, 0.726, 0.612, 0.8775,0.720, 0.974, 0.868, 0.992, 2.45, 0.98, 1.55),
    ( 1.000, 0.202, 0.726, 0.618, 0.8775,0.722, 0.984, 0.869, 0.999, 2.50, 0.94, 1.55),
    ( 0.800, 0.201, 0.726, 0.622, 0.8775,0.724, 0.991, 0.869, 1.004, 2.50, 0.90, 1.55),
    ( 0.680, 0.200, 0.726, 0.624, 0.8775,0.726, 0.997, 0.868, 1.010, 2.55, 0.86, 1.55),
    ( 0.600, 0.200, 0.726, 0.625, 0.8775,0.728, 1.001, 0.864, 1.028, 2.70, 0.82, 1.55),
    ( 0.500, 0.200, 0.726, 0.626, 0.8775,0.730, 1.004, 0.852, 1.090, 3.20, 0.75, 1.50),
    ( 0.400, 0.200, 0.726, 0.627, 0.8775,0.732, 1.006, 0.836, 1.152, 3.70, 0.68, 1.50),
    ( 0.300, 0.200, 0.726, 0.628, 0.8775,0.734, 1.007, 0.818, 1.213, 4.30, 0.62, 1.50),
    ( 0.200, 0.200, 0.726, 0.630, 0.8775,0.736, 1.008, 0.800, 1.272, 5.00, 0.56, 1.45),
    ( 0.100, 0.200, 0.726, 0.631, 0.8775,0.738, 1.008, 0.780, 1.333, 5.80, 0.50, 1.40),
    ( 0.000, 0.200, 0.726, 0.632, 0.8775,0.740, 1.007, 0.762, 1.388, 6.60, 0.46, 1.35),
    (-0.100, 0.200, 0.726, 0.633, 0.8775,0.741, 1.006, 0.750, 1.412, 7.40, 0.43, 1.35),
    (-0.300, 0.200, 0.726, 0.634, 0.8775,0.742, 1.004, 0.738, 1.420, 8.40, 0.40, 1.30),
    (-0.600, 0.200, 0.726, 0.635, 0.8775,0.743, 1.002, 0.730, 1.419, 8.60, 0.40, 1.30),
    (-0.800, 0.201, 0.725, 0.635, 0.8775,0.744, 1.002, 0.726, 1.414, 8.20, 0.41, 1.30),
    (-0.900, 0.202, 0.725, 0.634, 0.8775,0.745, 1.002, 0.728, 1.398, 7.60, 0.43, 1.35),
    (-1.050, 0.203, 0.724, 0.632, 0.8775,0.746, 1.003, 0.746, 1.345, 6.40, 0.47, 1.40),
    (-1.200, 0.205, 0.722, 0.630, 0.8760,0.748, 1.004, 0.768, 1.290, 5.50, 0.52, 1.45),
    (-1.350, 0.207, 0.720, 0.628, 0.8740,0.750, 1.005, 0.790, 1.228, 4.70, 0.58, 1.50),
    (-1.480, 0.210, 0.718, 0.626, 0.8720,0.752, 1.006, 0.812, 1.163, 4.00, 0.64, 1.50),
    (-1.560, 0.213, 0.716, 0.625, 0.8700,0.754, 1.008, 0.828, 1.120, 3.50, 0.70, 1.50),
    (-1.700, 0.218, 0.714, 0.623, 0.8680,0.756, 1.010, 0.846, 1.093, 3.00, 0.78, 1.50),
    (-1.860, 0.222, 0.712, 0.620, 0.8660,0.758, 1.012, 0.856, 1.075, 2.70, 0.86, 1.50),
    (-2.020, 0.228, 0.706, 0.616, 0.8620,0.760, 1.014, 0.858, 1.060, 2.60, 0.90, 1.50),
    (-2.120, 0.235, 0.696, 0.610, 0.8540,0.755, 1.006, 0.848, 1.040, 2.50, 0.94, 1.50),
    (-2.200, 0.245, 0.678, 0.600, 0.8400,0.742, 0.984, 0.828, 1.012, 2.40, 0.97, 1.50),
    (-2.270, 0.262, 0.640, 0.585, 0.8120,0.720, 0.950, 0.792, 0.975, 2.30, 1.00, 1.50),
    (-2.310, 0.290, 0.560, 0.560, 0.7400,0.680, 0.900, 0.700, 0.928, 2.30, 1.00, 1.50),
    (-2.330, 0.340, 0.440, 0.520, 0.6000,0.630, 0.830, 0.520, 0.870, 2.20, 1.00, 1.50),
]

# ----------------------------------------------------------------------------- panel boundaries (X)
# Every value here becomes an exact station sample so panels have crisp shut lines.
PANEL_X = [
    2.330, 2.290, 2.230, 2.140, 2.050, 1.990, 1.940, 1.900, 1.860, 1.820,
    1.700, 1.600, 1.500, 1.400, 1.300, 1.250, 1.150, 1.050, 1.000, 0.900,
    0.800, 0.760, 0.720, 0.680, 0.660, 0.625, 0.600, 0.560, 0.500, 0.450,
    0.400, 0.350, 0.300, 0.240, 0.180, 0.120, 0.060, 0.000, -0.100, -0.200,
    -0.240, -0.290, -0.350, -0.400, -0.500, -0.600, -0.700, -0.800, -0.860,
    -0.900, -0.960, -1.050, -1.150, -1.240, -1.350, -1.440, -1.480, -1.560,
    -1.620, -1.700, -1.780, -1.860, -1.930, -2.000, -2.060, -2.120, -2.200,
    -2.270, -2.310, -2.330,
]

# ----------------------------------------------------------------------------- landmarks
X_NOSE        =  2.330
X_TAIL        = -2.330
X_HOOD_FRONT  =  1.900
X_HOOD_REAR   =  0.800     # hood / cowl shut line
X_COWL        =  0.660
X_WS_BASE     =  0.625     # windscreen base (belt line)
X_WS_TOP      =  0.060     # windscreen top / roof front
X_ROOF_REAR   = -0.860
X_BACKLIGHT_B = -1.520     # backlight base
X_TRUNK_FRONT = -1.560
X_TRUNK_REAR  = -2.060
X_REAR_FACE   = -2.330
X_BUMP_F      =  1.900     # front bumper cover rear edge
X_BUMP_R      = -2.000     # rear bumper cover front edge

# doors (shut lines)
X_DR_F_FRONT  =  0.600     # front door, front cut line (at A-pillar base)
X_DR_F_REAR   = -0.240     # front door, rear cut (B-pillar front)
X_DR_R_FRONT  = -0.290     # rear door, front cut (B-pillar rear)
X_DR_R_REAR   = -0.875     # rear door, rear cut
X_FENDER_F    =  1.990     # front fender, front tip
X_FENDER_R    =  1.115     # front fender, rear cut

# wheel arch centres
ARCH_F_CX     = AXLE_F
ARCH_R_CX     = AXLE_R
ARCH_CZ       = 0.300

# powertrain
ENGINE_CX     =  1.020     # engine bay centre (longitudinal)
ENGINE_CZ     =  0.520
TRANS_CX      =  0.130     # transaxle
EXH_CX        = -0.400

# cabin
FLOOR_Z       =  0.300
DASH_X        =  0.540
SEAT_F_X      = -0.150
SEAT_R_X      = -1.000     # rear bench centre


# ----------------------------------------------------------------------------- monotone cubic interpolation
def _pchip_slopes(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0] = d[0]
    m[-1] = d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0.0:
            m[i] = 0.0
        else:
            w1 = 2.0 * h[i] + h[i - 1]
            w2 = h[i] + 2.0 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    return m


class Pchip:
    """Monotone cubic (PCHIP) interpolator - smooth but never overshoots."""

    def __init__(self, xs, ys):
        pairs = sorted(zip(xs, ys))
        self.xs = [p[0] for p in pairs]
        self.ys = [p[1] for p in pairs]
        self.ms = _pchip_slopes(self.xs, self.ys)

    def __call__(self, x):
        xs, ys, ms = self.xs, self.ys, self.ms
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        lo, hi = 0, len(xs) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= x:
                lo = mid
            else:
                hi = mid
        h = xs[hi] - xs[lo]
        t = (x - xs[lo]) / h
        t2, t3 = t * t, t * t * t
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        return (h00 * ys[lo] + h10 * h * ms[lo]
                + h01 * ys[hi] + h11 * h * ms[hi])


# ----------------------------------------------------------------------------- station sampling
def build_stations(step=0.020, extra=()):
    """Return a dense, sorted list of x samples holding every control station,
    every panel boundary and a uniform fill."""
    rows = sorted(STATIONS_FRONT_TO_REAR, key=lambda r: r[0])
    x0, x1 = rows[0][0], rows[-1][0]
    xs = set()
    n = int((x1 - x0) / step) + 1
    for i in range(n + 1):
        xs.add(round(x0 + (x1 - x0) * i / n, 6))
    for r in rows:
        xs.add(round(r[0], 6))
    for v in PANEL_X:
        xs.add(round(v, 6))
    for v in extra:
        xs.add(round(v, 6))
    return sorted(xs)


class Vehicle:
    """Interpolated vehicle section parameters."""

    def __init__(self, step=0.020, extra=()):
        rows = sorted(STATIONS_FRONT_TO_REAR, key=lambda r: r[0])
        self.X = [r[0] for r in rows]
        self.curves = {}
        for k, name in enumerate(FIELDS):
            if name == "x":
                continue
            self.curves[name] = Pchip(self.X, [r[k] for r in rows])
        self.samples = build_stations(step, extra)

    def params(self, x):
        p = {"x": x}
        for name, c in self.curves.items():
            p[name] = c(x)
        return p