"""cost/forecast WS handler — Phase 14-B."""
from __future__ import annotations

from typing import Final, Optional

from nyrahost.cost_forecaster import Forecast, PRICE_TABLE, forecast

ERR_BAD_INPUT: Final[int] = -32602


def _err(code: int, message: str, detail: str = "") -> dict:
    out: dict = {"error": {"code": code, "message": message}}
    if detail:
        out["error"]["data"] = {"detail": detail}
    return out


class CostHandlers:
    async def on_forecast(self, params: dict, session=None, ws=None) -> dict:
        content = params.get("content")
        if not isinstance(content, str):
            return _err(ERR_BAD_INPUT, "missing_field", "content")
        try:
            f: Forecast = forecast(
                content=content,
                history_chars=int(params.get("history_chars", 0)),
                image_count=int(params.get("image_count", 0)),
                model=params.get("model", "claude-sonnet-4-6"),
                expected_output_tokens=int(params.get("expected_output_tokens", 1500)),
                on_subscription=bool(params.get("on_subscription", True)),
            )
        except (TypeError, ValueError) as exc:
            return _err(ERR_BAD_INPUT, "bad_value", str(exc))
        return {
            "model": f.model,
            "input_tokens": f.input_tokens,
            "output_tokens_estimate": f.output_tokens_estimate,
            "input_cost_usd": f.input_cost_usd,
            "output_cost_usd": f.output_cost_usd,
            "total_cost_usd": f.total_cost_usd,
            "on_subscription": f.on_subscription,
        }

    async def on_price_table(self, params: dict, session=None, ws=None) -> dict:
        return {
            "models": [
                {
                    "model": m.model,
                    "input_per_million_usd": m.input_per_million,
                    "output_per_million_usd": m.output_per_million,
                }
                for m in PRICE_TABLE.values()
            ],
        }


__all__ = ["CostHandlers", "ERR_BAD_INPUT"]
