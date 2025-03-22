import requests
from bs4 import BeautifulSoup

USERNAMES = ["jpfinlayNBCS"]
NITTER_INSTANCE = "https://nitter.net"  # You can change to a live instance
OUTPUT_FILE = "tweets.txt"

def fetch_nitter_tweets(username):
    url = f"{NITTER_INSTANCE}/{username}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch {username}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    tweets = []

    for tweet in soup.find_all("div", class_="tweet-content"):
        tweet_text = tweet.get_text(strip=True)
        time_tag = tweet.find_parent("div", class_="timeline-item").find("span", class_="tweet-date")
        tweet_time = time_tag.get_text(strip=True) if time_tag else "Unknown Time"
        tweets.append({
            "username": username,
            "text": tweet_text,
            "time": tweet_time
        })

    return tweets

def main():
    all_tweets = []
    for username in USERNAMES:
        all_tweets.extend(fetch_nitter_tweets(username))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for idx, tweet in enumerate(all_tweets, 1):
            f.write(f"{idx}. @{tweet['username']}\n")
            f.write(f"   Time: {tweet['time']}\n")
            f.write(f"   Tweet: {tweet['text']}\n\n")

    print(f"Saved {len(all_tweets)} tweets to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
