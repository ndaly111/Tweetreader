import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
import feedparser
import pandas as pd

# Base URL for Nitter instance (can be overridden via environment variable)
NITTER_BASE = os.getenv("NITTER_BASE", "https://nitter.net")
# File containing a list of Twitter usernames (one per line)
ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", "accounts.txt")
# Output Excel file to store fetched tweets
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "tweets.xlsx")
# Number of days to look back when filtering tweets
DAYS = int(os.getenv("DAYS", "7"))


def fetch_nitter_rss(username: str) -> list:
    """Fetch recent tweets from a user via Nitter RSS.

    Args:
        username: Twitter username to fetch tweets for.

    Returns:
        A list of dictionaries with tweet text and timestamp (Eastern Time).
    """
    url = f"{NITTER_BASE}/{username}/rss"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    feed = feedparser.parse(response.text)
    tweets = []
    for entry in feed.entries:
        if not hasattr(entry, "published_parsed"):
            # Skip entries without a published timestamp
            continue
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        # Skip tweets older than the cutoff
        if (datetime.now(timezone.utc) - published) > timedelta(days=DAYS):
            continue
        eastern = published.astimezone(ZoneInfo("America/New_York"))
        tweets.append(
            {
                "account": username,
                "text": entry.title,
                "time": eastern.strftime("%b %d, %Y - %I:%M %p ET"),
            }
        )
    return tweets


def main() -> None:
    """Read accounts and fetch tweets for each, saving to an Excel file."""
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"No accounts file found: {ACCOUNTS_FILE}")
        return

    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as fh:
        accounts = [line.strip() for line in fh if line.strip()]

    all_tweets = []
    for account in accounts:
        try:
            all_tweets.extend(fetch_nitter_rss(account))
        except Exception as exc:
            # Log errors but continue with other accounts
            print(f"Failed to fetch for {account}: {exc}")

    if all_tweets:
        df = pd.DataFrame(all_tweets)
        # Sort tweets by time descending
        df["parsed_time"] = pd.to_datetime(df["time"])
        df.sort_values(by="parsed_time", ascending=False, inplace=True)
        df.drop(columns=["parsed_time"], inplace=True)
        df.to_excel(OUTPUT_FILE, index=False)
    else:
        # If no tweets were found, write an empty Excel file and a message
        empty_df = pd.DataFrame()
        empty_df.to_excel(OUTPUT_FILE, index=False)
        with open("tweets.txt", "w", encoding="utf-8") as f:
            f.write(f"No tweets found within the last {DAYS} days.\n")
       

if __name__ == "__main__":
    main()