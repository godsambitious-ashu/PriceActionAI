import pandas as pd

class PatternIdentifier:
    @staticmethod
    def add_candle_identifiers(stock_data, base_candle_pct, exciting_candle_pct):
        base_candle_threshold = base_candle_pct / 100.0
        exciting_candle_threshold = exciting_candle_pct / 100.0
        gap_up_threshold = 0.01  # 3%

        stock_data['BaseCandle'] = (
            (stock_data['UpperWick'] > base_candle_threshold * stock_data['Body']) | 
            (stock_data['LowerWick'] > base_candle_threshold * stock_data['Body'])
        )

        # Existing condition for exciting candle
        stock_data['ExcitingCandle'] = (
            (stock_data['UpperWick'] < exciting_candle_threshold * stock_data['Body']) & 
            (stock_data['LowerWick'] < exciting_candle_threshold * stock_data['Body'])
        )

        # Additional condition for gap-up exciting candle
        stock_data['GapUp'] = stock_data['Open'] > stock_data['Close'].shift(1) * (1 + gap_up_threshold)

        # Combine both conditions for exciting candle
        stock_data['ExcitingCandle'] = stock_data['ExcitingCandle'] | stock_data['GapUp']
        
        return stock_data
    
    @staticmethod
    def identify_patterns(stock_data):
        patterns = []
        used_indices = set()

        # Iterate over the stock data to identify patterns
        for i in range(4, len(stock_data)):
            current_candle = stock_data.iloc[i]
            previous_candles = stock_data.iloc[i-4:i]

            if current_candle['ExcitingCandle'] and current_candle['Close'] > current_candle['Open']:
                base_candles = previous_candles[previous_candles['BaseCandle']]
                base_indices = set(base_candles.index)

                # Ensure base candles are not reused
                if len(base_candles) <= 3 and not used_indices.intersection(base_indices):
                    pattern = {
                        'exciting_index': current_candle.name,
                        'base_indices': base_candles.index
                    }
                    patterns.append(pattern)
                    used_indices.update(base_indices)

        return patterns
