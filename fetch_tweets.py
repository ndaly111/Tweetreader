import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
import feedparser


NITTER_BASE = os.getenv("NITTER_BASE", "https://nitter.net")
TARGET_USER = os.getenv("TWITTER_USER", "JPFinlayNBCS")
OUTPUT_FILE = "tweets.txt"
DAYS = 7


def fetch_nitter_rss(username: str):
    """Fetch recent tweets from a user via Nitter RSS."""
    url = f"{NITTER_BASE.rstrip('/')}/{username}/rss"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    feed = feedparser.parse(response.text)
    tweets = []
    for entry in feed.entries:
        if not hasattr(entry, "published_parsed"):
            continue
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - published) > timedelta(days=DAYS):
            continue

        eastern = published.astimezone(ZoneInfo("America/New_York"))
        tweets.append(
            {
                "text": entry.title,
                "time": eastern.strftime("%b %d, %Y - %I:%M %p ET"),
            }
        )

    return tweets


def main():
    tweets = fetch_nitter_rss(TARGET_USER)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        if tweets:
            for tweet in tweets:
                fh.write(f"{tweet['time']}\n{tweet['text']}\n\n")
        else:
            fh.write(f"No tweets found within the last {DAYS} days.\n")


if __name__ == "__main__":
    main()

