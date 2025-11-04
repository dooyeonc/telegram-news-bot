import os
import sys
import time
import requests
from typing import List

CHANNEL_ID = "@newsnissue"  # 이슈 다이제스트 채널

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
MAX_LEN = 4096


def split_message(text: str, max_len: int = MAX_LEN) -> List[str]:
    if len(text) <= max_len:
        return [text]
    parts, buf, count = [], [], 0
    for line in text.splitlines(keepends=True):
        if count + len(line) > max_len:
            parts.append("".join(buf))
            buf, count = [line], len(line)
        else:
            buf.append(line)
            count += len(line)
    if buf:
        parts.append("".join(buf))
    return parts


def send_message(chat_id: str, text: str):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False,
    }
    r = requests.post(API_URL, data=payload, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Telegram API error: {r.status_code} {r.text}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN environment variable.")

    content_path = os.environ.get(
        "CONTENT_PATH", "culture_brief/content/2025-11-07_culture_brief.txt"
    )
    if len(sys.argv) > 1:
        content_path = sys.argv[1]

    with open(content_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    chunks = split_message(text)
    for part in chunks:
        for attempt in range(3):
            try:
                send_message(CHANNEL_ID, part)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))


if __name__ == "__main__":
    main()