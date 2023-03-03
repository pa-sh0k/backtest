import pandas as pd
import ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover, resample_apply

from binance import Client
from config import *

client = Client()


def get_data(symbol, start, finish, tf):
    frame = pd.DataFrame(client.get_historical_klines(symbol, tf, start, finish))
    frame = frame[[0, 1, 2, 3, 4]]
    frame.columns = ['Date', 'Open', 'High', 'Low', 'Close']
    frame.Date = pd.to_datetime(frame.Date, unit='ms')
    frame.set_index('Date', inplace=True)
    frame = frame.astype(float)
    return frame


data = get_data(ticker, date_start, date_finish, tf)


class DataTrader(Strategy):
    def init(self):
        close = self.data.Close
        high = self.data.High
        low = self.data.Low

        four_hours = close.s.resample(ema_tf, label='right').agg('last')

        self.atr = self.I(ta.volatility.average_true_range, pd.Series(high), pd.Series(low), pd.Series(close), window=atr_window)

        def ema_other_tf(series, window):
            return ta.trend.ema_indicator(series, window).reindex(close.s.index).ffill()

        self.fastema_other_tf_long = self.I(ema_other_tf, four_hours, window=fastema_long)
        self.slowema_other_tf_long = self.I(ema_other_tf, four_hours, window=slowema_long)

        self.rsi = self.I(ta.momentum.rsi, pd.Series(close), window=rsiLength)

        # self.macd = self.I(ta.trend.macd, pd.Series(close), window_fast=fast_length, window_slow=slow_length)
        # self.macd_signal = self.I(ta.trend.macd_signal, pd.Series(close), window_fast=fast_length, window_slow=slow_length, window_sign=signal_length)

        ma_func = ta.trend.sma_indicator if sma_source == "SMA" else ta.trend.ema_indicator
        fast_ma = self.I(ma_func, pd.Series(close), window=fast_length)
        slow_ma = self.I(ma_func, pd.Series(close), window=slow_length)

        macd_func = lambda x: ma_func(close=x, window=fast_length) - ma_func(close=x, window=slow_length)
        self.macd = self.I(macd_func, pd.Series(close))
        macd = macd_func(pd.Series(close))
        self.macd_signal = self.I(ma_func, macd, window=signal_length)

    def next(self):
        price = self.data.Close

        if price > self.fastema_other_tf_long > self.slowema_other_tf_long and crossover(self.macd_signal, self.macd) and len(self.trades) <= 0:
            sl = price - self.atr * atrStopMultiplierLong
            tp = price + self.atr * atrTakeMultiplierLong
            self.buy(sl=sl, tp=tp, size=order_size)


bt = Backtest(data, DataTrader, cash=initial_capital, commission=commission)

output = bt.run()

print(output)

bt.plot()
