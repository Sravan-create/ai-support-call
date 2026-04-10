"""
helpers/openai_helper.py
─────────────────────────
GPT-4o-mini powered analysis for call transcripts and AI summary.
Uses httpx directly — no openai SDK needed.
"""

import json
import logging
import os

import httpx

logger = logging.getLogger("openai_helper")

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_MODEL      = "gpt-4o-mini"


def _headers() -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }


def _has_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


# ── Per-call transcript analysis ─────────────────────────────────────────────

_ANALYSIS_SYSTEM = """\
You are analyzing a post-service feedback call transcript for Shri Venkanna Motors, a Hero MotoCorp dealership.
Return ONLY valid JSON with exactly these three keys:

- "sentiment": one of "positive", "negative", or "neutral"
- "takeaway": a concise 5-6 word statement capturing the call outcome (e.g. "Customer satisfied, will revisit soon")
- "callback": true if a human agent should follow up with this customer, false otherwise

Do not include any explanation outside the JSON object."""


async def analyze_transcript(transcript_text: str) -> dict:
    """
    Calls GPT-4o-mini to analyze a single call transcript.
    Returns {"sentiment": str, "takeaway": str, "callback": bool}
    """
    if not _has_key():
        logger.warning("OPENAI_API_KEY not set — skipping transcript analysis")
        return {"sentiment": "neutral", "takeaway": "Analysis unavailable", "callback": False}

    payload = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": _ANALYSIS_SYSTEM},
            {"role": "user",   "content": f"Analyze this call transcript:\n\n{transcript_text}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 120,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_OPENAI_URL, headers=_headers(), json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            result  = json.loads(content)
            return {
                "sentiment": str(result.get("sentiment", "neutral")).lower(),
                "takeaway":  str(result.get("takeaway",  "")).strip(),
                "callback":  bool(result.get("callback", False)),
            }
    except Exception as e:
        logger.error(f"OpenAI analyze_transcript failed: {e}")
        return {"sentiment": "neutral", "takeaway": "", "callback": False}


# ── Aggregate AI summary ──────────────────────────────────────────────────────

_SUMMARY_SYSTEM = """\
You are a business analyst for Shri Venkanna Motors, a Hero MotoCorp dealership.
You will be given data from recent customer feedback calls (transcripts, sentiments, summaries).

Return ONLY valid JSON with exactly these keys:
- "overall": 2-sentence business overview of the current feedback landscape
- "likes": array of strings — what customers are praising (max 5 bullet points)
- "dislikes": array of strings — what customers are complaining about (max 5 bullet points)
- "themes": array of short theme tag strings (max 8, e.g. "Wait time", "Staff friendliness")
- "callback_issues": array of strings — specific issues from customers who need callbacks
- "actions": array of strings — recommended business actions (max 5)
- "key_insights": array of strings — top 3 most important findings for management
- "sentiment_breakdown": object with keys "positive", "negative", "neutral" as integers"""


async def generate_summary(calls_data: list[dict]) -> dict:
    """
    Sends aggregated call data to GPT-4o-mini and returns a structured business summary.
    Each item in calls_data: {customer, sentiment, takeaway, callback, transcript}
    """
    if not _has_key():
        return {"error": "OPENAI_API_KEY not configured on the server"}

    if not calls_data:
        return {"error": "No call data available to summarize"}

    # Build the user message
    lines = [f"Total calls: {len(calls_data)}\n"]
    for i, c in enumerate(calls_data, 1):
        lines.append(f"--- Call {i} ---")
        lines.append(f"Customer: {c.get('customer') or 'Unknown'}")
        lines.append(f"Sentiment: {c.get('sentiment') or 'unknown'}")
        lines.append(f"Callback needed: {c.get('callback', False)}")
        if c.get("takeaway"):
            lines.append(f"Takeaway: {c['takeaway']}")
        if c.get("transcript"):
            # Trim transcript to avoid token limits
            lines.append(f"Transcript excerpt:\n{c['transcript'][:600]}")
        lines.append("")

    user_msg = "\n".join(lines)

    payload = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": _SUMMARY_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
        "max_tokens": 800,
    }

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(_OPENAI_URL, headers=_headers(), json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        logger.error(f"OpenAI generate_summary failed: {e}")
        return {"error": f"Summary generation failed: {str(e)}"}
