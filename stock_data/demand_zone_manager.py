import itertools
import logging
from stock_data.demand_zone_identifier import DemandZoneIdentifier
from stock_data.demand_zone_utils import DemandZoneUtils
from stock_data.candlestick_utils import CandleStickUtils
from stock_data.plotter import Plotter
from stock_data.data_fetcher import DataFetcher
import plotly.io as pio

class DemandZoneManager:
    def __init__(self, stock_code, fig=None):
        """
        Initializes the DemandZoneManager with the stock code and (optionally) a Plotly figure.

        :param stock_code: The stock symbol/code.
        :param fig: The Plotly figure object to annotate with demand zones.
        """
        self.stock_code = stock_code
        self.fig = fig
        self.colors = itertools.cycle(['purple', 'cyan', 'magenta', 'yellow', 'green', 'red'])
        self.monthly_zones_all = []    # For "all zones" on monthly
        self.monthly_zones_fresh = []  # For "fresh zones" on monthly

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

        merged_zones = daily_zones.copy()  # To avoid modifying the original list
        merged_zones.extend(monthly_zones)
        logging.debug(
            f"Merged {len(monthly_zones)} monthly zones into daily zones. "
            f"Total zones: {len(merged_zones)}"
        )
        return merged_zones

    def include_higher_tf_zones_in_lower_tf_zones(self, interval, demand_zones, zone_type='all'):
        """
        Includes higher timeframe demand zones into lower timeframe demand zones.

        Args:
            interval (str): The current interval being processed ('1mo', '1wk', '1d').
            demand_zones (list): List of demand zones for the current interval.
            zone_type (str): Type of zones being processed ('all' or 'fresh').

        Returns:
            list: Updated list of demand zones after merging if applicable.
        """
        logging.debug(
            f"Called include_higher_tf_zones_in_lower_tf_zones with interval={interval}, zone_type={zone_type}"
        )

        # Store or merge monthly zones if needed
        if interval == '1mo':
            # Just store them for later use in daily merges
            if zone_type == 'all':
                self.monthly_zones_all = demand_zones
                logging.debug(f"Stored monthly_zones_all: {self.monthly_zones_all}")
            elif zone_type == 'fresh':
                self.monthly_zones_fresh = demand_zones
                logging.debug(f"Stored monthly_zones_fresh: {self.monthly_zones_fresh}")

        elif interval == '1d':
            # Merge monthly zones into daily zones if monthly exist
            if zone_type == 'all' and self.monthly_zones_all:
                logging.debug("Merging monthly_zones_all into daily_zones_all")
                demand_zones = self.merge_monthly_zones_into_daily(self.monthly_zones_all, demand_zones)
            elif zone_type == 'fresh' and self.monthly_zones_fresh:
                logging.debug("Merging monthly_zones_fresh into daily_zones_fresh")
                demand_zones = self.merge_monthly_zones_into_daily(self.monthly_zones_fresh, demand_zones)
            else:
                logging.debug(f"No {zone_type}_zones to merge into daily_zones")

        return demand_zones

    def identify_demand_zones(self, stock_data, interval, fresh=False):
        """
        Identifies demand zones from the stock data.

        :param stock_data: DataFrame containing stock OHLC data.
        :param interval: The interval for demand zone identification.
        :param fresh: Boolean indicating whether to filter for fresh demand zones.
        :return: List of identified demand zones.
        """
        demand_zones = DemandZoneIdentifier.identify_demand_zones(stock_data, interval)
        logging.debug(f"Total demand zones identified for interval={interval}: {len(demand_zones)}")

        if fresh:
            demand_zones = [
                zone for zone in demand_zones
                if DemandZoneUtils.is_fresh_demand_zone(stock_data, zone)
            ]
            logging.debug(f"Fresh demand zones retained: {len(demand_zones)}")

        return demand_zones

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

    def generate_demand_zones_info(self, demand_zones):
        """
        Generates informational text about the identified demand zones.

        :param demand_zones: List of demand zones.
        :return: String containing demand zones information.
        """
        return DemandZoneUtils.generate_demand_zones_info(demand_zones)

    def process_single_interval(
        self,
        interval,
        period
    ):
        """
        Fetches stock data for the given interval & period, creates candlestick charts,
        identifies and merges demand zones, and returns all necessary components.

        :param interval: The interval (e.g., '1mo', '1d').
        :param period: The period over which to fetch data (e.g., '6mo', '1y').
        :return: A dictionary containing:
            {
                'chart_all_zones': (str) HTML of chart with all zones,
                'chart_fresh_zones': (str) HTML of chart with fresh zones,
                'all_zones_info': (str) info about all zones,
                'fresh_zones_info': (str) info about fresh zones,
                'all_zones': (list) the identified all-zones,
                'fresh_zones': (list) the identified fresh-zones,
                'current_price': (float|None) last close if interval == '1d', else None
            }
        """
        # 1. Fetch data
        stock_data = DataFetcher.fetch_stock_data(self.stock_code, interval=interval, period=period)
        if stock_data.empty:
            logging.warning(f"No data for {self.stock_code} at interval={interval}, period={period}.")
            return {}

        # 2. Create base candlestick chart
        plotter = Plotter()
        base_fig = plotter.create_candlestick_chart(stock_data, self.stock_code, interval)
        self.fig = base_fig  # Update our figure reference

        # 3. Identify 'all' zones and merge higher timeframe zones if needed
        demand_zones_all = self.identify_demand_zones(stock_data, interval, fresh=False)
        demand_zones_all = self.include_higher_tf_zones_in_lower_tf_zones(interval, demand_zones_all, 'all')

        # 4. Mark 'all' zones
        fig_all_zones = self.mark_demand_zones_on_chart(demand_zones_all)
        chart_all_zones = pio.to_html(fig_all_zones, full_html=False)
        all_zones_info = self.generate_demand_zones_info(demand_zones_all)

        # 5. Identify fresh zones and merge higher timeframe zones if needed
        fresh_fig = plotter.create_candlestick_chart(stock_data, self.stock_code, interval)
        dz_manager_fresh = DemandZoneManager(self.stock_code, fresh_fig)
        demand_zones_fresh = dz_manager_fresh.identify_demand_zones(stock_data, interval, fresh=True)
        demand_zones_fresh = self.include_higher_tf_zones_in_lower_tf_zones(interval, demand_zones_fresh, 'fresh')

        # 6. Mark fresh zones
        fig_fresh_zones = dz_manager_fresh.mark_demand_zones_on_chart(demand_zones_fresh)
        chart_fresh_zones = pio.to_html(fig_fresh_zones, full_html=False)
        fresh_zones_info = dz_manager_fresh.generate_demand_zones_info(demand_zones_fresh)

        # 7. Capture current market price if daily
        current_price = None
        if interval == '1d':
            current_price = stock_data.iloc[-1]['Close']

        return {
            'chart_all_zones': chart_all_zones,
            'chart_fresh_zones': chart_fresh_zones,
            'all_zones_info': all_zones_info,
            'fresh_zones_info': fresh_zones_info,
            'all_zones': demand_zones_all,
            'fresh_zones': demand_zones_fresh,
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
          - all_demand_zones_fresh (dict) storing fresh zones by interval,
          - monthly_fresh_zones (list) the final stored 'fresh' monthly zones,
          - daily_all_zones (list) the final stored 'all' daily zones,
          - current_market_price (float|None)
        """
        charts = {}
        demand_zones_info = {}
        all_demand_zones_fresh = {}
        monthly_fresh_zones = []
        daily_all_zones = []
        current_market_price = None

        for interval in intervals:
            logging.debug(f"Processing {interval} for stock {self.stock_code}...")
            result = self.process_single_interval(interval, period)
            if not result:
                # If no data or something unexpected, skip
                continue

            # Populate the output dictionaries
            charts[interval] = {
                'all_zones': result['chart_all_zones'],
                'fresh_zones': result['chart_fresh_zones']
            }
            demand_zones_info[interval] = {
                'all_zones_info': result['all_zones_info'],
                'fresh_zones_info': result['fresh_zones_info']
            }
            all_demand_zones_fresh[interval] = result['fresh_zones']

            # Capture monthly "all" and "fresh" zones, daily "all" zones, etc.
            if interval == '1mo':
                # We store the monthly *all* zones in self.monthly_zones_all,
                # but if you also want them outside:
                monthly_fresh_zones = result['all_zones']
            if interval == '1d':
                daily_all_zones = result['all_zones']
                current_market_price = result['current_price']

        return (
            charts,
            demand_zones_info,
            all_demand_zones_fresh,
            monthly_fresh_zones,
            daily_all_zones,
            current_market_price
        )