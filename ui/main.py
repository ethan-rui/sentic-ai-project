import os
import sys
import shelve
import nest_asyncio
import pandas as pd
import time

from datetime import datetime, timedelta
from flask import Flask, url_for, request
from flask.templating import render_template

from news import news
from reddit import reddit

sys.path.insert(0, "../twitter_scraper")
sys.path.insert(0, "../reddit_scraper")
sys.path.insert(0, "../predictor")

# Stock Forecast
from Stock_Prediction import StockForecast

# Twitter Module(s)
from TwitterScrape import TwitterSentimentAnalysis


import shelve

BASEDIR = os.getcwd()
print(f"Current directory: {BASEDIR}")

app = Flask(
    __name__,
    template_folder=f"{BASEDIR}/templates",
    static_folder=f"{BASEDIR}/templates",
)

app.register_blueprint(news)
app.register_blueprint(reddit)

app.config["SECRET_KEY"] = "1234"


def datetime_difference(date_from, date_to):
    date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S")
    date_to = datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S")
    return (date_to - date_from).total_seconds()


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
        print("\n", seconds_diff, "\n")
    except KeyError:
        seconds_diff = 36001

    if seconds_diff < 36000:
        return {"sentiment": db[search_query]["average_sentiment"] * 100}
    else:
        scraper = TwitterSentimentAnalysis(cwd=BASEDIR)
        scraper.scrape(search_query=search_query)
        scraper.clean()
        scraper.sentiment_analysis()
        return {"sentiment": scraper.average_sentiment(ticker=search_query) * 100}



@app.route("/stock-prediction")
def stock_prediction():
    try:
        with shelve.open("../logs/stock_prices") as db:
            data = dict(db)

        date_now = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
        if not datetime_difference(data["BTC-USD"]["date_created"], date_now) > 100000:
            ticker_data = data["BTC-USD"]
            return {
                "actual_prices": ticker_data["actual_prices"],
                "predicted_prices": ticker_data["predicted_prices"],
                "labels": ticker_data["days"],
            }
    except KeyError:
        print("Repredicting stocks")

    test = StockForecast(window=60)
    ticker_prices = test.get_ticker_prices(ticker="BTC-USD", mode="load")
    x_train, y_train = test.data_preprocessing(ticker_prices)
    model = test.build_model(x_train, y_train, ticker="BTC-USD", mode="load")
    actual_prices, predicted_prices, days = test.prediction(
        previous_days=45, model=model, ticker="BTC-USD"
    )
    print(days)
    with shelve.open("../logs/stock_prices", flag="c") as db:
        db["BTC-USD"] = {
            "actual_prices": list(actual_prices),
            "predicted_prices": list(predicted_prices),
            "days": days,
            "date_created": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        }
    return {
        "actual_prices": list(actual_prices),
        "predicted_prices": list(predicted_prices),
        "labels": days,
    }


if __name__ == "__main__":
    app.run(debug=True)
