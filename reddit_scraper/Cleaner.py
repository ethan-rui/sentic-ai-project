
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
    sentic_values = { 
        "NEGATIVE": -1,
        "NEUTRAL": 0,
        "POSITIVE": 1,
        "SUBJECTIVE": 1,
        "AMBIVALENT": -1,
        "OBJECTIVE": 0
    }
    def __init__(self):
        config = loads(open(os.path.join(os.path.abspath(''), '../config/config.json')).read())
        self.returns = None # Note remember to initialise this variable as a list before using Cleaner.SenticNet 
        self.sentic_config = config["SenticNet"]
        self.sentiment = None
    
    def SenticValuesHandler(self, df:pd.DataFrame, targeted_col_name:str="Subjectivity,Polarity", new_col_name:str = "Score"):
        new_df = df.copy()
        
        for col_name in targeted_col_name.split(","):
            converted_values = []
            for row in df.iloc():
                converted_values.append(Cleaner.sentic_values[row[col_name].strip()])
            new_df[col_name + "_" + new_col_name] = converted_values
        return new_df

    def SenticNet(self, api_type:str, df:pd.DataFrame,  targeted_col_name:str, new_col_name : str, dfname:str, load_last: bool=False\
        , save: bool=False, THREADS: int=10, debug:bool=False):
        """
        Desc:
        Input:
        1) Dataframe
        2) Targeted column name to extract concepts
        3) New column name for storing concepts
        4) Name of dataframe (for storing purposes)
        Output:
        1) Dataframe with an additional column for parsed concepts
        """
        cache_dir = os.path.join(os.path.abspath(''), "clean_history")
        if load_last:
            try:
                returned_df = pd.read_csv(os.path.join(cache_dir, f"cleaned_{dfname}.csv"))
                return returned_df
            except:
                print("\n".join(["Error has occurred","Proceeding with normal parsing..."]))
        CP_API=self.sentic_config[api_type]
        
        # Splitting dataset
        new_df = df.copy()
        splitted_ds = np.array_split(new_df, THREADS)
        # Sentic Concept Parse
        self.returns = [None] * THREADS
        ts = [None] * THREADS
        for thread_num in range(THREADS):
            ts[thread_num] = Thread(target=self.SenticNetHandler, args=(splitted_ds[thread_num], CP_API, targeted_col_name, thread_num, debug))
            ts[thread_num].start()
        for x in tqdm(range(THREADS)):
            ts[x].join()
        new_df[new_col_name] = list(itertools.chain.from_iterable(self.returns))
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            new_df.to_csv(os.path.join(cache_dir, f"cleaned_{dfname}.csv"))
        return new_df
            
    def SenticNetHandler(self, dataset : pd.DataFrame, API_KEY : str, targeted_col_name:str="Concepts" , thread_num:int=10, debug:bool=False, \
        LANGUAGE:str ="en")->pd.DataFrame:
        """
        Require: 
        1) Dataset with "Content" column
        2) API Key for SenticNet API
        3) Targeted Column's name for passing content
        4) Column Name for data obtained from SenticNet API
        5) Thread Number (For storing returns)
        Returns:
        1) Set Column to returns variable at the given thread number (In order)
        """
        s = Session()
        url = f"https://sentic.net/api/{LANGUAGE}/{API_KEY}.py"
        new_col = []
        for row in dataset.iloc():
            params = {
                "text" : row[targeted_col_name].replace(" ", "%20")
            }
            try:
                res = s.get(url, params=params)
            except:
                splitted_row = row[targeted_col_name].split(" ")
                params = {
                    "text" : "%20".join([str(word) for word in splitted_row][:int(len(splitted_row) / 2)]) # Limit params
                }
                res = s.get(url, params=params)
            if debug:
                print("\v")
                print(row)
                print(res.text)
                print("\v")
            new_col.append(res.text)
        self.returns[thread_num] = new_col
    def label_tickers(self, df: pd.DataFrame, tickers:pd.DataFrame, targeted_col_name:str, new_col_name: str, dfname:str, save:bool=False, load_last:bool=False):
        cache_dir = os.path.join(os.path.abspath(''), "label_history")
        
        if load_last:
            try:
                df = pd.read_csv(os.path.join(cache_dir, f"labelled_tickers_{dfname}.csv"))
                return df
            except:
                print("\n".join(["Error has occurred","Proceeding with labeling..."]))
        patterns = {ticker:re.compile(f"\W{re.escape(ticker)}\W") for ticker in tickers["ticker"].iloc()}
        
        #print(patterns)
        filtered_dataset = {
            "Comment/Post": [],
            "Corresponding ticker": []
        }
        for x in tqdm(range(len(df[targeted_col_name]))):
            tkers = []
            for ticker in patterns:
                results = re.search(patterns[ticker], df[targeted_col_name][x])
                if results:
                    tkers.append(ticker)
            if len(tkers) != 0:
                filtered_dataset["Comment/Post"].append(df.iloc[x])
                filtered_dataset["Corresponding ticker"].append(tkers)
        returned_df = pd.DataFrame(filtered_dataset["Comment/Post"])
        returned_df[new_col_name] = filtered_dataset["Corresponding ticker"]
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            returned_df.to_csv(os.path.join(cache_dir, f"labelled_tickers_{dfname}.csv"))
        return returned_df

    def transformers_sentiment_analysis(self, df:pd.DataFrame,  targeted_col_name:str, dfname:str, save:bool=False, load_last:bool=False):
        """
        Sentiment Using Transformers
        """
        cache_dir = os.path.join(os.path.abspath(''), "sentiment_history")
        if load_last:
            try:
                df = pd.read_csv(os.path.join(cache_dir, f"sentiment_{dfname}.csv"))    
                return df
            except:
                print("Targeted file not found, proceeding with clean(sentiment)")
                pass

        if self.sentiment == None:
            self.sentiment = pipeline("sentiment-analysis")
        tqdm.pandas() # For TQDM in pandas
        print("Running")
        df["score"] = df[targeted_col_name].apply(self.sentiment_analysis_handler)
    
        if save:
            try:
                os.mkdir(cache_dir)
            except:
                pass
            df.to_csv(os.path.join(cache_dir, f"sentiment_{dfname}.csv"))
        return df
    def sentiment_analysis_handler(self, content:str):
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
def main():
    from Scrape import Scraper
    s = Scraper()
    cleaner = Cleaner()
    raw_post_list = s.get_reddit_posts("wallstreetbets", load_last=True)
    raw_comment_list = s.get_reddit_comments("wallstreetbets,stocks,pennystocks", None, load_last=True)
    # ticker_list = s.get_stock_tickers(load_last=True)
    # posts_list = cleaner.concept_parse(raw_post_list, "Title", "Concepts", "posts", load_last=True, THREADS=50)
    comments_list = cleaner.SenticNet("Concept_Parsing",raw_comment_list, "body", "Concepts", "reddit_comments", load_last=True, THREADS=50).iloc()[:2000]
    comments_list = cleaner.SenticNet("Subjectivity_Detection",raw_comment_list, "body", "Subjectivity", "subjectivity_reddit_comments", save=True, THREADS=50)
    comments_list = cleaner.SenticNet("Polarity_Classification",raw_comment_list, "body", "Polarity", "polarity_reddit_comments", save=True, THREADS=50)
    print(comments_list)
    # df_tickerlabel_list = cleaner.label_tickers(df=posts_list, tickers=ticker_list, targeted_col_name="Title",new_col_name="Stock",dfname="posts", load_last=True)
    
    # comments_list = comments_list[comments_list["post_id"].isin(posts_list["ID"])] # Filter out comments from posts that are not included (not labelled)
    
    # print(comments_list)
    # posts_sentiment_list = cleaner.transformers_sentiment_analysis(df_tickerlabel_list, "Concepts", "posts", save=True)
    # comments_sentiment_list = cleaner.transformers_sentiment_analysis(comments_list, "Concepts", "comments", save=True)
    # print(df_tickerlabel_list)


    
if __name__ == "__main__":
    main()