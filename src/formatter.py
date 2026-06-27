from datetime import datetime, timezone

from .config import Config
from .fetch_papers import Paper


def format_message(papers: list[Paper], summaries: list[dict[str, str]], config: Config) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    separator = "\n\n────────────────────────\n\n"

    header = f"📚 *Daily AI Research Digest*\n\n📅 Date: {today}"
    sections: list[str] = []

    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    for i, (paper, summary) in enumerate(zip(papers, summaries)):
        emoji = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        authors_str = ", ".join(paper.authors[:3])
        if len(paper.authors) > 3:
            authors_str += f" et al. ({len(paper.authors)} authors)"

        contributions = summary.get("contributions", "")
        contributions_formatted = "\n".join(
            f"  • {line[2:]}" if line.startswith("- ") else f"  • {line}"
            for line in contributions.split("\n")
            if line.strip()
        )

        section = (
            f"{emoji} *{paper.title}*\n\n"
            f"👥 {authors_str}\n\n"
            f"📝 {summary.get('summary', '')}\n\n"
            f"✅ *Key Contributions*\n{contributions_formatted}\n\n"
            f"💡 *Why it Matters*\n{summary.get('why_it_matters', '')}\n\n"
            f"🔬 *Applications*\n{summary.get('applications', '')}\n\n"
            f"🔗 {paper.arxiv_url}"
        )
        sections.append(section)

    message = header + separator + separator.join(sections)

    if len(message) > config.whatsapp_max_message_length:
        message = message[: config.whatsapp_max_message_length - 20] + "\n\n... (truncated)"

    return message
