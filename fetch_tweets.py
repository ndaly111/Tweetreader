import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import time

# Change USERNAMES as needed. Using the account you specified.
USERNAMES = ["JPFinlayNBCS"]

# List of Nitter instances to try (update if needed)
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
    """
    Convert a time string in the format: "Mar 22, 2025 · 3:51 AM UTC"
    to Eastern Time and return a tuple (formatted_string, utc_datetime).
    """
    try:
        # Using strptime to parse the time string. Adjust format if needed.
        dt_utc = datetime.strptime(text_time, "%b %d, %Y · %I:%M %p UTC").replace(tzinfo=timezone.utc)
        dt_eastern = dt_utc.astimezone(ZoneInfo("America/New_York"))
        return dt_eastern.strftime("%b %d, %Y - %I:%M %p ET"), dt_utc
    except Exception as e:
        if DEBUG_MODE:
            print(f"⚠️ Failed to parse time: {e} | Raw: {text_time}")
        return "Unknown Time", None

def fetch_nitter_tweets(username):
    """
    Attempts to fetch tweets from the given username using a list of Nitter instances.
    Returns a tuple (tweets, skipped). Each tweet is a dict containing username, text, and time.
    """
    for instance in NITTER_INSTANCES:
        url = f"{instance}/{username}"
        print(f"🔍 Trying {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                print(f"❌ Received status {response.status_code} from {instance}")
                time.sleep(3)
                continue
        except Exception as e:
            print(f"❌ Request failed from {instance}: {e}")
            time.sleep(3)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        tweets = []
        skipped = []

        # Attempt to find tweet blocks; based on Nitter's layout these should be under a container like div.timeline-item
        tweet_items = soup.select("div.timeline-item")
        print(f"✅ Found {len(tweet_items)} tweet blocks on {instance}")

        if DEBUG_MODE and len(tweet_items) == 0:
            # Dump raw HTML for debugging
            with open("debug_nitter.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("⚠️ No tweet blocks found. Saved raw HTML to debug_nitter.html for inspection.")

        for item in tweet_items:
            # Use the Nitter layout: tweet text is often in a div with class "tweet-content"
            text_block = item.select_one("div.tweet-content")
            time_link = item.select_one("span.tweet-date > a")
            if not text_block or not time_link:
                continue

            tweet_text = text_block.get_text(strip=True)
            raw_time = time_link.get("title")  # Expected format: "Mar 22, 2025 · 3:51 AM UTC"
            if not raw_time:
                if DEBUG_MODE:
                    print("⚠️ No time string found for a tweet, skipping...")
                continue

            eastern_str, utc_time = convert_to_eastern(raw_time)
            if utc_time is None:
                continue

            # Filter tweets: only include those from the last 24 hours
            if (datetime.now(timezone.utc) - utc_time) <= timedelta(hours=24):
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
            print(f"✅ From {instance}: Collected {len(tweets)} tweets, skipped {len(skipped)}")
            return tweets, skipped

        time.sleep(3)

    print(f
