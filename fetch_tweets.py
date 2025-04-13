import time
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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
    print("⚠️ Credentials not set. Please set the environment variables 'GMAIL' and 'GMAIL_PASSWORD'.")
    exit(1)
else:
    print(f"✅ Using email: {EMAIL} (password is hidden)")

# ---------------------------
# Configuration
# ---------------------------
TARGET_PROFILE = "https://twitter.com/JPFinlayNBCS"
OUTPUT_FILE = "tweets.txt"

# ---------------------------
# Selenium Options
# ---------------------------
options = Options()
options.add_argument("--headless=new")  # Use new headless mode
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1280,800")
options.add_argument("--disable-blink-features=AutomationControlled")
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
    print("🔐 Starting Google login...")
    driver.get("https://accounts.google.com/v3/signin/identifier?hl=en")
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "identifierId")))
    driver.find_element(By.ID, "identifierId").send_keys(email)
    driver.find_element(By.ID, "identifierNext").click()

    try:
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, "password")))
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.ID, "passwordNext").click()
        print("✅ Google login successful.")
    except Exception as e:
        print(f"❌ Google login failed: {e}")
        driver.save_screenshot("google_login_error.png")

# ---------------------------
# Function: Login to Twitter using Google OAuth
# ---------------------------
def login_twitter_via_google(driver):
    print("🔄 Starting Twitter OAuth login via Google...")
    driver.get("https://twitter.com/i/flow/login")
    try:
        google_btn = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Sign in with Google')]"))
        )
        google_btn.click()
        time.sleep(12)
        print("✅ Twitter login via Google successful.")
    except Exception as e:
        print(f"❌ Twitter OAuth login failed: {e}")
        driver.save_screenshot("twitter_login_error.png")

# ---------------------------
# Function: Scrape Tweets from Target Profile
# ---------------------------
def scrape_tweets(driver):
    print(f"📄 Navigating to Twitter profile: {TARGET_PROFILE}")
    driver.get(TARGET_PROFILE)
    try:
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.TAG_NAME, "article")))
    except Exception as e:
        print(f"❌ Tweets did not load: {e}")
        return []

    time.sleep(8)
    actions = ActionChains(driver)
    for i in range(10):
        actions.send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(random.uniform(2, 4))

    articles = driver.find_elements(By.TAG_NAME, "article")
    print(f"✅ Found {len(articles)} tweets.")
    tweets = []
    for idx, article in enumerate(articles, 1):
        try:
            tweet_text_elem = article.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
            tweet_text = tweet_text_elem.text.strip()
            time_elem = article.find_element(By.TAG_NAME, "time")
            tweet_time_iso = time_elem.get_attribute("datetime")
            if not tweet_time_iso:
                continue
            eastern_str, utc_time = convert_to_eastern(tweet_time_iso)
            if utc_time and (datetime.now(timezone.utc) - utc_time) <= timedelta(hours=24):
                tweets.append({
                    "text": tweet_text,
                    "time": eastern_str
                })
        except Exception as e:
            print(f"⚠️ Skipped tweet {idx}: {e}")
            continue
    return tweets

# ---------------------------
# Main Function
# ---------------------------
def main():
    # Specify path if running in GitHub Actions
    chromedriver_path = "/usr/bin/chromedriver" if os.path.exists("/usr/bin/chromedriver") else None
    driver = webdriver.Chrome(service=Service(chromedriver_path) if chromedriver_path else None,
                              options=options)
    try:
        login_google(driver, EMAIL, PASSWORD)
        login_twitter_via_google(driver)
        time.sleep(10)
        tweets = scrape_tweets(driver)
        print(f"📦 Scraped {len(tweets)} tweets from {TARGET_PROFILE}.")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            if tweets:
                for tweet in tweets:
                    f.write(f"{tweet['time']}\n{tweet['text']}\n\n")
            else:
                f.write("No tweets found within the last 24 hours.\n")
    finally:
        driver.quit()
        print("🚪 Driver closed.")

if __name__ == "__main__":
    main()
