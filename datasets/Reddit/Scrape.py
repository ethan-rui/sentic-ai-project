import os
import time
import calendar
import pandas as pd
from ast import literal_eval
from json import loads
from datetime import datetime, timedelta
from tqdm import tqdm
from requests import Session

class Scraper():
    def __init__(self):
        config = loads(open(os.path.join(os.path.abspath(''), '../config/config.json')).read())
        reddit_config = config["Reddit"]
        # self.reddit = praw.Reddit(
        #         client_id=reddit_config["client_id"],
        #         client_secret=reddit_config["client_secret"],
        #         password=reddit_config["password"],
        #         user_agent=reddit_config["user_agent"],
        #         username=reddit_config["username"]
        #     )
        self.scrape_history = []
    def get_reddit_posts(self, subreddit:str, days:int=31, save:bool=False, load_last:bool=False):
        """
        Inputs:
        1) Subreddit -> Can only include one
        2) 
        """
        scrape_list = []
        cache_dir = os.path.join(os.path.abspath(''), "scrape_history")
        if load_last:
            for file in os.listdir(cache_dir):
                if file.endswith(".csv"):
                    scrape_list.append(pd.read_csv(os.path.join(cache_dir, file)))
            return scrape_list
        s = Session()
        url = "https://api.pushshift.io/reddit/submission/search/"
        
        for num in tqdm(range(1, days + 1)):
            params = {
                "before": int(time.time() - ((num - 1) * 60 * 60 * 24)),
                "after": int(time.time() - (num * 60 * 60 * 24)),
                "sort_type": "score",
                "sort": "desc",
                "subreddit": subreddit
            }
            res = s.get(url, params=params)
            res = loads(res.text)
            data = res["data"]
            raw_dataset = {
                "ID":[],
                "Date": [],
                "Username": [],
                "Title":[],
                "Content": [],
                "Upvotes":[],
            }
            properties = {
                "ID":"id",
                "Date": "created_utc",
                "Username": "author",
                "Title":"title",
                "Content": "selftext",
                "Upvotes": "score",
            }
            for post in data:
                for ppty in properties:
                    try:
                        raw_dataset[ppty].append(post[properties[ppty]])
                    except KeyError:
                        raw_dataset[ppty].append("")
                raw_dataset["Date"][-1] = datetime.utcfromtimestamp(raw_dataset["Date"][-1]).strftime('%Y-%m-%d')
            scrape_list.append(pd.DataFrame(raw_dataset))
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            for i in range(days):
                scrape_list[i].to_csv(os.path.join(cache_dir, f"reddit_posts_{i}.csv"))
        self.scrape_history = scrape_list
        return scrape_list
    def get_stock_tickers(self, save=False, load_last=False):
        """
        Returns Stock Tickers
        """
        if load_last:
            try:
                tickers = pd.read_csv(os.path.join(os.path.abspath(""), "tickers.csv"))
                return tickers
            except:
                print("Tickers not found")
                print("Proceeding with ticker scrape")
        s = Session()
        url = "https://api.stockanalysis.com/wp-json/sa/search?q=index"
        stocks = literal_eval(s.get(url).text)
        tickers = {
            "ticker":[],
            "Name":[],
        }
        for stock in tqdm(stocks):
            tickers["ticker"].append(stock["s"])
            tickers["Name"].append(stock["n"])
        tickers = pd.DataFrame(tickers)
        if save:
            tickers.to_csv(os.path.join(os.path.abspath(""), "tickers.csv"))
        return tickers
        

if __name__ == "__main__":
    s = Scraper()
    DAYS = 31
    df = s.get_reddit_posts(subreddit="wallstreetbets", days=DAYS, load_last=True)
    df2 = s.get_stock_tickers(load_last=True)
    print(df2)