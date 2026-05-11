"""nyrahost.cost_forecaster — Phase 14-B token + cost estimator (Tier 2 moat).

Aura's relative-cost UI shows "Sonnet vs Opus" pills but never an
absolute number. NYRA's wedge: estimate the token spend of a
prompt + history BEFORE running, in the user's own subscription
units, so they can tune scope before clicking Send.

Token estimator: heuristic 4 chars / token (the standard upper
bound for English Latin-1; Claude's own tokenizer averages 3.5–4.5
depending on the corpus). Image attachments are estimated at
1290 tokens each (Claude's documented vision budget for a 1024-px
square at standard quality).

Pricing table is per the public Anthropic pricing page snapshot
captured 2026-04-21. The user's actual subscription may metering
differently (Pro tier flat-rate users see no per-token charge); the
forecaster's job is "give me an order-of-magnitude" not "exact bill".
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.cost_forecaster")

# Heuristic: 4 chars per token (Latin alphabets); Claude's tokenizer
# typically yields 3.5–4.5 chars/tok on English prose.
CHARS_PER_TOKEN: Final[float] = 4.0
TOKENS_PER_IMAGE: Final[int] = 1290   # Claude vision budget per 1024-px square


@dataclass(frozen=True)
class ModelPrice:
    """USD per 1M tokens, per Anthropic public pricing 2026-04-21."""

    model: str
    input_per_million: float
    output_per_million: float


# Closed set; keeps NYRA's display from drifting on stale prices.
PRICE_TABLE: Final[dict[str, ModelPrice]] = {
    "claude-haiku-4-5":  ModelPrice("claude-haiku-4-5",  1.0,  5.0),
    "claude-sonnet-4-6": ModelPrice("claude-sonnet-4-6", 3.0, 15.0),
    "claude-opus-4-7":   ModelPrice("claude-opus-4-7",  15.0, 75.0),
}


@dataclass(frozen=True)
class Forecast:
    input_tokens: int
    output_tokens_estimate: int
    model: str
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    on_subscription: bool   # Pro tier flat-rate? (cosmetic — caller flag)


def estimate_tokens(content: str, *, image_count: int = 0) -> int:
    """Estimate input tokens for a chat turn."""
    if not isinstance(content, str):
        content = str(content)
    text_tokens = math.ceil(len(content) / CHARS_PER_TOKEN)
    return text_tokens + image_count * TOKENS_PER_IMAGE


def forecast(
    *,
    content: str,
    history_chars: int = 0,
    image_count: int = 0,
    model: str = "claude-sonnet-4-6",
    expected_output_tokens: int = 1500,
    on_subscription: bool = True,
) -> Forecast:
    """Forecast cost for one round-trip.

    Args:
      content                 — current user prompt
      history_chars           — characters of prior conversation context
      image_count             — image attachments
      model                   — Claude model slug
      expected_output_tokens  — estimated assistant reply size
      on_subscription         — True when the user's pinned model is on
                                their Pro subscription (cosmetic flag;
                                actual billing unaffected)

    Returns a Forecast dataclass. Unknown models fall back to Sonnet
    pricing with a warning logged — never silently zero.
    """
    price = PRICE_TABLE.get(model)
    if price is None:
        log.warning("cost_forecast_unknown_model", model=model)
        price = PRICE_TABLE["claude-sonnet-4-6"]
    in_tok = estimate_tokens(content, image_count=image_count) + math.ceil(
        history_chars / CHARS_PER_TOKEN
    )
    out_tok = max(0, int(expected_output_tokens))
    in_cost = in_tok / 1_000_000 * price.input_per_million
    out_cost = out_tok / 1_000_000 * price.output_per_million
    return Forecast(
        input_tokens=in_tok,
        output_tokens_estimate=out_tok,
        model=price.model,
        input_cost_usd=round(in_cost, 4),
        output_cost_usd=round(out_cost, 4),
        total_cost_usd=round(in_cost + out_cost, 4),
        on_subscription=bool(on_subscription),
    )


__all__ = [
    "Forecast",
    "ModelPrice",
    "PRICE_TABLE",
    "CHARS_PER_TOKEN",
    "TOKENS_PER_IMAGE",
    "estimate_tokens",
    "forecast",
]
