import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import itertools
import logging
from stock_data.demand_zone_identifier import DemandZoneIdentifier
from stock_data.pattern_identifier import CandleIdentifier
from stock_data.candlestick_utils import CandleStickUtils
from stock_data.demand_zone_utils import DemandZoneUtils

class Plotter:
    @staticmethod
    def create_candlestick_chart(stock_data, stock_code, interval, fresh=False):
        logging.debug("Starting to create candlestick chart")
        base_candle_threshold = 0.5
        exciting_candle_threshold = 0.5

        stock_data['Body'] = abs(stock_data['Close'] - stock_data['Open'])
        stock_data['UpperWick'] = stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)
        stock_data['LowerWick'] = stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']

        stock_data = CandleIdentifier.add_candle_identifiers(stock_data, base_candle_threshold * 100, exciting_candle_threshold * 100)

        fig = CandleStickUtils.highlightCandlesAsExcitingOrBase(stock_data)

        # Identify and mark demand zones
        logging.debug("Identifying demand zones")
        demand_zones = DemandZoneIdentifier.identify_demand_zones(stock_data, interval)
        logging.debug(f"Demand zones identified: {len(demand_zones)} zones found")
        
        if fresh:
            demand_zones = [zone for zone in demand_zones if DemandZoneUtils.is_fresh_demand_zone(stock_data, zone)]
            logging.debug(f"Fresh demand zones identified: {len(demand_zones)} zones found")

        colors = itertools.cycle(['purple', 'cyan', 'magenta', 'yellow', 'green', 'red'])

        CandleStickUtils.markDemandZoneInfoOnChart(stock_code, fig, demand_zones, colors)
        
        chart_html = pio.to_html(fig, full_html=False)
        demand_zones_info = DemandZoneUtils.generate_demand_zones_info(demand_zones)
        
        return chart_html, demand_zones_info


