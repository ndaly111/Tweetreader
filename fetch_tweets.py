import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

USERNAMES = ["JPFinlayNBCS"]
OUTPUT_FILE = "tweets.txt"
DEBUG_MODE = True
FILTER_LAST_24_HOURS = True

def convert_to_eastern(iso_time):
    try:
        iso_time = iso_time.replace('Z', '+00:00')
        utc_time = datetime.fromisoformat(iso_time)
        eastern = utc_time.astimezone(ZoneInfo('America/New_York'))
        return eastern.strftime("%b %d, %Y - %I:%M %p ET"), utc_time
    except Exception as e:
        if DEBUG_MODE:
            print(f"⚠️ Error parsing time: {e} | Raw time: {iso_time}")
        return "Unknown Time", None

async def fetch_tweets(username):
    tweets_collected = []
    skipped_tweets = []
    url = f"https://twitter.com/{username}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Fetching tweets from {url}")
        await page.goto(url, timeout=60000)
        await page.wait_for_selector('article', timeout=15000)

        last_height = await page.evaluate("document.body.scrollHeight")

        # ✅ Slow, interactive scrolling to load tweets naturally
        for _ in range(8):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(5000)  # Wait 5 seconds per scroll
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break  # Exit if no more content loads
            last_height = new_height

        tweet_articles = await page.locator('article').all()
        print(f"✅ Found {len(tweet_articles)} tweet articles")

        for article in tweet_articles:
            try:
                tweet_text = await article.locator('div[data-testid="tweetText"]').inner_text()
                tweet_time_iso = await article.locator('time').get_attribute('datetime')

                if not tweet_time_iso:
                    if DEBUG_MODE:
                        print("⚠️ Time tag missing, skipping...")
                    continue

                eastern_time_str, utc_time = convert_to_eastern(tweet_time_iso)
                tweets_collected.append({
                    "username": username,
                    "text": tweet_text.strip(),
                    "time": eastern_time_str,
                    "utc_time": utc_time
                })
            except Exception as e:
                if DEBUG_MODE:
                    print(f"⚠️ Error processing tweet: {e}")
                continue

        await browser.close()

    tweets_collected.sort(key=lambda x: x['utc_time'], reverse=True)

    final_tweets = []
    for tweet in tweets_collected:
        if FILTER_LAST_24_HOURS:
            if tweet['utc_time'] and (datetime.now(tz=ZoneInfo('UTC')) - tweet['utc_time']) <= timedelta(hours=24):
                final_tweets.append(tweet)
            else:
                skipped_tweets.append({**tweet, "reason": "⏩ Older than 24 hours"})
        else:
            final_tweets.append(tweet)

    return final_tweets, skipped_tweets

async def main():
    all_tweets = []
    skipped_tweets = []

    for username in USERNAMES:
        tweets, skipped = await fetch_tweets(username)
        print(f"✅ Fetched {len(tweets)} tweets from {username}")
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

    print(f"✅ Saved {len(all_tweets)} tweets and {len(skipped_tweets)} skipped tweets to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
