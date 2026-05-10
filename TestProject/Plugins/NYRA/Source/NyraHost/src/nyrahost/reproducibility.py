"""nyrahost.reproducibility — Phase 14-A repro pin (Tier 2 moat).

Aura is closed SaaS so reproducibility across runs is whatever the
service guarantees (effectively nothing — model rev + temp + seed all
move silently). NYRA's wedge: pin a seed + temperature per
conversation so "do this again" produces byte-identical output.

Implementation: in-memory ReproPin store mirroring ModelPreference's
shape. Persistence is intentionally out of scope for v0 — the WS
panel re-pins on session restart from the user's saved preferences.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.reproducibility")

# Hard caps — Anthropic's `temperature` is documented 0.0..1.0;
# `seed` is a 64-bit int in the API. These caps are user-facing
# friendly defaults that prevent obviously-wrong inputs.
TEMP_MIN: Final[float] = 0.0
TEMP_MAX: Final[float] = 1.0
SEED_MIN: Final[int] = -1                 # -1 = unpinned (CLI default)
SEED_MAX: Final[int] = 0x7FFF_FFFF_FFFF_FFFF


@dataclass(frozen=True)
class ReproPin:
    seed: int = -1            # -1 means "unpinned"
    temperature: float = -1.0  # -1.0 means "unpinned"

    @property
    def has_seed(self) -> bool:
        return self.seed >= 0

    @property
    def has_temperature(self) -> bool:
        return 0.0 <= self.temperature <= 1.0


@dataclass
class ReproPinStore:
    """In-memory per-conversation seed + temperature pins."""

    _by_conv: dict[str, ReproPin] = field(default_factory=dict)

    def get(self, conv_id: str) -> ReproPin:
        return self._by_conv.get(conv_id, ReproPin())

    def set(self, conv_id: str, *, seed: Optional[int] = None,
            temperature: Optional[float] = None) -> bool:
        if not isinstance(conv_id, str) or not conv_id:
            log.warning("repro_bad_conv_id", conv_id=conv_id)
            return False
        cur = self.get(conv_id)
        new_seed = cur.seed if seed is None else int(seed)
        new_temp = cur.temperature if temperature is None else float(temperature)
        if new_seed != -1 and not (SEED_MIN <= new_seed <= SEED_MAX):
            log.warning("repro_seed_out_of_range", seed=new_seed)
            return False
        if new_temp != -1.0 and not (TEMP_MIN <= new_temp <= TEMP_MAX):
            log.warning("repro_temperature_out_of_range", temperature=new_temp)
            return False
        self._by_conv[conv_id] = ReproPin(seed=new_seed, temperature=new_temp)
        log.info("repro_pin_set", conv_id=conv_id,
                 seed=new_seed, temperature=new_temp)
        return True

    def clear(self, conv_id: str) -> bool:
        return self._by_conv.pop(conv_id, None) is not None

    def cli_args(self, conv_id: str) -> list[str]:
        """Argv fragment for the Claude CLI subprocess driver."""
        pin = self.get(conv_id)
        out: list[str] = []
        if pin.has_seed:
            # Claude CLI accepts --seed for deterministic sampling.
            out.extend(["--seed", str(pin.seed)])
        if pin.has_temperature:
            out.extend(["--temperature", str(pin.temperature)])
        return out


__all__ = [
    "ReproPin",
    "ReproPinStore",
    "TEMP_MIN", "TEMP_MAX", "SEED_MIN", "SEED_MAX",
]
