"""nyrahost.external.local_sd — Phase 17-A on-device Stable Diffusion adapter.

Tier 2 privacy moat. Aura is closed SaaS; their image gen runs
server-side. NYRA's wedge for studios under NDA: same inpaint
contract as the ComfyUI path, but the inference runs in-process on
the user's GPU with no outbound HTTP.

Wiring contract:
  * Lazy-imports ``diffusers`` + ``torch`` only when the user
    actually invokes the local backend. If either is missing, the
    handler returns ``-32070 local_sd_not_installed`` with a
    remediation pointing at ``pip install diffusers torch``.
  * Privacy Mode (Phase 15-E ``GUARD``) is honoured implicitly:
    no network calls happen in this module. We download model
    weights only when explicitly invoked, gated by the user's
    explicit "Download model" click — never silently on idle.
  * Output shape matches the ComfyUI inpaint return:
    ``{"job_id", "image_path", "all_images"}`` so the existing
    chat-handler render path doesn't change.

Engineering ceiling: this module is the *adapter*. Actual model
loading + sampling happens in the optional dependency; if NYRA
ships without those wheels in the cache, the handler refuses
cleanly. The next step (founder-side) is to add ``diffusers`` +
``torch`` to ``requirements.lock`` and re-run prebuild.ps1.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.external.local_sd")

ERR_NOT_INSTALLED: Final[int] = -32070
ERR_INFER_FAILED: Final[int] = -32071
ERR_BAD_INPUT: Final[int] = -32602

# Hard cap mirrors the ComfyUI inpaint workflow (same SDXL latent budget).
DEFAULT_STEPS: Final[int] = 30
DEFAULT_CFG: Final[float] = 7.0
DEFAULT_DENOISE: Final[float] = 0.85
MAX_PROMPT_CHARS: Final[int] = 8 * 1024


@dataclass(frozen=True)
class LocalSDAvailability:
    """Result of probing the user's Python install for diffusers + torch."""

    diffusers: bool
    torch: bool
    cuda: bool
    notes: tuple[str, ...] = ()

    @property
    def usable(self) -> bool:
        return self.diffusers and self.torch

    def to_dict(self) -> dict:
        return {
            "diffusers": self.diffusers,
            "torch": self.torch,
            "cuda": self.cuda,
            "notes": list(self.notes),
            "usable": self.usable,
        }


def probe_availability() -> LocalSDAvailability:
    """Probe without raising. Lazy-imports both libs."""
    notes: list[str] = []
    diffusers_ok = False
    torch_ok = False
    cuda_ok = False
    try:
        importlib.import_module("diffusers")
        diffusers_ok = True
    except ModuleNotFoundError:
        notes.append("diffusers not installed")
    try:
        torch = importlib.import_module("torch")
        torch_ok = True
        try:
            cuda_ok = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
        except Exception:  # noqa: BLE001
            cuda_ok = False
    except ModuleNotFoundError:
        notes.append("torch not installed")
    return LocalSDAvailability(
        diffusers=diffusers_ok,
        torch=torch_ok,
        cuda=cuda_ok,
        notes=tuple(notes),
    )


def _err(code: int, message: str, detail: str = "", remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


class LocalSDBackend:
    """Lazy-load wrapper around diffusers.StableDiffusionInpaintPipeline."""

    def __init__(self, *, model_id: str = "runwayml/stable-diffusion-inpainting",
                 cache_dir: Path | None = None) -> None:
        self._model_id = model_id
        self._cache_dir = cache_dir
        self._pipe = None
        self._availability: LocalSDAvailability | None = None

    def _check_available(self) -> LocalSDAvailability:
        if self._availability is None:
            self._availability = probe_availability()
        return self._availability

    def _load_pipeline(self):
        """Build the diffusers pipeline; deferred to first call."""
        a = self._check_available()
        if not a.usable:
            raise RuntimeError(
                f"diffusers + torch required for on-device SD; got {a.to_dict()}"
            )
        import torch  # noqa: PLC0415 — lazy
        from diffusers import StableDiffusionInpaintPipeline  # noqa: PLC0415
        if self._pipe is None:
            self._pipe = StableDiffusionInpaintPipeline.from_pretrained(
                self._model_id,
                cache_dir=str(self._cache_dir) if self._cache_dir else None,
                torch_dtype=torch.float16 if a.cuda else torch.float32,
            )
            if a.cuda:
                self._pipe = self._pipe.to("cuda")
        return self._pipe

    async def inpaint(
        self,
        *,
        source_bytes: bytes,
        mask_bytes: bytes,
        prompt: str,
        negative_prompt: str = "",
        steps: int = DEFAULT_STEPS,
        cfg: float = DEFAULT_CFG,
        denoise: float = DEFAULT_DENOISE,
        seed: int = -1,
        output_path: Path,
    ) -> Path:
        """Run inpaint synchronously inside an executor thread.

        Diffusers is CPU/GPU-bound, not async — we wrap the call so
        asyncio dispatch isn't blocked.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._inpaint_blocking,
            source_bytes, mask_bytes, prompt, negative_prompt,
            steps, cfg, denoise, seed, output_path,
        )

    def _inpaint_blocking(self, source_bytes, mask_bytes, prompt, negative,
                          steps, cfg, denoise, seed, output_path: Path) -> Path:
        from io import BytesIO   # noqa: PLC0415
        from PIL import Image    # noqa: PLC0415 — Pillow ships with diffusers
        import torch             # noqa: PLC0415
        pipe = self._load_pipeline()
        src = Image.open(BytesIO(source_bytes)).convert("RGB")
        mask = Image.open(BytesIO(mask_bytes)).convert("L")
        generator = torch.Generator(device="cpu")
        if seed >= 0:
            generator = generator.manual_seed(int(seed))
        result = pipe(
            prompt=prompt,
            negative_prompt=negative or None,
            image=src,
            mask_image=mask,
            num_inference_steps=int(steps),
            guidance_scale=float(cfg),
            strength=float(denoise),
            generator=generator,
        )
        out_img = result.images[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_img.save(output_path, format="PNG")
        return output_path


async def on_local_inpaint(params: dict, session=None, ws=None) -> dict:
    """``inpaint/submit_local`` handler — same param shape as ComfyUI path
    but no upload, no remote HTTP."""
    import base64                # noqa: PLC0415
    src_b64 = params.get("source_image_b64")
    mask_b64 = params.get("mask_b64")
    prompt = params.get("prompt", "")
    if not isinstance(src_b64, str) or not src_b64:
        return _err(ERR_BAD_INPUT, "missing_field", "source_image_b64")
    if not isinstance(mask_b64, str) or not mask_b64:
        return _err(ERR_BAD_INPUT, "missing_field", "mask_b64")
    if not isinstance(prompt, str) or len(prompt) > MAX_PROMPT_CHARS:
        return _err(ERR_BAD_INPUT, "bad_prompt")
    project_saved = params.get("project_saved") or os.environ.get("NYRA_PROJECT_SAVED") or "."
    job_id = str(uuid.uuid4())
    out_path = Path(project_saved) / "NYRA" / "inpaint_local" / job_id / "result.png"

    backend = LocalSDBackend(
        model_id=params.get("model_id", "runwayml/stable-diffusion-inpainting"),
    )
    a = backend._check_available()
    if not a.usable:
        return _err(
            ERR_NOT_INSTALLED, "local_sd_not_installed", "; ".join(a.notes),
            remediation=(
                "Install diffusers + torch into the NyraHost venv: "
                "`pip install diffusers torch --index-url <pytorch-cuda-index>`. "
                "GPU not required but strongly recommended."
            ),
        )

    try:
        result_path = await backend.inpaint(
            source_bytes=base64.b64decode(src_b64),
            mask_bytes=base64.b64decode(mask_b64),
            prompt=prompt,
            negative_prompt=params.get("negative_prompt", "") or "",
            steps=int(params.get("steps", DEFAULT_STEPS)),
            cfg=float(params.get("cfg", DEFAULT_CFG)),
            denoise=float(params.get("denoise", DEFAULT_DENOISE)),
            seed=int(params.get("seed", -1)),
            output_path=out_path,
        )
    except (RuntimeError, ValueError, OSError) as exc:
        return _err(ERR_INFER_FAILED, "local_sd_infer_failed", str(exc))
    return {
        "job_id": job_id,
        "image_path": str(result_path),
        "all_images": [str(result_path)],
        "backend": "local_sd",
    }


async def on_probe(params: dict, session=None, ws=None) -> dict:
    return probe_availability().to_dict()


__all__ = [
    "LocalSDAvailability",
    "LocalSDBackend",
    "probe_availability",
    "on_local_inpaint",
    "on_probe",
    "ERR_NOT_INSTALLED",
    "ERR_INFER_FAILED",
    "ERR_BAD_INPUT",
    "MAX_PROMPT_CHARS",
]
