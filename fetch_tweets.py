import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Configuration
USER = "JPFinlayNBCS"
URL = f"https://twitter.com/{USER}"  # Change if you want to scrape a list instead
OUTPUT_FILE = "tweets.txt"
FILTER_LAST_24_HOURS = True
DEBUG_MODE = True

def convert_to_eastern(iso_time):
    """
    Convert ISO time string (e.g., "2025-03-22T03:51:00.000Z")
    to Eastern Time and return (formatted string, utc_datetime).
    """
    try:
        iso_time = iso_time.replace("Z", "+00:00")
        utc_time = datetime.fromisoformat(iso_time)
        eastern = utc_time.astimezone(ZoneInfo("America/New_York"))
        return eastern.strftime("%b %d, %Y - %I:%M %p ET"), utc_time
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error converting time: {e}")
        return "Unknown Time", None

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    # Use a realistic user agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/115.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def fetch_tweets():
    driver = setup_driver()
    driver.get(URL)
    time.sleep(5)  # Allow initial page load

    tweets_collected = []
    seen_tweets = set()
    scroll_attempts = 0
    MAX_SCROLLS = 15
    recent_found = False

    # Continue scrolling until we either detect at least one tweet within the last 24 hours or reach MAX_SCROLLS.
    while scroll_attempts < MAX_SCROLLS and not recent_found:
        articles = driver.find_elements(By.TAG_NAME, "article")
        print(f"Found {len(articles)} articles on scroll {scroll_attempts+1}")
        for article in articles:
            try:
                # Use a CSS selector to extract tweet text
                tweet_text_elem = article.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
                tweet_text = tweet_text_elem.text.strip()
                if tweet_text in seen_tweets:
                    continue
                seen_tweets.add(tweet_text)
                
                # Get the time element
                time_elem = article.find_element(By.TAG_NAME, "time")
                tweet_time_iso = time_elem.get_attribute("datetime")
                if not tweet_time_iso:
                    continue
                eastern_str, utc_time = convert_to_eastern(tweet_time_iso)
                tweet = {
                    "username": USER,
                    "text": tweet_text,
                    "time": eastern_str,
                    "utc_time": utc_time
                }
                tweets_collected.append(tweet)
                # If any tweet is within the last 24 hours, mark as recent
                if utc_time and (datetime.now(timezone.utc) - utc_time) <= timedelta(hours=24):
                    recent_found = True
            except Exception as e:
                if DEBUG_MODE:
                    print(f"Error processing an article: {e}")
                continue
        
        if recent_found:
            print("Recent tweet found, stopping scroll.")
            break
        
        # Simulate human-like scrolling:
        scroll_distance = random.randint(400, 800)
        driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
        pause_time = random.randint(4, 9)
        print(f"Scrolling {scroll_distance}px, pausing {pause_time} seconds.")
        time.sleep(pause_time)
        scroll_attempts += 1

    driver.quit()

    # Sort tweets by UTC timestamp (most recent first)
    tweets_collected.sort(key=lambda x: x["utc_time"], reverse=True)

    # Apply filtering if enabled
    final_tweets = []
    skipped_tweets = []
    for tweet in tweets_collected:
        if FILTER_LAST_24_HOURS:
            if tweet["utc_time"] and (datetime.now(timezone.utc) - tweet["utc_time"]) <= timedelta(hours=24):
                final_tweets.append(tweet)
            else:
                tweet["reason"] = "Older than 24 hours"
                skipped_tweets.append(tweet)
        else:
            final_tweets.append(tweet)
    
    return final_tweets, skipped_tweets

def main():
    tweets, skipped = fetch_tweets()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("✅ SAVED TWEETS:\n\n")
        if tweets:
            for idx, tweet in enumerate(tweets, 1):
                f.write(f"{idx}. @{tweet['username']} - {tweet['time']}\n")
                f.write(f"   Tweet: {tweet['text']}\n\n")
        else:
            f.write("No tweets found.\n\n")
        
        f.write("\n⏩ SKIPPED TWEETS:\n\n")
        if skipped:
            for idx, tweet in enumerate(skipped, 1):
                f.write(f"{idx}. @{tweet['username']} - {tweet['time']} ({tweet.get('reason','')})\n")
                f.write(f"   Tweet: {tweet['text']}\n\n")
        else:
            f.write("No tweets were skipped.\n\n")
    print(f"✅ Saved {len(tweets)} tweets and {len(skipped)} skipped to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
