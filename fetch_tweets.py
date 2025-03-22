import requests
from bs4 import BeautifulSoup
import datetime

USERNAMES = ["jpfinlayNBCS"]  # Add more Twitter usernames here
OUTPUT_FILE = "tweets.txt"

def fetch_tweets(username):
    url = f"https://mobile.twitter.com/{username}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch {username}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    tweets = []

    for tweet_div in soup.find_all("table", class_="tweet"):
        tweet_text = tweet_div.find("div", class_="dir-ltr").get_text(strip=True)
        time_tag = tweet_div.find("td", class_="timestamp")
        time_text = time_tag.get_text(strip=True) if time_tag else "Unknown Time"
        tweets.append({
            "username": username,
            "text": tweet_text,
            "time": time_text
        })
    return tweets

def main():
    all_tweets = []
    for username in USERNAMES:
        all_tweets.extend(fetch_tweets(username))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for idx, tweet in enumerate(all_tweets, 1):
            f.write(f"{idx}. @{tweet['username']}\n")
            f.write(f"   Time: {tweet['time']}\n")
            f.write(f"   Tweet: {tweet['text']}\n\n")

    print(f"Saved {len(all_tweets)} tweets to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
