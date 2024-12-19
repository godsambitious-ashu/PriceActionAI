import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import itertools
import logging
from stock_data.demand_zone_identifier import DemandZoneIdentifier
from stock_data.candlestick_utils import CandleStickUtils
from stock_data.demand_zone_utils import DemandZoneUtils

class Plotter:
    @staticmethod
    def create_candlestick_chart(stock_data, stock_code, interval):
        logging.debug("Starting to create candlestick chart")
        base_candle_threshold = 0.5
        exciting_candle_threshold = 0.5

        # Calculate candle components
        stock_data['Body'] = abs(stock_data['Close'] - stock_data['Open'])
        stock_data['UpperWick'] = stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)
        stock_data['LowerWick'] = stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']

        # Add candle identifiers
        stock_data = CandleStickUtils.add_candle_identifiers(
            stock_data,
            base_candle_threshold ,
            exciting_candle_threshold
        )
        logging.debug(f"Dataframe for interval1mo {stock_data}")

        # Create initial candlestick chart with highlighted candles
        fig = CandleStickUtils.highlightCandlesAsExcitingOrBase(stock_data)

        logging.debug("Candlestick chart created successfully")
        return fig


