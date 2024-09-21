import pandas as pd

class PatternIdentifier:
    @staticmethod
    def add_candle_identifiers(stock_data, base_candle_pct, exciting_candle_pct):
        base_candle_threshold = base_candle_pct / 100.0
        exciting_candle_threshold = exciting_candle_pct / 100.0

        stock_data['Body'] = abs(stock_data['Close'] - stock_data['Open'])
        stock_data['UpperWick'] = stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)
        stock_data['LowerWick'] = stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']

        stock_data['BaseCandle'] = (
            (stock_data['UpperWick'] > base_candle_threshold * stock_data['Body']) | 
            (stock_data['LowerWick'] > base_candle_threshold * stock_data['Body'])
        )

        stock_data['GapUp'] = (
            stock_data['Open'] >= stock_data['Close'].shift(1) * 1.03
        )

        stock_data['ExcitingCandle'] = (
            ((stock_data['UpperWick'] < exciting_candle_threshold * stock_data['Body']) & 
            (stock_data['LowerWick'] < exciting_candle_threshold * stock_data['Body'])) | 
            stock_data['GapUp']
        )
        
        return stock_data