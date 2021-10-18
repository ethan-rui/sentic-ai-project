import shelve

with shelve.open("stock_prices", "c") as db:
    print(dict(db))
