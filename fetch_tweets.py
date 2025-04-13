import time
import random
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# ---------------------------
# Load Credentials from Environment Variables
# ---------------------------
EMAIL = os.environ.get("GMAIL")
PASSWORD = os.environ.get("GMAIL_PASSWORD")
if not EMAIL or not PASSWORD:
    print("⚠️ Credentials not set. Please set the environment variables 'GMAIL' and 'GMAIL_PASSWORDS'.")
    exit(1)
else:
    print(f"Using email: {EMAIL} (password hidden)")

# ---------------------------
# Configuration
# ---------------------------
TARGET_PROFILE = "https://twitter.com/JPFinlayNBCS"
OUTPUT_FILE = "tweets.txt"
FILTER_LAST_24_HOURS = True
DEBUG_MODE = True

# ---------------------------
# Selenium Options
# ---------------------------
options = Options()
options.add_experimental_option("detach", True)
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1280,800")
options.add_argument("--disable-popup-blocking")
options.add_argument("--disable-save-password-bubble")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/115.0.0.0 Safari/537.36")

# ---------------------------
# Utility: Convert UTC time string to Eastern Time
# ---------------------------
def convert_to_eastern(iso_time):
    try:
        iso_time = iso_time.replace("Z", "+00:00")
        utc_time = datetime.fromisoformat(iso_time)
        eastern = utc_time.astimezone(ZoneInfo("America/New_York"))
        return eastern.strftime("%b %d, %Y - %I:%M %p ET"), utc_time
    except Exception as e:
        print(f"Error converting time: {e} | Raw: {iso_time}")
        return "Unknown Time", None

# ---------------------------
# Function: Login to Google via Selenium
# ---------------------------
def login_google(driver, email, password):
    print("Starting Google login...")
    driver.get("https://accounts.google.com/v3/signin/identifier?hl=en")
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "identifierId")))
    print("Email field located.")
    driver.find_element(By.ID, "identifierId").send_keys(email)
    print("Email entered.")
    driver.find_element(By.XPATH, "//*[@id='identifierNext']").click()
    print("Clicked 'Next' for email.")
    time.sleep(5)  # Wait for password field to load
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, "password")))
    print("Password field located.")
    driver.find_element(By.NAME, "password").send_keys(password)
    print("Password entered.")
    driver.find_element(By.XPATH, "//*[@id='passwordNext']").click()
    time.sleep(8)
    print("Google login successful.")

# ---------------------------
# Function: Login to Twitter using Google OAuth
# ---------------------------
def login_twitter_via_google(driver):
    print("Starting Twitter OAuth login via Google...")
    driver.get("https://twitter.com/i/flow/login")
    try:
        google_btn = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Sign in with Google')]"))
        )
        print("Found 'Sign in with Google' button.")
        google_btn.click()
        time.sleep(12)
        print("Twitter login via Google successful.")
    except Exception as e:
        print(f"Error during Twitter OAuth login: {e}")

# ---------------------------
# Function: Scrape Tweets from Target Profile
# ---------------------------
def scrape_tweets(driver):
    print(f"Navigating to Twitter profile: {TARGET_PROFILE}")
    driver.get(TARGET_PROFILE)
    try:
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.TAG_NAME, "article")))
    except Exception as e:
        print(f"Error: tweets (article elements) did not load - {e}")
        return []
    time.sleep(8)  # Additional wait to ensure tweets load

    # Scrolling behavior: mimic human browsing behavior
    actions = ActionChains(driver)
    for i in range(10):
        scroll_distance = random.randint(300, 700)
        actions.send_keys(Keys.PAGE_DOWN).perform()
        pause = random.uniform(3, 6)
        print(f"Scroll {i+1}: Scrolled {scroll_distance}px, pausing for {pause:.2f} seconds")
        time.sleep(pause)

    articles = driver.find_elements(By.TAG_NAME, "article")
    print(f"Found {len(articles)} articles on the page.")
    tweets = []
    for idx, article in enumerate(articles, 1):
        try:
            tweet_text_elem = article.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
            tweet_text = tweet_text_elem.text.strip()
            time_elem = article.find_element(By.TAG_NAME, "time")
            tweet_time_iso = time_elem.get_attribute("datetime")
            if not tweet_time_iso:
                print(f"Article {idx}: No datetime attribute found.")
                continue
            eastern_str, utc_time = convert_to_eastern(tweet_time_iso)
            print(f"Article {idx}: Tweet time (UTC): {utc_time}, Eastern: {eastern_str}")
            # Only include tweets from the last 24 hours
            if utc_time and (datetime.now(timezone.utc) - utc_time) <= timedelta(hours=24):
                tweets.append({
                    "text": tweet_text,
                    "time": eastern_str
                })
                print(f"Article {idx}: Added tweet: {tweet_text[:60]}...")
            else:
                print(f"Article {idx}: Tweet is older than 24 hours, skipped.")
        except Exception as e:
            print(f"Error processing article {idx}: {e}")
            continue
    return tweets

# ---------------------------
# Main Function
# ---------------------------
def main():
    driver = webdriver.Chrome(options=options)
    try:
        login_google(driver, EMAIL, PASSWORD)
        login_twitter_via_google(driver)
        time.sleep(10)
        tweets = scrape_tweets(driver)
        print(f"Scraped {len(tweets)} tweets from {TARGET_PROFILE}.")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            if tweets:
                for tweet in tweets:
                    f.write(f"{tweet['time']}\n")
                    f.write(tweet["text"] + "\n\n")
            else:
                f.write("No tweets found within the last 24 hours.\n")
    finally:
        driver.quit()
        print("Driver closed.")

if __name__ == "__main__":
    main()
