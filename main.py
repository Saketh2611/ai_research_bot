import sys
import time
import traceback

from src.config import Config
from src.dedup import filter_unsent, mark_as_sent
from src.fetch_papers import fetch_papers
from src.formatter import format_message
from src.logger import log
from src.summarize import summarize_papers
from src.whatsapp import send_whatsapp_message


def main() -> int:
    start_time = time.time()
    log.info("Starting AI Research Daily Bot")

    try:
        config = Config.from_env()
    except KeyError as e:
        log.error(f"Missing environment variable: {e}")
        return 1

    try:
        papers = fetch_papers(config)
        if not papers:
            log.info("No new papers found today. Exiting.")
            return 0

        papers = filter_unsent(papers)
        if not papers:
            log.info("All papers already sent. Exiting.")
            return 0

        summaries = summarize_papers(papers, config)
        message = format_message(papers, summaries, config)
        log.info(f"Formatted message ({len(message)} chars)")

        success = send_whatsapp_message(message, config)
        if not success:
            log.error("Failed to send WhatsApp message")
            return 1

        mark_as_sent(papers)

        elapsed = time.time() - start_time
        log.info(f"Completed successfully in {elapsed:.1f}s")
        return 0

    except Exception as e:
        log.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
