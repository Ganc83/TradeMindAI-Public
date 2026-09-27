import math
from numbers import Real

def finite(name, value, *, positive=False, minimum=None):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)): raise ValueError(f"{name} must be a finite number")
    if positive and value <= 0: raise ValueError(f"{name} must be positive")
    if minimum is not None and value < minimum: raise ValueError(f"{name} must be >= {minimum}")
def percent(name, value, *, allow_zero=True):
    finite(name, value)
    if value < 0 or value > 100 or (not allow_zero and value == 0): raise ValueError(f"{name} has an invalid percentage")
def text(name, value):
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{name} must be a non-empty string")
