import time

import requests

from .config import Config
from .fetch_papers import Paper
from .logger import log

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """You are a research paper summarizer. Given a paper's title and abstract, provide:
1. A one-line summary
2. Key contributions (exactly 3 bullet points)
3. Why it matters (1-2 sentences)
4. Real-world applications (1-2 sentences)

Rules:
- Use ONLY information from the title and abstract. Do NOT hallucinate or invent details.
- Keep the entire summary under 120 words.
- Be concise and precise.
- Use plain language accessible to technical professionals.

Format your response exactly as:
SUMMARY: <one line>
CONTRIBUTIONS:
- <point 1>
- <point 2>
- <point 3>
WHY IT MATTERS: <text>
APPLICATIONS: <text>"""


def summarize_papers(papers: list[Paper], config: Config) -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []

    for i, paper in enumerate(papers, 1):
        log.info(f"Summarizing paper {i}/{len(papers)}: {paper.title[:60]}...")
        summary = _summarize_single(paper, config)
        summaries.append(summary)

    return summaries


def _summarize_single(paper: Paper, config: Config) -> dict[str, str]:
    user_prompt = f"Title: {paper.title}\n\nAbstract: {paper.abstract}"
    url = GEMINI_API_URL.format(model=config.gemini_model)

    for attempt in range(config.max_retries):
        try:
            response = requests.post(
                url,
                params={"key": config.gemini_api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 500,
                    },
                },
                timeout=config.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            text = _extract_response_text(data)
            return _parse_summary(text)

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                wait = config.retry_delay * (attempt + 1)
                log.warning(f"Rate limited, retrying in {wait}s...")
                time.sleep(wait)
                continue
            if attempt == config.max_retries - 1:
                log.error(f"Failed to summarize: {e}")
                return _fallback_summary(paper)
            time.sleep(config.retry_delay)

        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            if attempt == config.max_retries - 1:
                log.error(f"Failed to summarize after {config.max_retries} attempts: {e}")
                return _fallback_summary(paper)
            time.sleep(config.retry_delay)

    return _fallback_summary(paper)


def _extract_response_text(data: dict) -> str:
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    if not parts:
        return ""
    return parts[0].get("text", "")


def _parse_summary(text: str) -> dict[str, str]:
    result = {"summary": "", "contributions": "", "why_it_matters": "", "applications": ""}

    lines = text.strip().split("\n")
    current_key = ""

    for line in lines:
        line = line.strip()
        if line.startswith("SUMMARY:"):
            current_key = "summary"
            result[current_key] = line[len("SUMMARY:"):].strip()
        elif line.startswith("CONTRIBUTIONS:"):
            current_key = "contributions"
        elif line.startswith("WHY IT MATTERS:"):
            current_key = "why_it_matters"
            result[current_key] = line[len("WHY IT MATTERS:"):].strip()
        elif line.startswith("APPLICATIONS:"):
            current_key = "applications"
            result[current_key] = line[len("APPLICATIONS:"):].strip()
        elif line.startswith("- ") and current_key == "contributions":
            result[current_key] += line + "\n"
        elif current_key and line:
            result[current_key] += " " + line

    for key in result:
        result[key] = result[key].strip()

    return result


def _fallback_summary(paper: Paper) -> dict[str, str]:
    abstract_short = paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract
    return {
        "summary": abstract_short,
        "contributions": "- See full paper for details",
        "why_it_matters": "Advances the state of AI research.",
        "applications": "See paper for specific applications.",
    }
