# Account / Claude auth issues

## I don't have a NYRA account — where do I sign in?

You don't. NYRA is free and uses **your own Claude / Codex subscription**. There is no NYRA account, no NYRA login, no NYRA dashboard.

## "claude_not_installed" error

Run `claude auth login` in a terminal once. NYRA drives `claude` as a subprocess; the CLI must be on PATH and authenticated against your Anthropic Pro/Max subscription.

## "ANTHROPIC_API_KEY env var present" warning

Phase 9-2 scrubs `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` from the child process env (per D-02 ToS-compliance). The warning means you had one set; NYRA removed it for the child only, your terminal still has it.

## Meshy says "auth failed" / I'm not Pro tier

Phase 9 RIG-01 + image_to_3d both call Meshy. The auto-rig endpoint requires **Pro tier ($20/mo)**. Set `MESHY_API_KEY` in **Settings → Tools → Meshy** with a Pro-tier key.

## ElevenLabs says "auth failed"

Phase 19-A audio gen uses ElevenLabs SFX. Free tier doesn't include the SFX product — you need Starter ($5/mo) or above. Set `ELEVENLABS_API_KEY` in Settings.

## Marketplace install says "signature_invalid"

Phase 17-B refuses any blob whose signature doesn't match a pinned trust root in `MARKETPLACE_TRUST_ROOTS`. If you're seeing this with a legit listing, the marketplace's signing key has rotated and we need to ship an updated client. File a bug.
