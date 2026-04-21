# NYRA Handshake Protocol

**Status:** Locked in Phase 1 Plan 05. See CONTEXT.md D-06, D-07.

## File path

- **Primary:** `%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json`
- **Fallback (if LOCALAPPDATA unwritable):** `<ProjectDir>/Saved/NYRA/handshake-<editor-pid>.json`
- **Permissions (Windows NTFS):** DACL restricted to the current user SID (owner only read/write). NyraHost applies ACL after atomic rename.

## JSON schema (D-06 exact)

```json
{
    "port":          <integer>,       // ephemeral TCP port NyraHost bound via 127.0.0.1:0
    "token":         "<hex-string>",  // 64 hex chars (32 bytes from secrets.token_bytes)
    "nyrahost_pid":  <integer>,       // PID of python.exe running `-m nyrahost`
    "ue_pid":        <integer>,       // PID of the UE editor process that spawned NyraHost
    "started_at":    <integer>        // unix timestamp in MILLISECONDS (ms since epoch)
}
```

## Writer protocol (NyraHost side)

1. Bind `127.0.0.1:0` and capture assigned port.
2. Generate token via `secrets.token_bytes(32).hex()` -> 64 hex chars.
3. Start WS server's accept loop.
4. Open `%LOCALAPPDATA%/NYRA/handshake-<ue_pid>.json.tmp` for write.
5. `json.dump(payload, f)`, `f.flush()`, `os.fsync(f.fileno())`, `f.close()`.
6. `os.replace(tmp_path, final_path)` — **atomic on Windows NTFS**.
7. Apply owner-only DACL via `pywin32` `win32security.SetNamedSecurityInfo`.

**Why atomic rename:** readers may poll between steps 4 and 6 and see an
empty or partial JSON. `os.replace` guarantees readers see either the
old file (or nothing) or the complete new file — never a half-written state.

## Reader protocol (UE side)

```cpp
// FNyraHandshake::Poll() — called from a ticker
// Initial delay 50ms, ×1.5 backoff, capped at 2s, total budget 30s.
```

1. Stat `%LOCALAPPDATA%/NYRA/handshake-<our-pid>.json`.
2. If not present, continue backoff.
3. If present, read via `FFileHelper::LoadFileToString`.
4. Parse as JSON. **If parse fails, treat as not-ready and continue backoff**
   (tolerates mid-write race per RESEARCH §3.10 P1.1).
5. Validate all 5 fields present and types match. If validation fails,
   treat as corrupt; continue backoff up to 30s deadline.
6. On valid: connect `ws://127.0.0.1:<port>/` and send
   `session/authenticate` as first frame (see docs/JSONRPC.md §3.1).

## Disconnect / cleanup

- **UE clean shutdown:** UE deletes its own `handshake-<our-pid>.json` during
  `FNyraEditorModule::ShutdownModule`, AFTER the graceful `shutdown` JSON-RPC
  notification and NyraHost exit acknowledgement.
- **UE force-kill:** handshake file leaks; next NyraEditor startup scans
  `%LOCALAPPDATA%/NYRA/handshake-*.json`, reads `ue_pid`, checks
  `FPlatformProcess::IsProcRunning` (or `OpenProcess` failing); if dead,
  also checks `nyrahost_pid` and `TerminateProc(KillTree=true)` if the
  orphaned NyraHost is still alive. Then deletes the stale file.

## Multiple editor instances

Because filename includes `<ue_pid>`, concurrent editors do not collide.
Each editor only reads/deletes its own PID-scoped file.

## Related specs

- First WS frame protocol: `docs/JSONRPC.md` §3.1 — must be `session/authenticate`;
  NyraHost rejects any other first method with **close code 4401**.
- Error code `-32002 auth` (token mismatch): `docs/ERROR_CODES.md`
