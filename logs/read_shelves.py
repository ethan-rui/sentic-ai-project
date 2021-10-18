import shelve

with shelve.open("sentiment_values.db", "c") as db:
    print(dict(db))
