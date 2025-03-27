import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

LIST_URL = "https://x.com/i/lists/940937136844476421"
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

async def fetch_tweets_from_list():
    tweets_collected = []
    skipped_tweets = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Fetching tweets from {LIST_URL}")
        await page.goto(LIST_URL, timeout=60000)
        await page.wait_for_timeout(8000)  # Wait for list content to load

        scrolls = 0
        MAX_SCROLLS = 10
        recent_found = False

        while scrolls < MAX_SCROLLS:
            tweet_blocks = await page.locator('div[data-testid="cellInnerDiv"]').all()
            print(f"✅ Found {len(tweet_blocks)} tweet blocks (scroll {scrolls+1})")

            for block in tweet_blocks:
                try:
                    tweet_text = await block.locator('div[data-testid="tweetText"]').inner_text()
                    tweet_time_iso = await block.locator('time').get_attribute('datetime')

                    if not tweet_time_iso:
                        continue

                    eastern_time_str, utc_time = convert_to_eastern(tweet_time_iso)
                    tweets_collected.append({
                        "text": tweet_text.strip(),
                        "time": eastern_time_str,
                        "utc_time": utc_time
                    })

                    if utc_time and (datetime.now(tz=ZoneInfo('UTC')) - utc_time) <= timedelta(hours=24):
                        recent_found = True

                except Exception as e:
                    if DEBUG_MODE:
                        print(f"⚠️ Error processing tweet: {e}")
                    continue

            if recent_found:
                print("✅ Recent tweet found, stopping scroll early")
                break

            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_timeout(4000)
            scrolls += 1

        if len(tweets_collected) == 0 and DEBUG_MODE:
            html_content = await page.content()
            with open("debug_list.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("❌ No tweets collected. Page content saved to debug_list.html for review.")

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
    tweets, skipped_tweets = await fetch_tweets_from_list()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("✅ SAVED TWEETS:\n\n")
        for idx, tweet in enumerate(tweets, 1):
            f.write(f"{idx}. {tweet['time']}\n")
            f.write(f"   Tweet: {tweet['text']}\n\n")

        f.write("\n⏩ SKIPPED TWEETS:\n\n")
        for idx, tweet in enumerate(skipped_tweets, 1):
            f.write(f"{idx}. {tweet['time']} ({tweet['reason']})\n")
            f.write(f"   Tweet: {tweet['text']}\n\n")

    print(f"✅ Saved {len(tweets)} tweets and {len(skipped_tweets)} skipped tweets to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())