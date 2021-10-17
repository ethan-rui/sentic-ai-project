# Scraping tools
from requests import get as crawl, Session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
from time import sleep
from random import randint

import sys
import os
import pandas as pd
import time
import shelve


# UI Stuff
from flask import Blueprint, render_template, abort, request
from json import loads
sys.path.insert(0, "../reddit_scraper")

from Cleaner import Cleaner 
from Scrape import Scraper
from Analysis import Analysis


news = Blueprint("news", __name__, template_folder="./templates")
news_api = loads(open("../config/config.json").read())["StockNews"]["Stock_TOKEN"]

opts = Options()
opts.add_argument("User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko)")
opts.add_argument("--headless")

headers = {
    "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko)"
}

def datetime_difference(date_from, date_to):
    date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S")
    date_to = datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S")
    return (date_to - date_from).total_seconds()

# Yahoo Scrape

def get_info(url, s : Session):
    res = s.get(url, headers=headers)
    soup = BS(res.text, "lxml")
    try:
        news = soup.find('div', attrs = {'class': 'caas-body'}).text
    except:
        print(res.url)
    headline = soup.find('h1').text
    date = datetime.strptime(soup.find("time").text, "%B %d, %Y, %I:%M %p")
    
    return dict(zip(["News", "Title", "Date", "link"],[news, headline, date, url]))
def scrape_news(name:str = "", stock:bool = False, crypto:bool = False, sets:int = 1, wait:float=2, load_last:bool=False, save:bool=False):
    
    # Load Last
    cache_dir = os.path.join(os.path.abspath(""), "scrape_history")
    if load_last:
        try:
            return pd.read_csv(os.path.join(cache_dir, f"news_scrape_{name}.csv"))
        except:
            print("Error in loading last scrape, proceeding with scraping.")

    TOPICS = []
    if not(stock) and not(crypto):
        print("stock or crypto argument needs to be defined as True to scrape")
        raise ValueError
    if stock:
        TOPICS.append("stock-market-news")
    if crypto:
        TOPICS.append("crypto")
    dicts = []
    for topic in TOPICS:
        # Get all URLs
        
        url = f"https://finance.yahoo.com/topic/{topic}/"
        driver = webdriver.Chrome(chrome_options=opts)
        soup = driver.get(url)
        links = []
        x = 1
        
        for x in range(sets):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"Wait for news to load ({wait} seconds)")
            sleep(wait)
            soup = BS(driver.execute_script("return document.body.innerHTML;"), 'lxml')
            while True:
                try:
                    links.append(soup.select(f"#Fin-Stream > ul > li:nth-child({x}) a")[0]["href"])
                except Exception as e:
                    break
                x += 1
        
        s = Session()
        for link in links:
            dicts.append(get_info("https://finance.yahoo.com" + link, s))
        print("Finished scraping", topic)
    result = pd.DataFrame(dicts)
    if save:
        try:
            os.mkdir(cache_dir)
        except:
            pass
        result.to_csv(os.path.join(cache_dir, f"news_scrape_{name}.csv"))
    return result


@news.route("/news-sentiment")
def new_sentiment():
    search_query = request.args.get("ticker") if request.args["ticker"] else "BTC"
    start_time = time.time()    
    s = Scraper()
    logs = None
    try:
        with shelve.open("../logs/news_sentiment_values.db","c") as db:
            logs = db["ticker"]            
    except:
        pass
    tickers = s.get_tickers(load_last=True)
    if search_query not in list(tickers["ticker"]):
        return {"news": "Not found"}
    if logs == None:
        logs = news_analysis(SETS=30, THREADS=10)
        ticker_data = logs[search_query].sort_values(by=["score"],ascending=False)
        data = dict(zip(["Title","Sentiment"],[list(ticker_data["Title"]),list(ticker_data["score"])]))
        return {"news": data}
    else:
        # Check if news is "up to date", having the current day's news
        latest_date = pd.concat(logs.values())["Date"].max()
        days_diff = timedelta(
            seconds=datetime_difference(
                str(latest_date),
                f"{datetime.now():%Y-%m-%d %H:%M:%S}",
            )
        ).days
        if days_diff >= 2:
            logs = news_analysis(SETS=30, THREADS=10)
            ticker_data = logs[search_query].sort_values(by=["score"],ascending=False)
            data = dict(zip(["Title","Sentiment"],[list(ticker_data["Title"]),list(ticker_data["score"])]))
            return {"news": data}
        ticker_data = logs[search_query].sort_values(by=["score"],ascending=False)
        data = dict(zip(["Title","Sentiment"],[list(ticker_data["Title"]),list(ticker_data["score"])]))
        return {"news": data}
        
def news_analysis(SETS:int=5, THREADS:int = 1):
    """
    Analysing all News
    # TODO
    data = cleaner.sentiment_analysis(df=data, targeted_col_name=CONCEPT_NAME, dfname=NAME, save=True) \\
    must be made into a lambda function, so other analysis function can be easily integrated
    """
    NAME = "News"
    CONCEPT_NAME = "Concepts"
    cleaner = Cleaner()
    scraper = Scraper()
    analysis = Analysis()

    tickers = scraper.get_tickers(load_last=True)
    #print(tickers)
    data = scrape_news(name="crypto&stock",sets=SETS, crypto=True, stock=True, save=True) # 5 sets scrapes abt "18 hours worth" of news
    

    # data = cleaner.label_tickers(df=data, tickers=tickers, targeted_col_name="News", new_col_name="Ticker", dfname=NAME, save=True)
    # data = cleaner.concept_parse(df=data, targeted_col_name="Title", new_col_name=CONCEPT_NAME, dfname=NAME, save=True, THREADS=THREADS, debug=True)
    # data = cleaner.sentiment_analysis(df=data, targeted_col_name=CONCEPT_NAME, dfname=NAME, save=True)
    print(data)
    
    return analysis.pack_to_tickers(df=data, stock_col="Ticker", name="news")

    

if __name__ == "__main__":
    news_analysis( SETS = 3, THREADS = 20)
    #s = Scraper()
    #print(s.get_tickers(load_last=True))
    # Last Scraped: 70 Sets (5 Sets is around 18 hours worth of news)
    

