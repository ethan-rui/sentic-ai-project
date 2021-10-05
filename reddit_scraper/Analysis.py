from Cleaner import Cleaner
from matplotlib import pyplot as plt
from datetime import time, timedelta
from ast import literal_eval
from tqdm import tqdm
import os
import pandas as pd



class Analysis:
    def __init__(self):
        pass
    def pack_to_tickers(self, df:pd.DataFrame, stock_col:str="Stock"):
        ticker_dict = {}
        for row in df.iloc():
            for ticker in literal_eval(row[stock_col]):
                try:
                    ticker_dict[ticker].append(row)
                except KeyError:
                    ticker_dict[ticker] = [row]
        for ticker in ticker_dict:
            ticker_dict[ticker] = pd.DataFrame(ticker_dict[ticker])
            ticker_dict[ticker]["Date"] = pd.to_datetime(ticker_dict[ticker]["Date"])
            ticker_dict[ticker].index = ticker_dict[ticker]["Date"]
        return ticker_dict
    
    def pack_comments_to_posts(self, df_posts:pd.DataFrame, df_comments:pd.DataFrame, name:str="posts", save:bool=False, load_last:bool=False):
        packed_df = df_posts.copy()
        evaluation = []
        comments_score = []
        cache_dir = os.path.join(os.path.abspath(""), "evaluate_history")
        if load_last:
            try:
                df = pd.read_csv(os.path.join(cache_dir, f"evaluated_{name}.csv"))
                return df
            except:
                print("Error loading previous saved, proceeding with packing and evaluation")
        for post in tqdm(df_posts.iloc(), total=df_posts.shape[0]):
            related_comments = df_comments[df_comments["post_id"] == post["ID"]]
            related_comments = related_comments["score"]
            evaluation.append(self.evaluation_matrix(post["score"], related_comments))
            comments_score.append(df_comments["score"])
        packed_df["sentiment_score"] = evaluation
        packed_df["comments_score"] = comments_score
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            packed_df.to_csv(os.path.join(cache_dir, f"evaluated_{name}.csv"))
        return packed_df
    @staticmethod
    def evaluation_matrix(post_score:float, comments_score:list, w1:int = 2, w2:int = 1):
        counter = w1
        total = post_score * w1
        for comment in comments_score:
            total += comment * w2
            counter += w2
        total /= counter
        return total

    def average_daily_sentiment(self, ticker_dict: dict, ticker: str="SPY", top: int=0,limit: int=31):
        # Sorting rows in dataframes by day
        """
        1) top10 -> Most talked ticker
        """
        fig, ax = plt.subplots()
        if top != 0:
            # Find Top 10 tickers
            sorted_ticker_dict = dict(sorted(ticker_dict.items(),key=lambda item: item[1]['score'].count(), reverse=True))
            counter = 0
            for ticker in sorted_ticker_dict:
                if counter == top:
                    break
                d = pd.DataFrame([{"Date":group[1]["Date"][0],"Average Sentiment": group[1]["sentiment_score"].sum() / group[1]["score"].count()}\
                    for group in ticker_dict[ticker].groupby(ticker_dict[ticker].index.date)])
                d = d[d["Date"] > d["Date"].max() - timedelta(days=limit)]
                if d["Date"].count() > 1:
                    ax.plot(d["Date"], d["Average Sentiment"], label=f"{ticker}")
                else:
                    print("Graphs with only one day are not plotted")
                    continue
                counter += 1
            ax.set_xlabel("Date")
            ax.set_ylabel("Average Sentiment")
            ax.set_title(f"Average Sentiment Analysis of Top {top} tickers")
            ax.axhline(y=0.70, color="g",linestyle="-")
            ax.legend(loc='best')
        else:    
            d = pd.DataFrame([{"Date":group[1]["Date"][0],"Average Sentiment": group[1]["sentiment_score"].sum() / group[1]["score"].count()}\
                for group in ticker_dict[ticker].groupby(ticker_dict[ticker].index.date)])
            d.set_index("Date")
            print(d)
            d.plot(x="Date",y="Average Sentiment", ylabel="Average Sentiment",\
            ylim=(0, 1), label=f"Sentiment Analysis for {ticker}")
            plt.axhline(y=0.70, color="g",linestyle="-")
        plt.show()
        
def main():
    cleaner = Cleaner()
    a = Analysis()
    df_tickerlabel_list = cleaner.label_tickers(df=None, tickers=None, targeted_col_name="Title",new_col_name=None, dfname="posts", load_last=True)    

    #ticker_dict = a.pack_to_tickers(cleaner.sentiment_analysis(df_tickerlabel_list, load_last=True))
    posts_sentiment_list = cleaner.sentiment_analysis(None, "Concepts", "posts", load_last=True)
    comments_sentiment_list = cleaner.sentiment_analysis(None, "Concepts", "comments", load_last=True)
    
    removed_string = "Your submission was removed from"
    comments_sentiment_list = comments_sentiment_list[~comments_sentiment_list["body"].str.contains(removed_string)]
    ticker_dict = a.pack_to_tickers(a.pack_comments_to_posts(df_posts=posts_sentiment_list, df_comments=comments_sentiment_list,name="posts3", load_last=True))

    a.average_daily_sentiment(ticker_dict=ticker_dict, ticker="SPY",top=5, limit=14)


if __name__ == "__main__":
    main()

                
    
    