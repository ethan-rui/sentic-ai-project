from Cleaner import Cleaner
from matplotlib import pyplot as plt
from datetime import time, timedelta
from ast import literal_eval
import pandas as pd



class Analysis:
    def __init__(self):
        pass
    def pack_to_tickers(self, df_list:list, stock_col:str="Stock"):
        ticker_dict = {}
        merged_df = pd.concat(df_list)
        for row in merged_df.iloc():
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
                d = pd.DataFrame([{"Date":group[1]["Date"][0],"Average Sentiment": group[1]["score"].sum() / group[1]["score"].count()}\
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
            d = pd.DataFrame([{"Date":group[1]["Date"][0],"Average Sentiment": group[1]["score"].sum() / group[1]["score"].count()}\
                for group in ticker_dict[ticker].groupby(ticker_dict[ticker].index.date)])
            d.set_index("Date")
            print(d)
            d.plot(x="Date",y="Average Sentiment", ylabel="Average Sentiment",\
            ylim=(0, 1), label=f"Sentiment Analysis for {ticker}")
            plt.axhline(y=0.70, color="g",linestyle="-")
        plt.show()
        
if __name__ == "__main__":
    cleaner = Cleaner()
    a = Analysis()
    df_tickerlabel_list = cleaner.label_tickers(df_list=None, tickers=None, targeted_col_name="Title", load_last=True)    

    ticker_dict = a.pack_to_tickers(cleaner.sentiment_analysis(df_tickerlabel_list, load_last=True))
    a.average_daily_sentiment(ticker_dict=ticker_dict, ticker="SPY",top=10, limit=14)

                
    
    