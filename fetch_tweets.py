import asyncio
from playwright.async_api import async_playwright

USERNAMES = ["JPFinlayNBCS"]
OUTPUT_FILE = "tweets.txt"
MAX_TWEETS = 10  # Adjust how many tweets you want

async def fetch_tweets(username):
    tweets = []
    url = f"https://twitter.com/{username}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = await context.new_page()

        print(f"Fetching tweets from {url}")
        await page.goto(url, timeout=60000)

        # ✅ Wait for tweets to load
        await page.wait_for_selector('article', timeout=15000)
        tweet_articles = await page.locator('article').all()

        for article in tweet_articles:
            try:
                tweet_text = await article.locator('div[data-testid="tweetText"]').inner_text()
                tweets.append({
                    "username": username,
                    "text": tweet_text.strip()
                })
                if len(tweets) >= MAX_TWEETS:
                    break
            except:
                continue  # Skip if the tweet content is missing

        await browser.close()
    return tweets

async def main():
    all_tweets = []
    for username in USERNAMES:
        tweets = await fetch_tweets(username)
        if tweets:
            print(f"✅ Fetched {len(tweets)} tweets from {username}")
        else:
            print(f"❌ No tweets found for {username}")
        all_tweets.extend(tweets)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for idx, tweet in enumerate(all_tweets, 1):
            f.write(f"{idx}. @{tweet['username']}\n")
            f.write(f"   Tweet: {tweet['text']}\n\n")

    print(f"✅ Saved {len(all_tweets)} tweets to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
