import feedparser

# The Nitter instance we'll try to use:
NITTER_BASE = "https://nitter.net"

# The Twitter username we want to follow (without the @):
USERNAME = "jpfinlayNBCS"

def main():
    # Build the RSS feed URL for this username
    feed_url = f"{NITTER_BASE}/{USERNAME}/rss"
    
    print(f"Attempting to fetch RSS feed:\n  {feed_url}\n")

    # Parse the feed
    feed = feedparser.parse(feed_url)

    # If feed.status is available, it can help diagnose success or failure
    if hasattr(feed, 'status'):
        print(f"HTTP status: {feed.status}")
        if feed.status != 200:
            print("There may be an error or the Nitter instance is down.")
    
    # Print basic feed info
    print(f"Feed Title: {feed.feed.get('title', 'No title')}")
    print(f"Feed Link: {feed.feed.get('link', 'No link')}")
    print("\n--- Recent Entries ---\n")

    # Loop through the first few entries (tweets)
    for idx, entry in enumerate(feed.entries[:5], start=1):
        print(f"{idx}. Title: {entry.title}")
        print(f"   Link:  {entry.link}")
        if hasattr(entry, 'published'):
            print(f"   Time:  {entry.published}")
        print("")

    print("Done.")

if __name__ == "__main__":
    main()
