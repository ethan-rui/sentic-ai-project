import os
import sys
import shelve
import nest_asyncio
from datetime import datetime
from flask import Flask, url_for, request
from flask.templating import render_template

sys.path.insert(0, "..\\twitter_scraper")
from TwitterScrape import TwitterSentimentAnalysis


BASEDIR = os.getcwd()
print(f"Current directory: {BASEDIR}")

app = Flask(
    __name__,
    template_folder=f"{BASEDIR}/templates",
    static_folder=f"{BASEDIR}/templates",
)

app.config["SECRET_KEY"] = "1234"


@app.route("/", methods=["GET"])
def page_home():
    return render_template("index.html")


@app.route("/twitter-sentiment")
def twitter_sentiment():
    search_query = request.args.get("ticker").upper()

    logs = shelve.open("../logs/sentiment_values.db")
    db = dict(logs)
    logs.close()

    try:
        seconds_diff = datetime_difference(
            db[search_query]["time"], f"{datetime.now():%Y-%m-%d %H:%M:%S}"
        )
    except KeyError:
        seconds_diff = 101

    if seconds_diff < 100:
        return {"sentiment": db[search_query]["average_sentiment"] * 100}
    else:
        scraper = TwitterSentimentAnalysis(cwd=BASEDIR)
        scraper.scrape(search_query=search_query)
        scraper.clean()
        scraper.sentiment_analysis()
        return {"sentiment": scraper.average_sentiment(ticker=search_query) * 100}


def datetime_difference(date_from, date_to):
    date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S")
    date_to = datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S")
    return (date_to - date_from).total_seconds()


if __name__ == "__main__":
    app.run(debug=True)
