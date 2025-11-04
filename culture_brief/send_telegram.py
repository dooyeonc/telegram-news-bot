import os, requests, time

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = "@newsnissue"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_message(text: str):
    res = requests.post(API_URL, data={
        "chat_id": CHANNEL_ID,
        "text": text,
        "disable_web_page_preview": False
    }, timeout=30)
    if not res.ok:
        raise RuntimeError(f"Telegram error: {res.status_code} {res.text}")

def split_text(text, max_len=4096):
    parts, buf, count = [], [], 0
    for line in text.splitlines(keepends=True):
        if count + len(line) > max_len:
            parts.append("".join(buf))
            buf, count = [line], len(line)
        else:
            buf.append(line)
            count += len(line)
    if buf: parts.append("".join(buf))
    return parts

def main():
    path = os.environ.get("CONTENT_PATH", "culture_brief/content/2025-11-07_culture_brief.txt")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    for part in split_text(text):
        for i in range(3):
            try:
                send_message(part)
                break
            except Exception as e:
                if i == 2:
                    raise
                time.sleep(2 * (i + 1))

if __name__ == "__main__":
    main()