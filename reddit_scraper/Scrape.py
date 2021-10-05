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
        1) Subreddit -> Name of subreddit (Use ' to delimit multiple)
        2) days -> Number of days of posts(submissions) to crawl
        """
        cache_dir = os.path.join(os.path.abspath(''), "scrape_history")
        if load_last:
            try:
                df = pd.read_csv(os.path.join(cache_dir, "reddit_posts.csv"))
                return df
            except:
                print("Error trying to load last cache, proceeding with scrape")
        s = Session()
        url = "https://api.pushshift.io/reddit/submission/search/"
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
        counter = 0
        for num in tqdm(range(1, days + 1)):
            last_time = int(time.time() - ((num - 1) * 60 * 60 * 24))
            
            while 1==1:
                params = {
                    "before": last_time,
                    "after": int(time.time() - (num * 60 * 60 * 24)),
                    "sort_type": "created_utc",
                    "sort": "asc",
                    "subreddit": subreddit
                }
                res = s.get(url, params=params)
                counter += 1
                try:
                    res = loads(res.text)
                except:
                    break
                data = res["data"]
                for post in data:
                    for ppty in properties:
                        try:
                            raw_dataset[ppty].append(post[properties[ppty]])
                        except KeyError:
                            raw_dataset[ppty].append("")
                    last_time = raw_dataset["Date"][-1]
                    raw_dataset["Date"][-1] = datetime.utcfromtimestamp(raw_dataset["Date"][-1]).strftime('%Y-%m-%d')
                if len(data) == 0:
                    break
        print("Total number of requests made:", counter)
        scraped = pd.DataFrame(raw_dataset)
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            scraped.to_csv(os.path.join(cache_dir, f"reddit_posts.csv"))
            scraped.to_csv(os.path.join(cache_dir, f"reddit_posts_{raw_dataset['Date'][-1]}.csv"))
        self.scrape_history = scraped
        return scraped
        
    def get_reddit_comments(self, subreddit:str, df:pd.DataFrame, save:bool=False, load_last:bool=False, MAX:int=5):
        """

        """
        url = "https://api.pushshift.io/reddit/comment/search/"
        bots = ["VisualMod"]
        s = Session()
        cache_dir = os.path.join(os.path.abspath(''), "comments_history")
        if load_last:
            try:
                comments = pd.read_csv(os.path.join(cache_dir,"comments.csv"))
                return comments
            except:
                print("Can't find previous cache, proceeding with crawl")
                pass
        comments = {
            "body": [],
            "score":[],
            "post_id":[]
        }
        for row in tqdm(df.iloc(), total=df.shape[0]):
            params = {
                "link_id": row["ID"],
                "subreddit": subreddit,
                "sort_type": "score",
                "sort": "desc"
            }
            res = s.get(url, params=params)
            try:
                res = loads(res.text)
            except:
                continue
            for comment in res["data"]:
                if comment["author"] in bots:
                    continue
                else:
                    comments["body"].append(comment["body"])
                    comments["score"].append(comment["score"])
                    comments["post_id"].append(row["ID"])
        comments = pd.DataFrame(comments)
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            comments.to_csv(os.path.join(cache_dir,f"comments.csv"))
            comments.to_csv(os.path.join(cache_dir,f"comments_{time.time().strftime('%Y-%m-%d')}.csv"))
            
        return comments
            


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
    def get_financial_data(self, limit:int=31):
        pass

if __name__ == "__main__":
    s = Scraper()
    DAYS = 31
    df = s.get_reddit_posts(subreddit="wallstreetbets,stocks,pennystocks", days=DAYS, save=True)
    df2 = s.get_stock_tickers(load_last=True)
    df3 = s.get_reddit_comments("wallstreetbets", df, save=True)
    print(df3)
    #print(df)