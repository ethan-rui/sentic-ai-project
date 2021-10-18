
from flask import Blueprint, render_template, abort, request

# Reddit Module(s)
from Analysis import Analysis as RedditAnalysis
from Cleaner import Cleaner as RedditCleaner
from Scrape import Scraper as RedditScraper
from datetime import datetime, timedelta


reddit = Blueprint("reddit", __name__, template_folder="./templates")

def datetime_difference(date_from, date_to):
    date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S")
    date_to = datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S")
    return (date_to - date_from).total_seconds()

@reddit.route("/reddit-sentiment")
def reddit_sentiment():
    # Returns Daily sentiment value for a day
    # Note for now this should only work with Crypto Tickers
    start_time = time.time()
    search_query = request.args.get("ticker").upper()

    db = None
    with shelve.open("../logs/reddit_sentiment_values.db", "c") as logs:
        try:
            db = dict(logs)["ticker"]
        except:
            pass
        # print(db)
    try:

        days_diff = timedelta(
            seconds=datetime_difference(
                str(db[search_query]["Date"].max()),
                f"{datetime.now():%Y-%m-%d %H:%M:%S}",
            )
        ).days
        print("Days Diff", days_diff)
    except Exception as e:
        print(e)
        days_diff = 1

    if days_diff < 1:
        analysis = RedditAnalysis()
        evaluated_sentiment_list = analysis.pack_comments_to_posts(
            df_posts=None, df_comments=None, name="ui_cache", load_last=True
        )
        packed_sentiment_list = analysis.pack_to_tickers(
            evaluated_sentiment_list, stock_col="Crypto"
        )

        return {
            "sentiment": str(
                round(
                    analysis.average_daily_sentiment(
                        ticker_dict=packed_sentiment_list,
                        ticker=search_query,
                        show_graph=False,
                        limit=1,
                    ).iloc()[0]["Average Sentiment"]
                    * 100,
                    2,
                )
            )
            + "%"
        }
    else:
        # Initialization
        scraper = RedditScraper()
        analysis = RedditAnalysis()
        cleaner = RedditCleaner()

        DAYS = 1
        # subreddits = "wallstreetbets,stocks,pennystocks" # For Stock
        subreddits = "Crypto_General,CryptoCurrency"  # For Crypto

        # Scrape
        posts = scraper.get_reddit_posts(
            subreddit=subreddits, days=DAYS, name="_UI_cache", save=True
        )
        comments = scraper.get_reddit_comments(df=posts, save=True)
        ticker = scraper.get_crypto_tickers(save=True)
        if search_query not in ticker["ticker"].values:
            return {"sentiment": "Ticker not found"}

        # Data Cleaning
        posts = cleaner.concept_parse(
            posts, "Title", "Concepts", "posts", save=True, THREADS=50
        )
        comments = cleaner.concept_parse(
            comments, "body", "Concepts", "comments", save=True, THREADS=50
        )
        posts = cleaner.label_tickers(
            df=posts,
            tickers=ticker,
            targeted_col_name="Title",
            new_col_name="Crypto",
            dfname="posts",
            save=True,
        )
        comments = comments[
            comments["post_id"].isin(posts["ID"])
        ]  # Filter out comments from posts that are not included (not labelled)

        # Sentiment Analysis
        posts_sentiment_list = cleaner.sentiment_analysis(
            posts, "Concepts", "posts", save=True
        )
        comments_sentiment_list = cleaner.sentiment_analysis(
            comments, "Concepts", "comments", save=True
        )

        # Post Evaluation
        evaluated_sentiment_list = analysis.pack_comments_to_posts(
            df_posts=posts_sentiment_list,
            df_comments=comments_sentiment_list,
            name="ui_cache",
            save=True,
        )

        packed_sentiment_list = analysis.pack_to_tickers(
            evaluated_sentiment_list, stock_col="Crypto"
        )
        if search_query not in packed_sentiment_list:
            return {"sentiment": "Ticker not found"}

        print("Time Taken: ", time.time() - start_time, "seconds")
        return {
            "sentiment": str(
                round(
                    analysis.average_daily_sentiment(
                        ticker_dict=packed_sentiment_list,
                        ticker=search_query,
                        show_graph=False,
                        limit=1,
                    ).iloc()[0]["Average Sentiment"]
                    * 100,
                    2,
                )
            )
            + "%"
        }