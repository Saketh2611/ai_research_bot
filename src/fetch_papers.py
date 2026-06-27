import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

from .config import Config
from .logger import log

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


@dataclass
class Paper:
    title: str
    authors: list[str]
    abstract: str
    published: str
    arxiv_url: str
    pdf_url: str


def fetch_papers(config: Config) -> list[Paper]:
    categories_query = " OR ".join(f"cat:{cat}" for cat in config.arxiv_categories)
    query = f"({categories_query})"

    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": 50,
    }

    log.info("Fetching papers from arXiv...")
    response = requests.get(ARXIV_API_URL, params=params, timeout=config.request_timeout)
    response.raise_for_status()

    papers = _parse_response(response.text)
    recent = _filter_recent(papers, hours=48)
    log.info(f"Found {len(recent)} papers from the last 48 hours")

    if recent:
        result = recent[: config.max_papers]
    else:
        log.info("No recent papers found, falling back to latest available papers")
        result = papers[: config.max_papers]

    log.info(f"Selected top {len(result)} papers")
    return result


def _parse_response(xml_text: str) -> list[Paper]:
    root = ET.fromstring(xml_text)
    papers: list[Paper] = []

    for entry in root.findall("atom:entry", ATOM_NS):
        title_el = entry.find("atom:title", ATOM_NS)
        if title_el is None or title_el.text is None:
            continue

        title = " ".join(title_el.text.strip().split())
        abstract_el = entry.find("atom:summary", ATOM_NS)
        abstract = " ".join((abstract_el.text or "").strip().split())

        authors = [
            (a.find("atom:name", ATOM_NS).text or "").strip()
            for a in entry.findall("atom:author", ATOM_NS)
            if a.find("atom:name", ATOM_NS) is not None
        ]

        published_el = entry.find("atom:published", ATOM_NS)
        published = (published_el.text or "").strip() if published_el is not None else ""

        arxiv_url = ""
        pdf_url = ""
        for link in entry.findall("atom:link", ATOM_NS):
            href = link.get("href", "")
            if link.get("type") == "text/html":
                arxiv_url = href
            elif link.get("title") == "pdf":
                pdf_url = href

        if not arxiv_url:
            id_el = entry.find("atom:id", ATOM_NS)
            if id_el is not None and id_el.text:
                arxiv_url = id_el.text.strip()
                pdf_url = arxiv_url.replace("/abs/", "/pdf/")

        papers.append(Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            published=published,
            arxiv_url=arxiv_url,
            pdf_url=pdf_url,
        ))

    return papers


def _filter_recent(papers: list[Paper], hours: int = 48) -> list[Paper]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent: list[Paper] = []

    for paper in papers:
        try:
            pub_date = datetime.fromisoformat(paper.published.replace("Z", "+00:00"))
            if pub_date >= cutoff:
                recent.append(paper)
        except (ValueError, TypeError):
            recent.append(paper)

    return recent
