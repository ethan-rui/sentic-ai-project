import sys
from stocknews import StockNews
from crypto
from flask import Blueprint, render_template, abort, request
from json import loads
sys.path.insert(0, "../reddit_scraper")

from Scrape import Scraper as RedditScraper

news = Blueprint("news", __name__, template_folder="./templates")
news_api = loads(open("../config/config.json").read())["StockNews"]["Stock_TOKEN"]
def scrape(ticker:str):
    sn = StockNews(ticker,wt_key=news_api)
    print(sn.summarize())
@news.route("/news-sentiment")
def new_sentiment():
    search_query = request.args.get("ticker") if request.args["ticker"] else "BTC"
    ds = scrape(search_query)

if __name__ == "__main__":
    scrape("BTC")


