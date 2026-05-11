# Connection issues

## Status pill never goes green

The pill goes green only after the WS handshake + first `session/authenticate` succeed. Failures by stage:

| Pill colour | Stage | What's failing |
|---|---|---|
| Grey | Spawning | NyraHost subprocess didn't start. Check `Saved/Logs/NyraHost.log` for Python tracebacks. |
| Yellow blink | Waiting for handshake | Sidecar is alive but isn't writing `%LOCALAPPDATA%/NYRA/handshake-<editor_pid>.json`. Check antivirus quarantines + write permissions. |
| Red | Auth failed | Token mismatch. Run **Restart NYRA** from the chat header — this regenerates the handshake. |
| Red flash repeat | Unstable | NyraHost crashed ≥3 times in a 60 s window. The supervisor stops auto-respawn; check the log for the root cause. |

## "auth_token_mismatch" log line

Almost always means a stale handshake file from a previous editor session. Phase 1's `FNyraHandshake::CleanupOrphans` + the `started_at` timestamp check should catch this — if you see it on a *fresh* editor, file a bug.

## Privacy Mode blocks my request

Phase 15-E's PrivacyGuard refuses every non-loopback HTTP when Privacy Mode is on. Toggle off in **Settings → Privacy Mode** if you need Meshy / ComfyUI / Claude.

## Multiplayer NYRA: "ghost room" error

Phase 17-C's `LocalRoomBackend` is single-process. Rooms don't persist across editor restarts in v0. Real sync is gated on the founder deploying the multiplayer server.
