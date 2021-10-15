import sys
from stocknews import StockNews # For Stocks

# Scraping tools  [For Crypto]
from requests import get as crawl, Session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup as BS
from datetime import datetime
from time import sleep
from tqdm import tqdm

import os
import pandas as pd
import platform
# UI Stuff
from flask import Blueprint, render_template, abort, request
from json import loads
sys.path.insert(0, "../reddit_scraper")

#from Scrape import Scraper as RedditScraper
#from Cleaner import Cleaner

news = Blueprint("news", __name__, template_folder="./templates")
news_api = loads(open("../config/config.json").read())["StockNews"]["Stock_TOKEN"]

opts = Options()
opts.add_argument("User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko)")
opts.add_argument("--headless")

headers = {
    "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko)"
}



def stock_scrape(ticker:str):
    sn = StockNews(ticker,wt_key=news_api)
    print(sn.summarize())
    # TODO: Implement sentiment analysis on articles by stock

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
    
    return dict(zip(["News", "Title", "Date"],[news, headline, date]))
def crypto_scrape(sets:int = 1, wait:float=2, save:bool=False, load_last:bool = False, name:str=""):
    cache_dir = os.path.join(os.path.abspath(""),"crypto_news_history")
    if load_last:
        try:
            return pd.read_csv(os.path.join(cache_dir, "fin_news{}.csv".format(name)))
        except:
            print("Reading from cache failed, manually scraping now")

    # Get all URLs
    url = "https://finance.yahoo.com/topic/crypto/"
    if platform.system() == "Darwin":
        driver = webdriver.Chrome(options=opts, executable_path="./chromedriver_mac")
    else:
        driver = webdriver.Chrome(options=opts)
    soup = driver.get(url)
    links = []
    x = 1
    
    for x in range(sets):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print("Wait for news to load ({} seconds)".format(wait))
        sleep(wait)
        soup = BS(driver.execute_script("return document.body.innerHTML;"), 'lxml')
        while True:
            try:
                links.append(soup.select("#Fin-Stream > ul > li:nth-child({}) a".format(x))[0]["href"])
            except Exception as e:
                break
            x += 1
    dicts = []
    s = Session()
    print("Found",len(links),"links.")
    for link in tqdm(links):
        dicts.append(get_info("https://finance.yahoo.com" + link, s))
    result = pd.DataFrame(dicts)
    if save:
        results.to_csv(os.path.join(cache_dir, "fin_news{}.csv".format(name)))
    return result






@news.route("/news-sentiment")
def new_sentiment():
    search_query = request.args.get("ticker") if request.args["ticker"] else "BTC"
    ds = scrape(search_query)

if __name__ == "__main__":
    result = crypto_scrape(100, 1, save=True)
    print(result)
    print("Scraped",len(result),"of links")
    

