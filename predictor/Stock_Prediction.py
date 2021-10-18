import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import datetime as dt
from pandas.core.algorithms import mode
import pandas_datareader as web
from pandas_datareader.data import DataReader
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Dropout, LSTM
import os
import shelve

db = shelve.open("../logs/stock_prices")
db.close()


class StockForecast:
    def __init__(self, window: int = 60):
        self.window = 60
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def get_ticker_prices(self, ticker, mode):
        path = f"../datasets/stock_prices/{ticker}.csv"

        if mode == "load":
            print("Loading ticker prices for stock prediction...")
            if os.path.exists(path=path):
                return pd.read_csv(path)

        print("Rescraping for stock prices")

        start = dt.datetime(2012, 1, 1)
        end = dt.datetime.today()

        data = web.DataReader(ticker, "yahoo", start, end)
        print(data.head())
        data.to_csv(path)
        return data

    def data_preprocessing(self, data):
        scaler = self.scaler
        scaled_data = scaler.fit_transform(data["Close"].values.reshape(-1, 1))

        prediction_days = self.window

        x_train = []
        y_train = []

        for x in range(prediction_days, len(scaled_data)):
            x_train.append(scaled_data[x - prediction_days : x, 0])
            y_train.append(scaled_data[x, 0])

        x_train, y_train = np.array(x_train), np.array(y_train)
        x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
        return x_train, y_train

    def build_model(self, x_train, y_train, ticker, mode):
        path = f"../models/{ticker}"
        if mode == "load":
            if os.path.exists(path=f"../models/{ticker}"):
                return load_model(path)

        print("Building model")

        model = Sequential()
        model.add(
            LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], 1))
        )
        model.add(Dropout(0.2))
        model.add(LSTM(units=50, return_sequences=True))
        model.add(Dropout(0.2))
        model.add(LSTM(units=50))
        model.add(Dropout(0.2))
        model.add(Dense(units=1))

        model.compile(optimizer="adam", loss="mean_squared_error")
        model.fit(x_train, y_train, epochs=25, batch_size=32)
        model.save(filepath=path)
        return model

    def predict_prices(self, days, model, ticker, data):
        prediction_days = self.window
        scaler = self.scaler

        test_end = dt.datetime.today()
        test_start = test_end - dt.timedelta(45)

        test_data = web.DataReader(ticker, "yahoo", test_start, test_end)
        actual_prices = test_data["Close"].values

        total_dataset = pd.concat((data["Close"], test_data["Close"]), axis=0)

        model_inputs = total_dataset[
            len(total_dataset) - len(test_data) - prediction_days :
        ].values
        model_inputs = model_inputs.reshape(-1, 1)
        model_inputs = scaler.transform(model_inputs)

        # Making Prediction
        x_test = []
        for x in range(prediction_days, len(model_inputs)):
            x_test.append(model_inputs[x - prediction_days : x, 0])

        x_test = np.array(x_test)
        x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[-1], 1))

        predicted_prices = model.predict(x_test)
        predicted_prices = scaler.inverse_transform(predicted_prices)

        # Predicting future stock prices
        prediction_dataset = total_dataset[-prediction_days - 1 :].values
        predicted_values = []

        for i in range(1, 15):
            model_inputs = prediction_dataset.reshape(-1, 1)
            model_inputs = scaler.transform(model_inputs)

            real_data = [model_inputs[-prediction_days : len(model_inputs) + 1, 0]]
            real_data = np.array(real_data)
            real_data = np.reshape(
                real_data, (real_data.shape[0], real_data.shape[1], 1)
            )
            prediction = model.predict(real_data)
            prediction = scaler.inverse_transform(prediction)
            predicted_values.append(float(prediction))
            prediction_dataset = np.append(prediction_dataset, float(prediction))

        predicted_graph = [float(i) for i in predicted_prices] + predicted_values

        print(len(predicted_graph))
        days = [x for x in range(days, 0, -1)] + ["today"] + [i for i in range(1, 16)]

        return actual_prices, predicted_graph, days


if __name__ == "__main__":
    ticker = "ETH-USD"

    test = StockForecast(window=60)
    ticker_prices = test.get_ticker_prices(ticker=ticker, mode="load")
    x_train, y_train = test.data_preprocessing(ticker_prices)
    model = test.build_model(x_train, y_train, ticker=ticker, mode="load")
    actual_prices, predicted_prices, days = test.predict_prices(
        days=45, model=model, ticker=ticker, data=ticker_prices
    )
