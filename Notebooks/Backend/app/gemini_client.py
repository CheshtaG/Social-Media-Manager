"""Gemini client for generating reel scripts from prompts."""

import re
import time
from typing import Optional

import google.generativeai as genai

SYSTEM_INSTRUCTION = """You write Instagram Reel scripts with timestamps, visuals, and voiceover. Expand prompts into compelling angles. Use fun storytelling: hook → curiosity → payoff.

**CRITICAL: You MUST follow the user's specified Duration exactly.**
- If Duration is "15s" → script ends at 15 seconds
- If Duration is "30s" → script ends at 30 seconds  
- If Duration is "1 min" or "60s" → script ends at 60 seconds
- If no duration specified → default to 30 seconds

**Format (REQUIRED):** Output a 3-column MARKDOWN table ONLY with these columns:
Time | What we SEE (Visual) | What we HEAR (Voiceover / Talking / Music)
| --- | --- | --- |

Rules:
- Use timestamps like 0–3s, 3–7s, 7–12s, etc. Cover the FULL duration.
- The final time range MUST end at the specified duration (15s, 30s, or 60s).
- Keep each row concise and easy to scan.
- Use a short hook in the first row.
- Match the user's tone (Motivational, Playful, etc.) and language.
- Output only the table. No extra text, no [HOOK]/[BODY] labels.

Example:
| Time | What we SEE (Visual) | What we HEAR (Voiceover / Talking / Music) |
| --- | --- | --- |
| 0–3s | Close-up of face, pointing to camera | "Stop scrolling." |
| 3–7s | B-roll of laptop / notes | "If you're a student, listen to this." |
| 7–15s | Quick montage of key tips | "Here are three things you can do today..." |
"""

RECOMMEND_SYSTEM_INSTRUCTION = """You are a recommendation system for Instagram Reels. The user has given you an idea for a reel. Your job is to recommend a duration and tone based on your understanding of the topic—do NOT write a script.

Understand the topic first: Is it a quick tip, a story, a product demo, a complex concept? Then recommend what fits.
- For quick tips or single hooks: suggest 15s.
- For a story, product branding, or concept that needs setup and payoff: suggest 30s or 1 min.
- For deep dives, tutorials, or multi-part ideas: suggest 1 min.
- Match tone to the topic: playful for fun topics, motivational for goals, storytelling for narratives, aesthetic for lifestyle/visual content.

Output requirements:
- Start with this exact sentence:
  "According to my understanding, here is what I recommend for your idea:"
- Then output a short bulleted list (each point starts with "-").
- Include these points, in this order:
  1) Recommended duration + short why
  2) Recommended tone + short why
  3) Assumed target audience (based on the topic)
- Keep it concise (max 3 bullets total).
- Do NOT write any script, hook, or body content.

Example:
According to my understanding, here is what I recommend for your idea:
- Duration: 1 min — this topic needs setup + payoff.
- Tone: Motivational / Inspiring — fits the brand-building angle.
- Target audience: early-stage founders and marketers.

You must also output the exact suggested duration and tone in this format so the system can use them:
[DURATION]
15s
[/DURATION]
[TONE]
Playful / Fun
[/TONE]

Put the sentence + bullet list first, then the [DURATION] and [TONE] blocks. No other text."""


def recommend_script(
    prompt: str,
    duration_hint: Optional[str] = None,
    tone_hint: Optional[str] = None,
    api_key: str = "",
    model: str = "gemini-2.5-flash",
) -> tuple[str, str, str]:
    """
    Get a recommendation (duration, tone) for a reel idea. Does not generate a script.

    Returns:
        (message, suggested_duration, suggested_tone)
    """
    user_prompt = f"User's reel idea: {prompt}\n"
    if duration_hint:
        user_prompt += f"(User previously selected duration: {duration_hint})\n"
    if tone_hint:
        user_prompt += f"(User previously selected tone: {tone_hint})\n"
    user_prompt += "\nRecommend a duration and tone for this reel. Reply with your short message and the [DURATION] and [TONE] blocks."

    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=RECOMMEND_SYSTEM_INSTRUCTION,
    )
    print(f"[Gemini] Recommend API (model={model})...", flush=True)
    t0 = time.monotonic()
    try:
        response = gemini_model.generate_content(user_prompt)
    except Exception as e:
        print(f"[Gemini] Recommend API failed: {e}", flush=True)
        raise
    elapsed = time.monotonic() - t0
    print(f"[Gemini] Recommend API returned in {elapsed:.1f}s", flush=True)
    if not response.candidates:
        feedback = getattr(response, "prompt_feedback", None)
        raise ValueError(f"Gemini returned no text. prompt_feedback={feedback}")
    text = response.text.strip()

    # Parse message (everything before [DURATION]) and [DURATION]/[TONE] blocks
    duration_match = re.search(r"\[DURATION\]\s*([\s\S]*?)\s*\[/DURATION\]", text)
    tone_match = re.search(r"\[TONE\]\s*([\s\S]*?)\s*\[/TONE\]", text)
    suggested_duration = (duration_match.group(1).strip() or "30s").strip()
    suggested_tone = (tone_match.group(1).strip() or "Playful").strip() if tone_match else "Playful"
    # Message is the part before [DURATION]
    message = re.sub(r"\[DURATION\][\s\S]*", "", text).strip()
    if not message:
        message = f"For your topic I recommend a {suggested_duration} reel with a {suggested_tone} tone. If you're comfortable with it, I can create the script for you."

    return (message, suggested_duration, suggested_tone)


def _parse_duration_tone_from_conversation(conversation: list[dict]) -> tuple[Optional[str], Optional[str]]:
    """
    Parse user messages for duration/tone overrides. Latest user message wins.
    Returns (duration_override, tone_override); either can be None.
    """
    duration_override: Optional[str] = None
    tone_override: Optional[str] = None
    user_messages = [(m.get("content") or "").lower() for m in conversation if m.get("role") == "user"]
    # Scan from latest message so user's last correction wins
    for text in reversed(user_messages):
        if not text:
            continue
        if duration_override is None:
            if re.search(r"\b(1\s*min|one\s*minute|60\s*s|60\s*sec|60\s*second)", text):
                duration_override = "1 min"
            elif re.search(r"\b(30\s*s|30\s*sec|30\s*second|half\s*minute)", text):
                duration_override = "30s"
            elif re.search(r"\b(15\s*s|15\s*sec|15\s*second)", text):
                duration_override = "15s"
        if tone_override is None:
            if re.search(r"\b(playful|fun|chaotic)\b", text):
                tone_override = "Playful / Fun"
            elif re.search(r"\b(motivational|inspiring)\b", text):
                tone_override = "Motivational / Inspiring"
            elif re.search(r"\b(aesthetic|soft|cozy)\b", text):
                tone_override = "Aesthetic / Soft / Cozy"
            elif re.search(r"\b(storytelling|cinematic)\b", text):
                tone_override = "Storytelling / Cinematic"
        if duration_override is not None and tone_override is not None:
            break
    return (duration_override, tone_override)


def generate_script(
    prompt: str,
    duration: Optional[str] = None,
    tone: Optional[str] = None,
    language: Optional[str] = None,
    notes: Optional[str] = None,
    conversation_history: Optional[list[dict]] = None,
    api_key: str = "",
    model: str = "gemini-2.5-flash",
) -> str:
    """
    Generate a reel script with timestamps and VO from a prompt and optional form inputs.
    If conversation_history is provided, user-stated duration/tone overrides are applied.

    Args:
        prompt: The user's topic or idea for the reel.
        duration: Target duration (e.g. '15s', '30s', '1 min'). Defaults to 30s.
        tone: Desired tone/mood (e.g. 'Motivational', 'Playful'). Model will match it.
        language: Output language (e.g. 'English'). Defaults to English.
        notes: Additional context, notes, or existing script to improve.
        conversation_history: Optional chat history; user messages are scanned for duration/tone overrides.
        api_key: Gemini API key (e.g. from Google AI Studio).
        model: Gemini model id. Defaults to gemini-2.5-flash.

    Returns:
        Plain-text script with [HOOK] and [BODY] sections, timestamped with VO.

    Raises:
        Exception: On API or network errors.
    """
    # Apply overrides from conversation (e.g. user said "1 min long")
    final_duration = duration or "30s"
    final_tone = tone or "Playful"
    if conversation_history:
        dur_ov, tone_ov = _parse_duration_tone_from_conversation(conversation_history)
        if dur_ov:
            final_duration = dur_ov
        if tone_ov:
            final_tone = tone_ov
    print(f"[Gemini] Form inputs - duration={final_duration}, tone={final_tone}, language={language}, notes={bool(notes)}", flush=True)

    user_prompt = f"Topic: {prompt}\n"
    user_prompt += f"Duration: {final_duration}\n"
    user_prompt += f"Tone: {final_tone}\n"
    if language:
        user_prompt += f"Language: {language}\n"
    if notes:
        user_prompt += f"Notes/Context: {notes}\n"
    if conversation_history:
        conv_text = "\n".join(
            f"{m.get('role', '')}: {m.get('content', '')}"
            for m in conversation_history
        )
        user_prompt += f"\nConversation with user (honor their stated preferences, e.g. duration or tone):\n{conv_text}\n\n"
    user_prompt += "Generate the script with timestamps and VO. The script MUST be exactly the specified duration."

    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    print(f"[Gemini] Calling API (model={model}, prompt_len={len(user_prompt)})...", flush=True)
    t0 = time.monotonic()
    try:
        response = gemini_model.generate_content(user_prompt)
    except Exception as e:
        print(f"[Gemini] API call failed: {e}", flush=True)
        raise
    elapsed = time.monotonic() - t0
    print(f"[Gemini] API returned in {elapsed:.1f}s", flush=True)
    if not response.candidates:
        feedback = getattr(response, "prompt_feedback", None)
        msg = f"Gemini returned no text. prompt_feedback={feedback}"
        raise ValueError(msg)
    text = response.text
    if text is None:
        raise ValueError("Gemini response had no text (content may be blocked).")
    return text.strip()


def generate_script_stream(prompt: str, api_key: str, model: str = "gemini-2.5-flash"):
    """
    Stream a 30-second reel script from a text prompt using Gemini.
    Yields text chunks as they arrive for lower perceived latency.

    Args:
        prompt: The user's topic or idea for the reel.
        api_key: Gemini API key (e.g. from Google AI Studio).
        model: Gemini model id. Defaults to gemini-2.5-flash.

    Yields:
        Plain-text chunks of the script.

    Raises:
        Exception: On API or network errors.
    """
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    response_stream = gemini_model.generate_content(prompt, stream=True)
    for chunk in response_stream:
        if chunk.candidates and chunk.text:
            yield chunk.text


OPTIMIZE_SYSTEM_INSTRUCTION = """You help the user refine a reel script through conversation. You have full context of the chat history and the current script.

**Your behavior:**
1. When the user asks for changes (shorter, longer, different tone, etc.): Apply the changes and return the revised script. Reply with a brief confirmation (e.g. "Done. I've shortened the hook."). Keep confirmations to 1-2 short sentences.
2. When you need clarification (e.g. "shorter" could mean hook or whole script): Ask a short, direct question. Do NOT return a revised script. Just ask.
3. Use the full conversation history to understand context.

**Output format:** Use EXACTLY this structure. No other text before or after.

[MESSAGE]
your brief confirmation or clarification question (1-2 sentences)
[/MESSAGE]

[SCRIPT]
revised script with [HOOK] and [BODY] sections - ONLY if you applied changes. If you need clarification, leave this section completely empty.
[/SCRIPT]

- If you applied changes: put the full revised script between [SCRIPT] and [/SCRIPT].
- If you need clarification: put nothing between [SCRIPT] and [/SCRIPT] (or just a blank line)."""


def optimize_script(
    current_script: str,
    conversation_history: list[dict],
    api_key: str,
    model: str = "gemini-2.5-flash",
) -> tuple[Optional[str], str]:
    """
    Optimize a script based on user feedback and full conversation context.

    Args:
        current_script: The current script to refine.
        conversation_history: List of {role: "user"|"ai", content: str}.
        api_key: Gemini API key.
        model: Gemini model id.

    Returns:
        (revised_script_or_none, message) - If clarification needed, script is None.
    """
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=OPTIMIZE_SYSTEM_INSTRUCTION,
    )

    conv_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in conversation_history
    )
    prompt = f"""Conversation so far:
{conv_text}

Current script:
{current_script}

The user's latest message is the last USER line above. Apply changes or ask for clarification. Use the [MESSAGE] and [SCRIPT] format exactly."""

    print(f"[Gemini] Calling optimize API (model={model})...", flush=True)
    t0 = time.monotonic()
    try:
        response = gemini_model.generate_content(prompt)
    except Exception as e:
        print(f"[Gemini] Optimize API call failed: {e}", flush=True)
        raise
    elapsed = time.monotonic() - t0
    print(f"[Gemini] Optimize API returned in {elapsed:.1f}s", flush=True)

    if not response.candidates:
        feedback = getattr(response, "prompt_feedback", None)
        raise ValueError(f"Gemini returned no text. prompt_feedback={feedback}")
    text = response.text
    if not text or not text.strip():
        raise ValueError("Gemini response had no text.")

    text = text.strip()
    # Parse [MESSAGE]...[/MESSAGE] and [SCRIPT]...[/SCRIPT] (avoids JSON escaping issues)
    msg_match = re.search(r"\[MESSAGE\]([\s\S]*?)\[/MESSAGE\]", text)
    script_match = re.search(r"\[SCRIPT\]([\s\S]*?)\[/SCRIPT\]", text)
    message = msg_match.group(1).strip() if msg_match else "Done."
    script_block = script_match.group(1).strip() if script_match else ""
    script = script_block if script_block else None
    return (script if script else None, message)
