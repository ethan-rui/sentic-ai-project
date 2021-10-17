from datetime import datetime, timedelta
from transformers import pipeline
from langdetect import detect
import nest_asyncio
import pandas as pd
import numpy as np
import shelve
import twint
import os
import re

nest_asyncio.apply()
BASEDIR = os.getcwd()


class TwitterSentimentAnalysis:
    def __init__(self, cwd: None):
        print(f"Data would be stored in {BASEDIR}")
        self.cwd = BASEDIR if cwd != None else cwd

    def scrape(self, date_from=None, date_to=None, search_query=None):
        if date_from == None:
            print("Date from is not defined, defaulting to current date")
            # Today's date
            # date_from = datetime.today().strftime("%Y-%m-%d")
            date_from = (datetime.today() - timedelta(1)).strftime("%Y-%m-%d")

        if date_to == None:
            # Tomorrow's date
            print("Date to is not defined, defaulting to the next day")
            date_to = (datetime.today() + timedelta(1)).strftime("%Y-%m-%d")

        # If both are not defined, the scaper would only scrape today's tweets

        tweets = pd.DataFrame(columns=["date", "tweet"])
        c = twint.Config()
        # c.Username = "elonmusk"
        # c.Limit = 10
        c.Limit = 1000
        c.Store_csv = False
        c.Pandas = True
        c.Hide_output = True
        c.Since = date_from
        c.Until = date_to
        c.Min_likes = 10
        # Getting only English tweets, undefined == all,
        # Lang codes here https://github.com/twintproject/twint/wiki/Langauge-codes
        # This shit is not accurate
        c.Lang = "en"

        # Search = "string OR string AND string"
        c.Search = search_query

        twint.run.Search(c)

        df = twint.storage.panda.Tweets_df
        try:
            # tweets = tweets.append(df[["date", "user_id", "username", "tweet", "nlikes", "nretweets", "nreplies"]])
            tweets = tweets.append(df[["date", "tweet"]])
        except KeyError:
            print("No more data!")
        try:
            os.mkdir("../datasets")
        except:
            pass
        try:
            os.mkdir("../datasets/twitter")
        except:
            pass
        tweets.to_csv(f"../datasets/twitter/tweets.csv")
        print(f"Data Preview\n{tweets.head()}")
        return tweets

    def clean(self, path=None):
        # This function would clean each individual tweet
        def tweet_clean(tweet):
            try:
                if detect(tweet) != "en":
                    return np.NaN
            except:
                return np.NaN
            tweet = re.sub("@[A-Za-z0-9_]+", "", tweet)
            tweet = re.sub("#[A-Za-z0-9_]+", "", tweet)
            tweet = re.sub(
                r"(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)", "", tweet
            )
            tweet = re.sub(r"www.\S+", "", tweet)
            return tweet

        if path == None:
            path = f"../datasets/twitter/tweets.csv"

        try:
            tweets = pd.read_csv(path)
        except:
            print(f"Tweets not found in {self.cwd}/data\nExiting...")
            return
        else:
            tweets["cleaned_tweet"] = tweets["tweet"].apply(tweet_clean)
            print(tweets.head())
            tweets = tweets.dropna()
            tweets = tweets.drop_duplicates()
            tweets.to_csv(f"../datasets/twitter/tweets_cleaned.csv")

        return tweets

    def sentiment_analysis(self, path=None):
        sentiment = pipeline("sentiment-analysis")
        if path == None:
            path = f"../datasets/twitter/tweets_cleaned.csv"

        def sentiment_tweet(tweet):
            label, score = sentiment(tweet)[0].values()
            if label == "NEGATIVE":
                return 1 - score
            else:
                return score

        tweets = pd.read_csv(f"../datasets/twitter/tweets_cleaned.csv")
        tweets["sentiment"] = tweets["tweet"].apply(sentiment_tweet)
        print(tweets.head())
        tweets.to_csv(f"../datasets/twitter/tweets_sentiment.csv")
        print("Average Sentiment:", tweets["sentiment"].sum() / len(tweets.index))

        return tweets

    def average_sentiment(self, path=None, ticker=None):
        if path == None:
            path = f"../datasets/twitter/tweets_sentiment.csv"

        try:
            tweets = pd.read_csv(path)
        except:
            print(f"Tweets not found in {path}")
            return
        else:
            average_sentiment = tweets["sentiment"].sum() / len(tweets.index)
            with shelve.open("../logs/sentiment_values.db") as db:
                db[ticker] = {
                    "ticker": ticker,
                    "average_sentiment": average_sentiment,
                    "time": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
                }
            return average_sentiment


if __name__ == "__main__":
    test = TwitterSentimentAnalysis(cwd=BASEDIR)
    test.scrape(search_query="a")
