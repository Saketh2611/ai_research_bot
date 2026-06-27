import json
from pathlib import Path

from .fetch_papers import Paper
from .logger import log

SENT_PAPERS_FILE = Path("sent_papers.json")


def load_sent_ids() -> set[str]:
    if not SENT_PAPERS_FILE.exists():
        return set()
    try:
        data = json.loads(SENT_PAPERS_FILE.read_text())
        return set(data.get("sent_ids", []))
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Could not load sent papers file: {e}")
        return set()


def save_sent_ids(ids: set[str]) -> None:
    data = {"sent_ids": sorted(ids)}
    SENT_PAPERS_FILE.write_text(json.dumps(data, indent=2))
    log.info(f"Saved {len(ids)} sent paper IDs")


def filter_unsent(papers: list[Paper]) -> list[Paper]:
    sent_ids = load_sent_ids()
    unsent = [p for p in papers if _extract_id(p.arxiv_url) not in sent_ids]
    skipped = len(papers) - len(unsent)
    if skipped:
        log.info(f"Skipped {skipped} previously sent papers")
    return unsent


def mark_as_sent(papers: list[Paper]) -> None:
    sent_ids = load_sent_ids()
    for paper in papers:
        sent_ids.add(_extract_id(paper.arxiv_url))
    save_sent_ids(sent_ids)


def _extract_id(url: str) -> str:
    return url.rstrip("/").split("/")[-1]
