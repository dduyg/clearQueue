"""
Entry point for deploying ClearQueue on a Hugging Face Space using the
**Gradio SDK** (free), rather than the Docker SDK (now paid-plan-only on
Hugging Face as of mid-2026).

ClearQueue itself has nothing to do with Gradio — it's a FastAPI backend
serving a plain HTML/CSS/JS frontend. This file exists purely so a
Gradio-SDK Space (which runs `python app.py`) ends up serving that same
FastAPI app. We mount a tiny, informational Gradio page at /gradio so the
Space genuinely uses the SDK it's declared under; the real app is served
at "/" exactly as it is on Render or any other host.

Not used for local development or for Render/Fly/Docker deployments —
those run `uvicorn main:app` directly from inside backend/. This file is
Hugging-Face-Gradio-Space-specific.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

import gradio as gr
from main import app as fastapi_app  # noqa: E402  (import after sys.path tweak)

_info_page = gr.Blocks(title="ClearQueue")
with _info_page:
    gr.Markdown(
        "### ClearQueue is running.\n\n"
        "This is a Gradio-SDK wrapper used only because Hugging Face's "
        "Docker SDK requires a paid plan. The actual app is plain "
        "FastAPI + HTML/CSS/JS — open the Space's main URL (not this "
        "`/gradio` path) to use it."
    )

app = gr.mount_gradio_app(fastapi_app, _info_page, path="/gradio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
