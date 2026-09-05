"""
One-time, post-analysis generation of:
  - a short summary
  - key takeaways
  - suggested starter questions
  - "important moments" (real timestamps, not hallucinated)

For important moments, the LLM is asked to pick from a numbered list of
*actual* transcript chunks rather than invent timestamps from scratch. We
then map its chosen chunk indices back to the chunk's real start time, so a
"moment" can never point to a timestamp that doesn't exist in the video.

This step is best-effort: if the LLM output can't be parsed, or Ollama is
unreachable, analysis still succeeds with empty/placeholder fields rather
than failing the whole request — a user should still be able to ask
questions even if the nice-to-have summary step fails.
"""
import json
import re
from typing import List, TypedDict

from langchain_core.documents import Document

from app.utils.llm import get_llm
from app.utils.logging import logger
from app.schemas import ImportantMoment


class AnalysisExtras(TypedDict):
    summary: str
    key_takeaways: List[str]
    suggested_questions: List[str]
    important_moments: List[ImportantMoment]


def _format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _sample_chunks(chunks: List[Document], max_total_chars: int = 6000, max_chunks: int = 40) -> List[Document]:
    if not chunks:
        return []
    total_chars = sum(len(c.page_content) for c in chunks)
    if total_chars <= max_total_chars and len(chunks) <= max_chunks:
        return chunks

    n = min(max_chunks, len(chunks))
    step = len(chunks) / n
    indices = sorted({min(len(chunks) - 1, int(i * step)) for i in range(n)})
    sampled = [chunks[i] for i in indices]

    result, total = [], 0
    for c in sampled:
        if total + len(c.page_content) > max_total_chars and result:
            break
        result.append(c)
        total += len(c.page_content)
    return result or chunks[:1]


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


_PROMPT_TEMPLATE = """You will read numbered excerpts from a YouTube video's transcript and produce a JSON object summarizing it.

Excerpts (format: [index] (timestamp) [video_id] text):
{excerpts}

Respond with ONLY a JSON object (no markdown, no commentary) matching exactly this shape:
{{
  "summary": "2-4 sentence summary of the video content",
  "key_takeaways": ["short takeaway 1", "short takeaway 2", "..."],
  "suggested_questions": ["a specific question a viewer could ask about this content", "..."],
  "important_moments": [{{"chunk_index": 0, "label": "short description of what happens here"}}]
}}

Rules:
- Base everything strictly on the excerpts. Do not invent facts.
- key_takeaways: 3-5 items.
- suggested_questions: 3-4 specific, answerable-from-this-content questions.
- important_moments: 3-6 items, each referencing a real chunk_index from the excerpts above.
"""


async def generate_analysis_extras(chunks: List[Document]) -> AnalysisExtras:
    fallback: AnalysisExtras = {
        "summary": "",
        "key_takeaways": [],
        "suggested_questions": [],
        "important_moments": [],
    }
    if not chunks:
        return fallback

    sampled = _sample_chunks(chunks)
    excerpts = "\n".join(
        f"[{i}] ({_format_time(c.metadata.get('start', 0.0))}) [{c.metadata.get('video_id', '')}] {c.page_content[:400]}"
        for i, c in enumerate(sampled)
    )

    try:
        llm = get_llm()
        raw = await llm.ainvoke(_PROMPT_TEMPLATE.format(excerpts=excerpts))
        data = _extract_json(raw)

        moments: List[ImportantMoment] = []
        for m in data.get("important_moments", []):
            idx = m.get("chunk_index")
            label = (m.get("label") or "").strip()
            if isinstance(idx, int) and 0 <= idx < len(sampled) and label:
                chunk = sampled[idx]
                moments.append(
                    ImportantMoment(
                        video_id=chunk.metadata.get("video_id", ""),
                        time=chunk.metadata.get("start", 0.0),
                        label=label,
                    )
                )

        return {
            "summary": (data.get("summary") or "").strip(),
            "key_takeaways": [str(t).strip() for t in data.get("key_takeaways", []) if str(t).strip()],
            "suggested_questions": [str(q).strip() for q in data.get("suggested_questions", []) if str(q).strip()],
            "important_moments": moments,
        }
    except Exception as exc:
        logger.warning(f"Analysis-extras generation failed, degrading gracefully: {exc}")
        return fallback
