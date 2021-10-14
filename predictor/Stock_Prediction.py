# Imports
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import datetime as dt
from pandas.core.algorithms import mode
import pandas_datareader as web

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Dropout, LSTM

scaler = MinMaxScaler(feature_range=(0, 1))


class StockForecast:
    def __init__(self, window: int = 60):
        self.window = window

    def get_ticker_prices(self, ticker: str = "BTC-USD", mode="save"):
        if mode.lower() == "load":
            data = pd.read_csv(f"datasets/{ticker}")
        else:
            start = dt.datetime(2012, 1, 1)
            end = dt.datetime.today()
            data = web.DataReader(ticker, "yahoo", start, end)
            data.to_csv(f"datasets/{ticker}")
        self.data = data

        # Data Preparation
        return scaler.fit_transform(data["Close"].values.reshape(-1, 1))

    def data_preprocessing(self, scaled_data) -> tuple:
        prediction_days = self.window
        x_train = []
        y_train = []

        for x in range(prediction_days, len(scaled_data)):
            x_train.append(scaled_data[x - prediction_days : x, 0])
            y_train.append(scaled_data[x, 0])

        x_train, y_train = np.array(x_train), np.array(y_train)
        x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
        return x_train, x_train

    def build_model(self, x_train, y_train, ticker: str, mode):
        if mode.lower() == "load":
            return load_model(filepath=f"models/{ticker}")

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
        model.save(filepath=f"models/{ticker}")
        return model

    def prediction(
        self,
        previous_days,
        model,
        ticker: str = "BTC-USD",
    ):
        # Testing the accuracy using previous data
        data = self.data
        prediction_days = self.window

        test_end = dt.datetime.today()
        test_start = test_end - dt.timedelta(previous_days)

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

        prediction_dataset = total_dataset[-prediction_days - 1 :].values
        print(len(prediction_dataset))
        predicted_values = []

        for i in range(1, 31):
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
        return actual_prices, predicted_graph


if __name__ == "__main__":
    test = StockForecast(window=60)
    ticker_prices = test.get_ticker_prices(ticker="BTC-USD", mode="load")
    x_train, y_train = test.data_preprocessing(ticker_prices)
    model = test.build_model(x_train, y_train, ticker="BTC-USD", mode="load")
    actual_prices, predicted_prices = test.prediction(
        previous_days=45, model=model, ticker="BTC-USD"
    )
    print(actual_prices, predicted_prices)
