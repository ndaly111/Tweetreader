import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import time

USERNAMES = ["JPFinlayNBCS"]
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.nohost.network",
]
OUTPUT_FILE = "tweets.txt"
HEADERS = {"User-Agent": "Mozilla/5.0"}
DEBUG_MODE = True

def convert_to_eastern(text_time):
    try:
        dt_utc = datetime.strptime(text_time, "%b %d, %Y · %I:%M %p UTC").replace(tzinfo=timezone.utc)
        dt_eastern = dt_utc.astimezone(ZoneInfo("America/New_York"))
        return dt_eastern.strftime("%b %d, %Y - %I:%M %p ET"), dt_utc
    except Exception as e:
        if DEBUG_MODE:
            print(f"⚠️ Failed to parse time: {e} | Raw: {text_time}")
        return "Unknown Time", None

def fetch_nitter_tweets(username):
    for instance in NITTER_INSTANCES:
        url = f"{instance}/{username}"
        print(f"🔍 Trying {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                print(f"❌ Status {response.status_code} from {instance}")
                time.sleep(3)
                continue
        except Exception as e:
            print(f"❌ Request failed: {e}")
            time.sleep(3)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        tweets = []
        skipped = []

        for item in soup.select("div.timeline-item"):
            text_block = item.select_one("div.tweet-content")
            time_tag = item.select_one("span.tweet-date > a")

            if not text_block or not time_tag:
                continue

            tweet_text = text_block.get_text(strip=True)
            raw_time = time_tag.get("title")  # Format: Mar 22, 2025 · 3:51 AM UTC

            eastern_str, utc_time = convert_to_eastern(raw_time)
            if utc_time and (datetime.now(timezone.utc) - utc_time <= timedelta(hours=24)):
                tweets.append({
                    "username": username,
                    "text": tweet_text,
                    "time": eastern_str
                })
            else:
                skipped.append({
                    "username": username,
                    "text": tweet_text,
                    "time": eastern_str,
                    "reason": "⏩ Older than 24 hours"
                })

        if tweets or skipped:
            print(f"✅ Fetched {len(tweets)} tweets and skipped {len(skipped)} from {instance}")
            return tweets, skipped

        time.sleep(3)

    print(f"❌ No working Nitter instance returned tweets for {username}")
    return [], []

def main():
    all_tweets = []
    skipped_tweets = []

    for username in USERNAMES:
        tweets, skipped = fetch_nitter_tweets(username)
        all_tweets.extend(tweets)
        skipped_tweets.extend(skipped)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("✅ SAVED TWEETS:\n\n")
        for idx, tweet in enumerate(all_tweets, 1):
            f.write(f"{idx}. @{tweet['username']} - {tweet['time']}\n")
            f.write(f"   Tweet: {tweet['text']}\n\n")

        f.write("\n⏩ SKIPPED TWEETS:\n\n")
        for idx, tweet in enumerate(skipped_tweets, 1):
            f.write(f"{idx}. @{tweet['username']} - {tweet['time']} ({tweet['reason']})\n")
            f.write(f"   Tweet: {tweet['text']}\n\n")

    print(f"✅ Saved {len(all_tweets)} tweets and {len(skipped_tweets)} skipped to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
