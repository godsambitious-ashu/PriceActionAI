# demand_zone_manager.py

import itertools
import logging
from stock_data.demand_zone_identifier import DemandZoneIdentifier
from stock_data.demand_zone_utils import DemandZoneUtils
from stock_data.candlestick_utils import CandleStickUtils

class DemandZoneManager:
    def __init__(self, stock_code, fig):
        """
        Initializes the DemandZoneManager with the stock code and the Plotly figure.
        
        :param stock_code: The stock symbol/code.
        :param fig: The Plotly figure object to annotate with demand zones.
        """
        self.stock_code = stock_code
        self.fig = fig
        self.colors = itertools.cycle(['purple', 'cyan', 'magenta', 'yellow', 'green', 'red'])
        self.monthly_zones = []  # Initialize monthly_zones as an empty list

    def merge_monthly_zones_into_daily(self, monthly_zones, daily_zones):
        """
        Merges monthly demand zones into daily demand zones.

        Args:
            monthly_zones (list): List of monthly demand zone dictionaries.
            daily_zones (list): List of daily demand zone dictionaries.

        Returns:
            list: Merged list of daily and monthly demand zones.
        """
        if not isinstance(monthly_zones, list) or not isinstance(daily_zones, list):
            logging.error("monthly_zones and daily_zones must be lists")
            return daily_zones

        # Optional: Implement logic to prevent duplicates or conflicts
        merged_zones = daily_zones.copy()  # To avoid modifying the original list
        merged_zones.extend(monthly_zones)
        logging.debug(f"Merged {len(monthly_zones)} monthly zones into daily zones. Total zones: {len(merged_zones)}")
        return merged_zones
    
    def includeHigherTfDzInLDailyDz(self, interval, demand_zones_all):
        if interval == '1mo':
            self.monthly_zones = demand_zones_all
        elif interval == '1d':
            if self.monthly_zones:
                demand_zones_all = self.merge_monthly_zones_into_daily(self.monthly_zones, demand_zones_all)
        return demand_zones_all

    def identify_demand_zones(self, stock_data, interval, fresh=False):
        """
        Identifies demand zones from the stock data.
        
        :param stock_data: DataFrame containing stock OHLC data.
        :param interval: The interval for demand zone identification.
        :param fresh: Boolean indicating whether to filter for fresh demand zones.
        :return: List of identified demand zones.
        """
        logging.debug("Identifying demand zones")
        demand_zones = DemandZoneIdentifier.identify_demand_zones(stock_data, interval)
        logging.debug(f"Demand zones identified: {len(demand_zones)} zones found")

        if fresh:
            demand_zones = [
                zone for zone in demand_zones
                if DemandZoneUtils.is_fresh_demand_zone(stock_data, zone)
            ]
            logging.debug(f"Fresh demand zones identified: {len(demand_zones)} zones found")

        return demand_zones

    def mark_demand_zones_on_chart(self, demand_zones):
        """
        Marks the identified demand zones on the Plotly figure.
        
        :param demand_zones: List of demand zones to mark.
        :return: Annotated Plotly figure.
        """
        logging.debug("Marking demand zones on the chart")
        CandleStickUtils.markDemandZoneInfoOnChart(
            self.stock_code,
            self.fig,
            demand_zones,
            self.colors
        )
        logging.debug("Demand zones marked successfully")
        return self.fig

    def generate_demand_zones_info(self, demand_zones):
        """
        Generates informational text about the identified demand zones.
        
        :param demand_zones: List of demand zones.
        :return: String containing demand zones information.
        """
        logging.debug("Generating demand zones information")
        return DemandZoneUtils.generate_demand_zones_info(demand_zones)