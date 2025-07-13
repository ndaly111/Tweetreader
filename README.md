# Tweetreader

This project fetches the latest tweets from a specific Twitter profile using Selenium.

The `fetch_tweets.py` script logs in to Twitter via a Google account (credentials supplied through the `GMAIL` and `GMAIL_PASSWORD` environment variables) and saves recent tweets to `tweets.txt`.

By default it retrieves tweets from the last seven days of `JPFinlayNBCS`.

## Usage

Install the dependencies and run the script:

```bash
pip install -r requirements.txt
GMAIL=your_email@gmail.com GMAIL_PASSWORD=your_password python fetch_tweets.py
```

The results will be written to `tweets.txt`.
