# Tweetreader

This project fetches the latest tweets from a specific Twitter profile using the
public Nitter RSS feed. No API credentials or login are required.

The `fetch_tweets.py` script downloads the user's RSS feed and saves recent
tweets to `tweets.txt`.

By default it retrieves tweets from the last seven days of `JPFinlayNBCS`.

## Usage

Install the dependencies and run the script:

```bash
pip install -r requirements.txt
python fetch_tweets.py  # optionally set TWITTER_USER and NITTER_BASE
```

The results will be written to `tweets.txt`.
