"""NyraInfer subpackage: llama-server spawn, Ollama detect, SSE parser, router.

Per CONTEXT.md D-18/D-19/D-20:
- detect Ollama fast path (http://127.0.0.1:11434/api/tags)
- else spawn bundled llama-server.exe with GPU-backend fallback (CUDA -> Vulkan -> CPU)
- parse OpenAI-compatible SSE stream from /v1/chat/completions
- lazy spawn + 10-minute idle shutdown
"""
