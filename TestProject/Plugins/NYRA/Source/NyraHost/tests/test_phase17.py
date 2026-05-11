"""Phase 17 — finish Tier 2: A (local SD), B (marketplace), C (multiplayer)."""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nyrahost.external import local_sd as lsd
from nyrahost.marketplace import (
    DEFAULT_BASE_URL,
    Listing,
    MAX_BLOB_BYTES,
    MARKETPLACE_TRUST_ROOTS,
    MarketplaceClient,
    MarketplaceHandlers,
    verify_blob_signature,
)
from nyrahost.multiplayer import (
    ALLOWED_KINDS,
    EventEnvelope,
    LocalRoomBackend,
    Member,
    MultiplayerHandlers,
    Room,
)
from nyrahost.privacy_guard import PrivacyGuard


# ---------- 17-A on-device SD ----------

def test_probe_reports_missing_libs():
    """Sandbox has no torch / diffusers — probe must say so without raising."""
    a = lsd.probe_availability()
    # neither lib is installed in this sandbox
    assert a.diffusers is False
    assert a.torch is False
    assert a.usable is False
    assert "not installed" in " ".join(a.notes)


def test_local_inpaint_refuses_when_libs_missing(tmp_path):
    params = {
        "source_image_b64": base64.b64encode(b"src").decode(),
        "mask_b64": base64.b64encode(b"mask").decode(),
        "prompt": "anything",
        "project_saved": str(tmp_path),
    }
    out = asyncio.run(lsd.on_local_inpaint(params))
    assert out["error"]["code"] == -32070
    assert out["error"]["message"] == "local_sd_not_installed"


def test_local_inpaint_missing_source():
    out = asyncio.run(lsd.on_local_inpaint({"mask_b64": "x", "prompt": "y"}))
    assert out["error"]["code"] == -32602


def test_local_inpaint_oversize_prompt(tmp_path):
    params = {
        "source_image_b64": "AA==",
        "mask_b64": "AA==",
        "prompt": "x" * (lsd.MAX_PROMPT_CHARS + 1),
        "project_saved": str(tmp_path),
    }
    out = asyncio.run(lsd.on_local_inpaint(params))
    assert out["error"]["code"] == -32602


def test_local_sd_probe_handler():
    out = asyncio.run(lsd.on_probe({}))
    # Must return a usable bool — never raise
    assert "usable" in out
    assert isinstance(out["usable"], bool)


def test_local_sd_backend_load_pipeline_raises_without_libs():
    backend = lsd.LocalSDBackend()
    with pytest.raises(RuntimeError, match="diffusers"):
        backend._load_pipeline()


# ---------- 17-B marketplace ----------

def test_verify_signature_untrusted_key_rejected():
    # Random non-pinned key
    bad_key = "deadbeef" * 8
    assert verify_blob_signature(
        blob=b"hello",
        signature_hex="aa" * 64,
        public_key_hex=bad_key,
    ) is False


def test_verify_signature_pinned_key_with_real_ed25519():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_hex = pub.public_bytes_raw().hex()
    blob = b"hello-world"
    sig_hex = priv.sign(blob).hex()
    # Now treat pub_hex as a trust root
    trust = (pub_hex,)
    assert verify_blob_signature(
        blob=blob, signature_hex=sig_hex, public_key_hex=pub_hex,
        trust_roots=trust,
    ) is True


def test_marketplace_list_handler_network_error():
    async def fake_http_get(self, url, **k):
        raise RuntimeError("network unreachable")

    client = MarketplaceClient()
    # Patch _client to return an object whose async with yields a session
    # that fails on .get
    class _FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, **k): raise RuntimeError("network unreachable")
    client._http = _FakeClient()
    h = MarketplaceHandlers(client, user_tools_dir=Path("/tmp/x"))
    out = asyncio.run(h.on_list({"page": 0}))
    assert out["error"]["code"] == -32074


def test_marketplace_install_signature_invalid(tmp_path):
    bad_listing = {
        "listing_id": "abc",
        "download_url": "https://marketplace.nyra.ai/v1/listings/abc/blob",
        "signature_hex": "00" * 64,
        "public_key_hex": "11" * 32,   # not in trust roots
    }
    client = MarketplaceClient()
    # Replace download_blob to return a body that has a bad signature.
    async def _fake_download(self, listing):
        # Re-raise the same path the real code takes
        raise PermissionError("signature_invalid")
    with patch.object(MarketplaceClient, "download_blob", new=_fake_download):
        h = MarketplaceHandlers(client, user_tools_dir=tmp_path)
        out = asyncio.run(h.on_install(bad_listing))
    assert out["error"]["code"] == -32073


def test_marketplace_install_blob_too_large(tmp_path):
    listing = {
        "listing_id": "huge",
        "download_url": "https://marketplace.nyra.ai/x",
        "signature_hex": "00" * 64,
        "public_key_hex": "11" * 32,
    }
    async def _fake_download(self, listing):
        raise ValueError(f"blob exceeds {MAX_BLOB_BYTES} bytes")
    with patch.object(MarketplaceClient, "download_blob", new=_fake_download):
        h = MarketplaceHandlers(MarketplaceClient(), user_tools_dir=tmp_path)
        out = asyncio.run(h.on_install(listing))
    assert out["error"]["code"] == -32075


def test_marketplace_install_missing_field(tmp_path):
    h = MarketplaceHandlers(MarketplaceClient(), user_tools_dir=tmp_path)
    out = asyncio.run(h.on_install({"name": "x"}))
    assert out["error"]["code"] == -32602


def test_marketplace_uninstall_absent(tmp_path):
    h = MarketplaceHandlers(MarketplaceClient(), user_tools_dir=tmp_path)
    out = asyncio.run(h.on_uninstall({"listing_id": "nonexistent"}))
    assert out["removed"] is False


def test_marketplace_install_writes_file(tmp_path):
    blob = b"NYRA_TOOL = {'name': 'fake', 'description': 'demo', 'input_schema': {}}\nasync def execute(p, s=None, w=None): return {}\n"
    async def _fake_download(self, listing):
        return blob
    listing = {
        "listing_id": "good",
        "download_url": "https://marketplace.nyra.ai/x",
        "signature_hex": "00" * 64,
        "public_key_hex": MARKETPLACE_TRUST_ROOTS[0],
    }
    with patch.object(MarketplaceClient, "download_blob", new=_fake_download):
        h = MarketplaceHandlers(MarketplaceClient(), user_tools_dir=tmp_path)
        out = asyncio.run(h.on_install(listing))
    assert out["installed"] is True
    target = tmp_path / "market_good.py"
    assert target.exists()
    assert target.read_bytes() == blob


# ---------- 17-C multiplayer ----------

def test_mp_join_creates_room():
    b = LocalRoomBackend()
    member = Member(user_id="alice", display_name="Alice", joined_at=0.0)
    room = asyncio.run(b.join_room("r1", member))
    assert room.room_id == "r1"
    assert "alice" in room.members


def test_mp_post_event_assigns_monotonic_cursor():
    b = LocalRoomBackend()
    asyncio.run(b.join_room("r1", Member("u", "U", 0.0)))
    e1 = asyncio.run(b.post_event("r1", sender_id="u", kind="chat_turn", payload={"text": "hi"}))
    e2 = asyncio.run(b.post_event("r1", sender_id="u", kind="chat_turn", payload={"text": "again"}))
    assert e1.cursor == 1 and e2.cursor == 2


def test_mp_post_event_rejects_unknown_kind():
    b = LocalRoomBackend()
    asyncio.run(b.join_room("r1", Member("u", "U", 0.0)))
    with pytest.raises(ValueError, match="kind"):
        asyncio.run(b.post_event("r1", sender_id="u", kind="not_a_kind", payload={}))


def test_mp_post_event_rejects_huge_payload():
    b = LocalRoomBackend()
    asyncio.run(b.join_room("r1", Member("u", "U", 0.0)))
    huge = {"k": "x" * 100_000}
    with pytest.raises(ValueError, match="payload exceeds"):
        asyncio.run(b.post_event("r1", sender_id="u", kind="chat_turn", payload=huge))


def test_mp_poll_filters_by_cursor():
    b = LocalRoomBackend()
    asyncio.run(b.join_room("r1", Member("u", "U", 0.0)))
    asyncio.run(b.post_event("r1", sender_id="u", kind="chat_turn", payload={"i": 1}))
    asyncio.run(b.post_event("r1", sender_id="u", kind="chat_turn", payload={"i": 2}))
    asyncio.run(b.post_event("r1", sender_id="u", kind="chat_turn", payload={"i": 3}))
    out = asyncio.run(b.poll_events("r1", since_cursor=1, limit=10))
    assert [e.payload["i"] for e in out] == [2, 3]


def test_mp_handler_join_then_post():
    h = MultiplayerHandlers(LocalRoomBackend())
    j = asyncio.run(h.on_join({"room_id": "r1", "user_id": "alice", "display_name": "Alice"}))
    assert j["joined"] is True
    p = asyncio.run(h.on_post_event({
        "room_id": "r1", "kind": "chat_turn",
        "payload": {"text": "hello"},
    }))
    assert "event" in p


def test_mp_handler_post_to_unknown_room():
    h = MultiplayerHandlers(LocalRoomBackend())
    out = asyncio.run(h.on_post_event({
        "room_id": "ghost", "kind": "chat_turn", "payload": {},
    }))
    assert out["error"]["code"] == -32076


def test_mp_handler_bad_kind():
    h = MultiplayerHandlers(LocalRoomBackend())
    asyncio.run(h.on_join({"room_id": "r1"}))
    out = asyncio.run(h.on_post_event({
        "room_id": "r1", "kind": "shouting", "payload": {},
    }))
    assert out["error"]["code"] == -32602


def test_mp_high_water_in_poll():
    h = MultiplayerHandlers(LocalRoomBackend())
    asyncio.run(h.on_join({"room_id": "r1"}))
    for _ in range(3):
        asyncio.run(h.on_post_event({
            "room_id": "r1", "kind": "chat_turn", "payload": {},
        }))
    out = asyncio.run(h.on_poll_events({"room_id": "r1"}))
    assert out["high_water"] == 3


def test_mp_handler_list_rooms():
    h = MultiplayerHandlers(LocalRoomBackend())
    asyncio.run(h.on_join({"room_id": "r1"}))
    asyncio.run(h.on_join({"room_id": "r2"}))
    out = asyncio.run(h.on_list_rooms({}))
    room_ids = {r["room_id"] for r in out["rooms"]}
    assert {"r1", "r2"} == room_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
