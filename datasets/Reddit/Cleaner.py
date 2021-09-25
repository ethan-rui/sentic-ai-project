
from json import loads
from requests import Session
from threading import Thread
from tqdm import tqdm
from transformers import pipeline
from ast import literal_eval
import itertools  
import pandas as pd
import numpy as np
import os
import re


class Cleaner:
    def __init__(self):
        config = loads(open(os.path.join(os.path.abspath(''), '../config/config.json')).read())
        self.returns = None # Note remember to initialise this variable as a list before using Cleaner.SenticNet 
        self.sentic_config = config["SenticNet"]
        self.sentiment = None
    def concept_parse(self, df_list: list, targeted_col_name:str, new_col_name : str, load_last: bool=False\
        , save: bool=False, THREADS: int=10):
        """
        Desc:
        Input:
        1) List of dataframes(From Reddit_Scrape)
        Output:
        2) List of dataframes with an additional column
        """
        cache_dir = os.path.join(os.path.abspath(''), "clean_history")
        new_df_list = []
        if load_last:
            try:
                for file in os.listdir(cache_dir):
                    if file.endswith(".csv"):
                        new_df_list.append(pd.read_csv(os.path.join(cache_dir, file)))
                return new_df_list
            except:
                print("\n".join(["Error has occurred","Proceeding with normal parsing..."]))
        CP_API=self.sentic_config["Concept_Parsing"]
        
        for index in tqdm(range(len(df_list))):
            # Splitting dataset
            new_df = df_list[index].copy()
            splitted_ds = np.array_split(new_df, THREADS)
            # Sentic Concept Parse
            self.returns = [None] * THREADS
            ts = [None] * THREADS
            for thread_num in range(THREADS):
                ts[thread_num] = Thread(target=self.SenticNet, args=(splitted_ds[thread_num], CP_API, targeted_col_name, thread_num))
                ts[thread_num].start()
            for x in range(THREADS):
                ts[x].join()
            new_df[new_col_name] = list(itertools.chain.from_iterable(self.returns))
            new_df_list.append(new_df)
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            for x in range(len(new_df_list)):
                new_df_list[x].to_csv(os.path.join(cache_dir, f"cleaned_reddit_posts_{x}.csv"))
        return new_df_list
            
    def SenticNet(self, dataset : pd.DataFrame, API_KEY : str, targeted_col_name:str="Concepts" , thread_num:int=10, \
        LANGUAGE:str ="en")->pd.DataFrame:
        """
        Require: 
        1) Dataset with ["Content"] column
        2) API Key for SenticNet API
        3) Targeted Column's name for passing content
        4) Column Name for data obtained from SenticNet API
        5) Thread Number (For storing returns)
        Returns:
        Set Column to returns variable at the given thread number (In order)
        """
        s = Session()
        url = f"https://sentic.net/api/{LANGUAGE}/{API_KEY}.py"
        new_col = []
        for row in dataset.iloc():
            params = {
                "text" : row[targeted_col_name].replace(" ", "%20")
            }
            res = s.get(url, params=params)
            new_col.append(res.text)
        self.returns[thread_num] = new_col
    def label_tickers(self, df_list: list, tickers:pd.DataFrame, targeted_col_name:str, new_col_name: str="Stock", save:bool=False, load_last:bool=False):
        cache_dir = os.path.join(os.path.abspath(''), "label_history")
        new_df_list = []
        if load_last:
            try:
                for file in os.listdir(cache_dir):
                    if file.endswith('.csv'):
                        new_df_list.append(pd.read_csv(os.path.join(cache_dir, file)))
                return new_df_list
            except:
                print("\n".join(["Error has occurred","Proceeding with labeling..."]))
        patterns = {ticker:re.compile(f"\W{ticker}\W") for ticker in tickers["ticker"].iloc()}
        
        
        for index in tqdm(range(len(df_list))):
            filtered_dataset = {
                "Comment/Post": [],
                "Corresponding ticker": []
            }
            for x in range(len(df_list[index][targeted_col_name])):
                tkers = []
                for ticker in patterns:
                    results = re.search(patterns[ticker], df_list[index][targeted_col_name][x])
                    if results:
                        tkers.append(ticker)
                if len(tkers) != 0:
                    filtered_dataset["Comment/Post"].append(df_list[index].iloc[x])
                    filtered_dataset["Corresponding ticker"].append(tkers)
            df = pd.DataFrame(filtered_dataset["Comment/Post"])
            df[new_col_name] = filtered_dataset["Corresponding ticker"]
            new_df_list.append(df)
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            for x in range(len(new_df_list)):
                new_df_list[x].to_csv(os.path.join(cache_dir,f"labelled_tickers_{x}.csv"))
        return new_df_list

    def sentiment_analysis(self, df_list:list,  targeted_col_name:str="Concepts", save:bool=False, load_last:bool=False):
        cache_dir = os.path.join(os.path.abspath(''), "sentiment_history")
        if load_last:
            returned_df_list = []
            for file in os.listdir(cache_dir):
                if file.endswith(".csv"):
                    returned_df_list.append(pd.read_csv(os.path.join(cache_dir,file)))
            return returned_df_list

        if self.sentiment == None:
            self.sentiment = pipeline("sentiment-analysis")
        for index in tqdm(range(len(df_list))):
            df_list[index]["score"] = df_list[index][targeted_col_name].apply(self.sentiment_analysis_handler)
    
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            for df in range(len(df_list)):
                df_list[df].to_csv(os.path.join(cache_dir, f"sentiment_{df}.csv"))
                
        return df_list
    def sentiment_analysis_handler(self, content):
        content = content.strip()
        if content[0] != "[": # Implies that the SenticNetAPI did not extract any concepts
            return 0
        content = literal_eval(content)
        datas = self.sentiment(content)
        total = 0
        for data in datas:
            if(data["label"] == "NEGATIVE"):
                total += 1-data["score"] 
            else:
                total += data["score"]
        if len(datas) != 0:
            return total / len(datas)
        else:
            return 0
    
    
if __name__ == "__main__":
    from Scrape import Scraper
    s = Scraper()
    cleaner = Cleaner()
    stock_list = s.get_reddit_posts("wallstreetbets", load_last=True)
    ticker_list = s.get_stock_tickers(save=True)
    df_list = cleaner.concept_parse(stock_list, "Title", "Concepts", save=True)
    df_tickerlabel_list = cleaner.label_tickers(df_list=df_list, tickers=ticker_list, targeted_col_name="Title", save=True)    
    df_sentiment_list = cleaner.sentiment_analysis(df_tickerlabel_list)
    print(df_tickerlabel_list)