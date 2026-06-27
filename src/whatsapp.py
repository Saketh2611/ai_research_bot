import time

import requests

from .config import Config
from .logger import log

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0/{phone_number_id}/messages"


def send_whatsapp_message(message: str, config: Config) -> bool:
    url = WHATSAPP_API_URL.format(phone_number_id=config.phone_number_id)
    headers = {
        "Authorization": f"Bearer {config.whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": config.recipient_number,
        "type": "text",
        "text": {"body": message},
    }

    for attempt in range(config.max_retries):
        try:
            log.info(f"Sending WhatsApp message (attempt {attempt + 1}/{config.max_retries})...")
            response = requests.post(url, headers=headers, json=payload, timeout=config.request_timeout)
            response.raise_for_status()
            data = response.json()

            if data.get("messages"):
                msg_id = data["messages"][0].get("id", "unknown")
                log.info(f"Message sent successfully. ID: {msg_id}")
                return True

            log.warning(f"Unexpected response format: {data}")
            return True

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            body = e.response.text if e.response is not None else ""

            if status == 401:
                log.error(f"Invalid WhatsApp token. Response: {body}")
                return False

            if status == 429:
                wait = config.retry_delay * (attempt + 1) * 2
                log.warning(f"Rate limited. Waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            log.error(f"HTTP {status} error: {body}")
            if attempt == config.max_retries - 1:
                return False
            time.sleep(config.retry_delay * (attempt + 1))

        except requests.exceptions.Timeout:
            log.warning(f"Request timed out (attempt {attempt + 1})")
            if attempt == config.max_retries - 1:
                return False
            time.sleep(config.retry_delay)

        except requests.exceptions.RequestException as e:
            log.error(f"Request failed: {e}")
            if attempt == config.max_retries - 1:
                return False
            time.sleep(config.retry_delay * (attempt + 1))

    return False
