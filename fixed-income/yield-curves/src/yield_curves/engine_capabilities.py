"""Internal support contract for shared curve-construction engines.

Capabilities authorize a caller-selected method; they do not select policy or
construct representations. The domain factory remains in ``curves``.
"""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from .curves import CurveInterpolationMethod


class CurveConstructionEngine(StrEnum):
    SEQUENTIAL = "sequential bootstrap"
    SIMULTANEOUS = "simultaneous nodal calibration"


@dataclass(frozen=True, slots=True)
class MethodCapabilities:
    sequential: bool
    simultaneous: bool


METHOD_CAPABILITIES = MappingProxyType({
    CurveInterpolationMethod.LOG_LINEAR_DF: MethodCapabilities(True, True),
    CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO: MethodCapabilities(True, True),
    CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO: MethodCapabilities(False, True),
    CurveInterpolationMethod.PCHIP_CONTINUOUS_ZERO: MethodCapabilities(False, True),
})


def supports(
    method: CurveInterpolationMethod,
    engine: CurveConstructionEngine,
) -> bool:
    """Return explicit support, rejecting unknown methods and engines."""
    try:
        capabilities = METHOD_CAPABILITIES[method]
    except (KeyError, TypeError):
        raise ValueError(f"Unknown interpolation method: {method}") from None
    engine = CurveConstructionEngine(engine)
    if engine is CurveConstructionEngine.SEQUENTIAL:
        return capabilities.sequential
    return capabilities.simultaneous


def require_supported_method(
    method: CurveInterpolationMethod,
    engine: CurveConstructionEngine,
) -> None:
    """Reject unsupported combinations before instrument preparation or solve."""
    if not supports(method, engine):
        raise ValueError(
            f"{method} is not supported by the {CurveConstructionEngine(engine).value}."
        )
