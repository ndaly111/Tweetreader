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
import pandas as pd
import openpyxl

# ---------------------------
# Load Credentials from Environment Variables
# ---------------------------
EMAIL = os.environ.get("Gmail")
PASSWORD = os.environ.get("Gmail_Password")

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
        if DEBUG_MODE:
            print(f"Error converting time: {e} | Raw: {iso_time}")
        return "Unknown Time", None

# ---------------------------
# Function: Login to Google via Selenium
# ---------------------------
def login_google(driver, email, password):
    driver.get("https://accounts.google.com/v3/signin/identifier?hl=en")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "identifierId")))
    driver.find_element(By.ID, "identifierId").send_keys(email)
    driver.find_element(By.XPATH, "//*[@id='identifierNext']").click()
    time.sleep(3)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "password")))
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.XPATH, "//*[@id='passwordNext']").click()
    time.sleep(5)
    print("Google login successful.")

# ---------------------------
# Function: Login to Twitter using Google OAuth
# ---------------------------
def login_twitter_via_google(driver):
    driver.get("https://twitter.com/i/flow/login")
    try:
        google_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Sign in with Google')]"))
        )
        google_btn.click()
        time.sleep(10)  # Allow time for Twitter to complete authentication using the existing Google session
        print("Twitter login via Google successful.")
    except Exception as e:
        print(f"Error during Twitter OAuth login: {e}")

# ---------------------------
# Function: Scrape Tweets from Target Profile
# ---------------------------
def scrape_tweets(driver):
    driver.get(TARGET_PROFILE)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "article")))
    time.sleep(5)
    
    actions = ActionChains(driver)
    # Simulate human-like scrolling
    for _ in range(8):
        actions.send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(random.uniform(3, 6))
    
    articles = driver.find_elements(By.TAG_NAME, "article")
    tweets = []
    for article in articles:
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
            if DEBUG_MODE:
                print(f"Error extracting tweet: {e}")
            continue
    return tweets

# ---------------------------
# Main Function
# ---------------------------
def main():
    driver = webdriver.Chrome(options=options)
    try:
        # Login to Google first
        login_google(driver, EMAIL, PASSWORD)
        # Login to Twitter via Google OAuth
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

if __name__ == "__main__":
    main()
