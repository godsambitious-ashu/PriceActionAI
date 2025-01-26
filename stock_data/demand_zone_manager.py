import itertools
from stock_data.demand_zone_identifier import DemandZoneIdentifier
from stock_data.supply_zone_identifier import SupplyZoneIdentifier
from stock_data.demand_zone_utils import DemandZoneUtils
from stock_data.candlestick_utils import CandleStickUtils
from stock_data.plotter import Plotter
from stock_data.data_fetcher import DataFetcher
from stock_data.stocks_config import special_stocks_map
import logging
import plotly.io as pio

class DemandZoneManager:
    def __init__(self, stock_code, fig=None):
        """
        Initializes the DemandZoneManager with the stock code and (optionally) a Plotly figure.

        :param stock_code: The stock symbol/code.
        :param fig: The Plotly figure object to annotate with demand and supply zones.
        """
        self.stock_code = stock_code
        self.fig = fig
        self.colors = itertools.cycle(['green'])
        self.supply_colors = itertools.cycle(['red'])  # Colors for supply zones
        self.monthly_zones_all = []    # For "all demand zones" on monthly
        self.monthly_zones_fresh = []  # For "fresh demand zones" on monthly
        self.monthly_supply_zones_all = []    # For "all supply zones" on monthly
        self.monthly_supply_zones_fresh = []  # For "fresh supply zones" on monthly

    def merge_monthly_zones_into_daily(self, monthly_zones, daily_zones):
        """
        Merges monthly demand or supply zones into daily demand or supply zones.

        Args:
            monthly_zones (list): List of monthly zone dictionaries.
            daily_zones (list): List of daily zone dictionaries.

        Returns:
            list: Merged list of daily and monthly zones.
        """
        if not isinstance(monthly_zones, list) or not isinstance(daily_zones, list):
            return daily_zones

        merged_zones = daily_zones.copy()  # To avoid modifying the original list
        merged_zones.extend(monthly_zones)
        return merged_zones

    def include_higher_tf_zones_in_lower_tf_zones(self, interval, zones, zone_type='all', zone_category='demand'):
        """
        Includes higher timeframe zones (demand or supply) into lower timeframe zones.

        Args:
            interval (str): The current interval being processed ('1mo', '1wk', '1d').
            zones (list): List of zone dictionaries for the current interval.
            zone_type (str): Type of zones being processed ('all' or 'fresh').
            zone_category (str): Category of zones ('demand' or 'supply').

        Returns:
            list: Updated list of zones after merging if applicable.
        """
        if zone_category == 'demand':
            if interval == '1mo':
                if zone_type == 'all':
                    self.monthly_zones_all = zones
                elif zone_type == 'fresh':
                    self.monthly_zones_fresh = zones

            elif interval == '1d':
                if zone_type == 'all' and self.monthly_zones_all:
                    zones = self.merge_monthly_zones_into_daily(self.monthly_zones_all, zones)
                elif zone_type == 'fresh' and self.monthly_zones_fresh:
                    zones = self.merge_monthly_zones_into_daily(self.monthly_zones_fresh, zones)
        
        elif zone_category == 'supply':
            if interval == '1mo':
                if zone_type == 'all':
                    self.monthly_supply_zones_all = zones
                elif zone_type == 'fresh':
                    self.monthly_supply_zones_fresh = zones

            elif interval == '1d':
                if zone_type == 'all' and self.monthly_supply_zones_all:
                    zones = self.merge_monthly_zones_into_daily(self.monthly_supply_zones_all, zones)
                elif zone_type == 'fresh' and self.monthly_supply_zones_fresh:
                    zones = self.merge_monthly_zones_into_daily(self.monthly_supply_zones_fresh, zones)

        return zones

    def identify_demand_zones(self, stock_data, interval, fresh=False):
        """
        Identifies demand zones from the stock data.

        :param stock_data: DataFrame containing stock OHLC data.
        :param interval: The interval for demand zone identification.
        :param fresh: Boolean indicating whether to filter for fresh demand zones.
        :return: List of identified demand zones.
        """
        demand_zones = DemandZoneIdentifier.identify_demand_zones(stock_data, interval)

        if fresh:
            demand_zones = [
                zone for zone in demand_zones
                if DemandZoneUtils.is_fresh_demand_zone(stock_data, zone)
            ]

        return demand_zones

    def identify_supply_zones(self, stock_data, interval, fresh=False):
        """
        Identifies supply zones from the stock data.

        :param stock_data: DataFrame containing stock OHLC data.
        :param interval: The interval for supply zone identification.
        :param fresh: Boolean indicating whether to filter for fresh supply zones.
        :return: List of identified supply zones.
        """
        supply_zones = SupplyZoneIdentifier.identify_supply_zones(stock_data, interval)

        if fresh:
            supply_zones = [
                zone for zone in supply_zones
                if DemandZoneUtils.is_fresh_supply_zone(stock_data, zone)  # Ensure this utility exists
            ]

        return supply_zones

    def mark_demand_zones_on_chart(self, demand_zones):
        """
        Marks the identified demand zones on the current Plotly figure.

        :param demand_zones: List of demand zones to mark.
        :return: Annotated Plotly figure.
        """
        CandleStickUtils.markDemandZoneInfoOnChart(
            self.stock_code,
            self.fig,
            demand_zones,
            self.colors
        )
        return self.fig

    def mark_supply_zones_on_chart(self, supply_zones):
        """
        Marks the identified supply zones on the current Plotly figure.

        :param supply_zones: List of supply zones to mark.
        :return: Annotated Plotly figure.
        """
        CandleStickUtils.markDemandZoneInfoOnChart(
            self.stock_code,
            self.fig,
            supply_zones,
            self.supply_colors
        )
        return self.fig

    def generate_demand_zones_info(self, demand_zones):
        """
        Generates informational text about the identified demand zones.

        :param demand_zones: List of demand zones.
        :return: String containing demand zones information.
        """
        return DemandZoneUtils.generate_demand_zones_info(demand_zones)

    def generate_supply_zones_info(self, supply_zones):
        """
        Generates informational text about the identified supply zones.

        :param supply_zones: List of supply zones.
        :return: String containing supply zones information.
        """
        return DemandZoneUtils.generate_demand_zones_info(supply_zones)  # Ensure this utility exists

    def process_single_interval(self, interval, period):
        """
        Fetches stock data for the given interval & period, creates candlestick charts,
        identifies and merges demand and supply zones, and returns all necessary components.

        :param interval: The interval (e.g., '1mo', '1wk', '1d').
        :param period: The period over which to fetch data (e.g., '6mo', '1y').
        :return: A dictionary containing:
            {
                'chart_all_zones': (str) HTML of chart with all zones,
                'chart_fresh_zones': (str) HTML of chart with fresh zones,
                'all_zones_info': (str) info about all zones,
                'fresh_zones_info': (str) info about fresh zones,
                'all_zones': {'demand': list, 'supply': list},
                'fresh_zones': {'demand': list, 'supply': list},
                'current_price': (float|None) last close if interval == '1d', else None
            }
        """
        stock_data = DataFetcher.fetch_stock_data(self.stock_code, interval=interval, period=period)
        if stock_data.empty:
            return {}

        plotter = Plotter()
        base_fig = plotter.create_candlestick_chart(stock_data, self.stock_code, interval)
        self.fig = base_fig

        demand_zones_all = self.identify_demand_zones(stock_data, interval, fresh=False)
        demand_zones_all = self.include_higher_tf_zones_in_lower_tf_zones(interval, demand_zones_all, 'all', 'demand')

        supply_zones_all = self.identify_supply_zones(stock_data, interval, fresh=False)
        supply_zones_all = self.include_higher_tf_zones_in_lower_tf_zones(interval, supply_zones_all, 'all', 'supply')

        fig_all_zones = self.mark_demand_zones_on_chart(demand_zones_all)
        fig_all_zones = self.mark_supply_zones_on_chart(supply_zones_all)
        chart_all_zones = pio.to_html(fig_all_zones, full_html=False)
        all_zones_info = self.generate_demand_zones_info(demand_zones_all) + "\n" + self.generate_supply_zones_info(supply_zones_all)

        demand_zones_fresh = self.identify_demand_zones(stock_data, interval, fresh=True)
        demand_zones_fresh = self.include_higher_tf_zones_in_lower_tf_zones(interval, demand_zones_fresh, 'fresh', 'demand')

        supply_zones_fresh = self.identify_supply_zones(stock_data, interval, fresh=True)
        supply_zones_fresh = self.include_higher_tf_zones_in_lower_tf_zones(interval, supply_zones_fresh, 'fresh', 'supply')

        fig_fresh_zones = plotter.create_candlestick_chart(stock_data, self.stock_code, interval)
        self.fig = fig_fresh_zones

        fig_fresh_zones = self.mark_demand_zones_on_chart(demand_zones_fresh)
        fig_fresh_zones = self.mark_supply_zones_on_chart(supply_zones_fresh)
        chart_fresh_zones = pio.to_html(fig_fresh_zones, full_html=False)
        fresh_zones_info = self.generate_demand_zones_info(demand_zones_fresh) + "\n" + self.generate_supply_zones_info(supply_zones_fresh)

        current_price = None
        if interval == '1d':
            current_price = stock_data.iloc[-1]['Close']

        return {
            'chart_all_zones': chart_all_zones,
            'chart_fresh_zones': chart_fresh_zones,
            'all_zones_info': all_zones_info,
            'fresh_zones_info': fresh_zones_info,
            'all_zones': {
                'demand': demand_zones_all,
                'supply': supply_zones_all
            },
            'fresh_zones': {
                'demand': demand_zones_fresh,
                'supply': supply_zones_fresh
            },
            'current_price': current_price
        }

    def process_all_intervals(self, intervals, period):
        """
        Runs process_single_interval across all specified intervals in ascending order
        (e.g., ['3mo', '1mo', '1wk', '1d']), returning consolidated charts and zone info.

        :param intervals: List of intervals, e.g. ['3mo', '1mo', '1wk', '1d'].
        :param period: Period to fetch data for, e.g. '1y'.
        :return: A tuple of:
          - charts (dict) with keys = interval, containing 'all_zones' and 'fresh_zones' charts,
          - demand_zones_info (dict) similar structure,
          - supply_zones_info (dict) similar structure,
          - all_demand_zones_fresh (dict) storing fresh demand zones by interval,
          - all_supply_zones_fresh (dict) storing fresh supply zones by interval,
          - monthly_fresh_zones (list) the final stored 'fresh' monthly zones,
          - daily_all_zones (dict) the final stored 'all' daily zones,
          - current_market_price (float|None)
        """
        charts = {}
        demand_zones_info = {}
        supply_zones_info = {}
        all_demand_zones_fresh = {}
        all_supply_zones_fresh = {}
        monthly_all_zones = []
        daily_all_zones = {'demand': [], 'supply': []}
        current_market_price = None
        fresh_demand_zones_1d = []
        wk_demand_zones = []

        for interval in intervals:
            result = self.process_single_interval(interval, period)
            if not result:
                continue

            required_keys = ['chart_all_zones', 'chart_fresh_zones', 'all_zones_info', 'fresh_zones_info', 'fresh_zones']
            for key in required_keys:
                if key not in result:
                    continue

            try:
                charts[interval] = {
                    'all_zones': result['chart_all_zones'],
                    'fresh_zones': result['chart_fresh_zones']
                }
                demand_zones_info[interval] = {
                    'all_zones_info': result['all_zones_info'],
                    'fresh_zones_info': result['fresh_zones_info']
                }
                supply_zones_info[interval] = {
                    'all_zones_info': result['all_zones_info'],
                    'fresh_zones_info': result['fresh_zones_info']
                }
                all_demand_zones_fresh[interval] = result['fresh_zones']['demand']
                all_supply_zones_fresh[interval] = result['fresh_zones']['supply']
            except (AttributeError, KeyError):
                continue

            if interval in ['1mo', '3mo']:
                demand_zones = result['all_zones']['demand']
                supply_zones = result['all_zones']['supply']
    
                if isinstance(demand_zones, list) and isinstance(supply_zones, list):
                    # Combine demand and supply zones
                    aggregated_zones = demand_zones + supply_zones
                    monthly_all_zones.extend(aggregated_zones)  # Append to the list
                    logging.debug(f"Aggregated zones for {interval}: {aggregated_zones}")
                else:
                    logging.warning(f"Invalid zone format for {interval}")

            if interval == '1d':
                if isinstance(result['all_zones'], dict):
                    daily_all_zones = result['all_zones']
                    current_market_price = result.get('current_price')
                fresh_demand_zones_1d = result['fresh_zones']['demand']
            if interval == '1wk':
                wk_demand_zones = result['all_zones']['demand']    

        return (
            charts,
            demand_zones_info,
            supply_zones_info,
            all_demand_zones_fresh,
            all_supply_zones_fresh,
            monthly_all_zones,
            daily_all_zones,
            current_market_price,
            fresh_demand_zones_1d, 
            wk_demand_zones
        )
    

    def get_stock_codes_to_process(self, original_stock_code):
        """
        Checks if the given stock_code belongs to a specific set of stocks.
        If it does, returns the mapped stock codes.
        Otherwise, returns an empty list.

        :param original_stock_code: The original stock code to check.
        :return: List of stock codes to process.
        """
        original_upper = original_stock_code.upper()
        if original_upper in special_stocks_map:
            result = special_stocks_map[original_upper]
        else:
            result = []
    
        return result