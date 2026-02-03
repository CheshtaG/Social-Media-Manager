"""FastAPI app for the reel script generator."""

import asyncio
import logging
from typing import Annotated, Optional

# So you see "Calling Gemini API..." and "Gemini API returned" in the server terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.gemini_client import generate_script, optimize_script, recommend_script


app = FastAPI(
    title="Reel Script Generator",
    description="Generate a 30-second reel script from a text prompt using Gemini 2.5 Flash.",
    version="0.1.0",
)


class ConversationMessage(BaseModel):
    role: str = Field(..., description="'user' or 'ai'")
    content: str = Field(..., description="Message content")


class GenerateScriptRequest(BaseModel):
    """Request body for script generation."""

    prompt: str = Field(..., min_length=1, description="Topic or idea for the reel.")
    duration: Optional[str] = Field(None, description="Duration (e.g. '15s', '30s', '1 min')")
    tone: Optional[str] = Field(None, description="Tone/mood (e.g. 'Motivational', 'Playful')")
    language: Optional[str] = Field(None, description="Language (e.g. 'English')")
    notes: Optional[str] = Field(None, description="Additional notes or existing script to improve")
    conversation_history: Optional[list[ConversationMessage]] = Field(
        None, description="Chat history; user-stated duration/tone overrides are applied."
    )


class GenerateScriptResponse(BaseModel):
    """Response with the generated script as plain text."""

    script: str = Field(..., description="Generated script with [HOOK] and [BODY] sections.")


class OptimizeScriptRequest(BaseModel):
    current_script: str = Field(..., min_length=1)
    conversation_history: list[ConversationMessage] = Field(default_factory=list)


class OptimizeScriptResponse(BaseModel):
    message: str = Field(..., description="AI confirmation or clarification question")
    script: Optional[str] = Field(None, description="Revised script if changes were applied")


class RecommendScriptRequest(BaseModel):
    """Request for reel recommendation (no script)."""

    prompt: str = Field(..., min_length=1, description="Reel idea or topic.")
    duration: Optional[str] = Field(None, description="Optional hint: user's preferred duration.")
    tone: Optional[str] = Field(None, description="Optional hint: user's preferred tone.")


class RecommendScriptResponse(BaseModel):
    """Recommendation only; no script."""

    message: str = Field(..., description="AI recommendation text.")
    suggested_duration: str = Field(..., description="e.g. '30s', '15s', '1 min'.")
    suggested_tone: str = Field(..., description="e.g. 'Playful / Fun', 'Motivational'.")


# Timeout for Gemini API call (seconds) so we never hang indefinitely.
GEMINI_TIMEOUT_SECONDS = 90


@app.post("/recommend-script", response_model=RecommendScriptResponse)
async def recommend_script_endpoint(
    body: RecommendScriptRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RecommendScriptResponse:
    """
    Get a recommendation (duration, tone) for a reel idea. Does not generate a script.
    Use this first; after user confirms, call POST /generate-script.
    """
    if not (settings.gemini_api_key or "").strip():
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not set. Add it to your .env or export it in the shell.",
        )
    loop = asyncio.get_event_loop()
    try:
        message, suggested_duration, suggested_tone = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: recommend_script(
                    prompt=body.prompt,
                    duration_hint=body.duration,
                    tone_hint=body.tone,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                ),
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Recommendation timed out after {GEMINI_TIMEOUT_SECONDS} seconds.",
        ) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}") from e
    return RecommendScriptResponse(
        message=message,
        suggested_duration=suggested_duration,
        suggested_tone=suggested_tone,
    )


@app.post("/generate-script", response_model=GenerateScriptResponse)
async def generate_script_endpoint(
    body: GenerateScriptRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenerateScriptResponse:
    """
    Generate a 30-second reel script from a text prompt.

    Returns plain text with [HOOK] and [BODY] sections.
    """
    if not (settings.gemini_api_key or "").strip():
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not set. Add it to your .env or export it in the shell.",
        )
    loop = asyncio.get_event_loop()
    try:
        conv = [{"role": m.role, "content": m.content} for m in (body.conversation_history or [])]
        script = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: generate_script(
                    prompt=body.prompt,
                    duration=body.duration,
                    tone=body.tone,
                    language=body.language,
                    notes=body.notes,
                    conversation_history=conv if conv else None,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                ),
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Script generation timed out after {GEMINI_TIMEOUT_SECONDS} seconds. Check server logs.",
        ) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}") from e
    return GenerateScriptResponse(script=script)


@app.post("/generate-script/stream")
@app.post("/generate-script/stream/")
async def generate_script_stream_endpoint(
    body: GenerateScriptRequest,
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Stream a 30-second reel script from a text prompt. Returns plain text
    (full script in one chunk). Use POST /generate-script for JSON response.
    """
    if not (settings.gemini_api_key or "").strip():
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not set. Add it to your .env or export it in the shell.",
        )

    conv = [{"role": m.role, "content": m.content} for m in (body.conversation_history or [])]
    loop = asyncio.get_event_loop()
    try:
        script = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: generate_script(
                    prompt=body.prompt,
                    duration=body.duration,
                    tone=body.tone,
                    language=body.language,
                    notes=body.notes,
                    conversation_history=conv if conv else None,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                ),
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Script generation timed out after {GEMINI_TIMEOUT_SECONDS} seconds.",
        ) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}") from e

    async def stream() -> str:
        yield script

    return StreamingResponse(
        stream(),
        media_type="text/plain; charset=utf-8",
    )


@app.post("/optimize-script", response_model=OptimizeScriptResponse)
async def optimize_script_endpoint(
    body: OptimizeScriptRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> OptimizeScriptResponse:
    """
    Refine a script based on user feedback. Pass full conversation history for context.
    Returns a brief message; script is included only when changes were applied.
    """
    if not (settings.gemini_api_key or "").strip():
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not set. Add it to your .env or export it in the shell.",
        )
    history = [{"role": m.role, "content": m.content} for m in body.conversation_history]
    loop = asyncio.get_event_loop()
    try:
        script, message = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: optimize_script(
                    current_script=body.current_script,
                    conversation_history=history,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                ),
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Optimization timed out after {GEMINI_TIMEOUT_SECONDS} seconds.",
        ) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}") from e
    return OptimizeScriptResponse(message=message, script=script)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
