import feedparser
import time
import datetime
import os

# You can track multiple usernames if you wish:
USERNAMES = [
    "jpfinlayNBCS"
    # You can add more, for example: "elonmusk", "jack", etc.
]

# Base Nitter instance (change if nitter.net is down):
NITTER_BASE = "https://nitter.net"

# Output file where we'll store tweets in plain text:
OUTPUT_TEXT_FILE = "tweets.txt"

def main():
    # We'll open the file in write mode each time, overwriting old content.
    # If you prefer to append, use mode="a" instead of "w".
    with open(OUTPUT_TEXT_FILE, "w", encoding="utf-8") as outfile:
        for username in USERNAMES:
            feed_url = f"{NITTER_BASE}/{username}/rss"
            print(f"Fetching RSS feed: {feed_url}")
            
            # Parse the RSS
            feed = feedparser.parse(feed_url)

            # Optional: check HTTP status if available
            if hasattr(feed, 'status'):
                print(f" - HTTP status: {feed.status}")
                if feed.status != 200:
                    print("   Something might be wrong (or the instance is down).")
                    outfile.write(f"\nERROR fetching {username}: HTTP {feed.status}\n")
                    continue  # skip this user if error

            # Print feed info (just for debugging)
            feed_title = feed.feed.get("title", f"Tweets by {username}")
            print(f" - Feed Title: {feed_title}\n")

            outfile.write(f"=== {feed_title} ===\n")

            # Iterate through entries
            entries = feed.entries[:10]  # limit to the first 10 for brevity
            if not entries:
                outfile.write("No tweets found or feed is empty.\n\n")
                continue

            for idx, entry in enumerate(entries, start=1):
                # Title is usually the tweet text
                title = entry.title if hasattr(entry, "title") else "No title"
                link = entry.link if hasattr(entry, "link") else "No link"

                # Published time
                if hasattr(entry, "published"):
                    published = entry.published
                else:
                    # fallback if not present
                    published = "No published date"

                # Write to console
                print(f"{idx}. {title}")
                print(f"   Link:  {link}")
                print(f"   Time:  {published}\n")

                # Write to our output file
                outfile.write(f"{idx}. {title}\n")
                outfile.write(f"   Link:  {link}\n")
                outfile.write(f"   Time:  {published}\n\n")

            outfile.write("\n")  # extra spacing after each user's feed

    print(f"\nDone! Output saved to '{OUTPUT_TEXT_FILE}'.")

if __name__ == "__main__":
    main()