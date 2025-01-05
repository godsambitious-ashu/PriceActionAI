
import pandas as pd


class DemandZoneUtils:
    @staticmethod
    def is_fresh_demand_zone(stock_data, zone):
        """
        Check if the price has never entered the demand zone after it was created.

        :param stock_data: DataFrame containing stock OHLC data (must include 'Low' and 'High' columns).
        :param zone: Dict containing zone info with 'proximal', 'distal', and 'dates' (the last date is the formation date).
        :return: True if the zone is fresh (not retested), False otherwise.
        """
        proximal = zone['proximal']
        distal = zone['distal']
        zone_end_date = zone['dates'][-1]
        end_date = stock_data.index[-1]

        # If zone_end_date is the last known date, there's no future data to test → zone is fresh
        if zone_end_date >= end_date:
            return True

        # Get the index position of zone_end_date in stock_data
        zone_end_pos = stock_data.index.get_loc(zone_end_date)
        # If this is the last row, there's no future candle to test
        if zone_end_pos == len(stock_data.index) - 1:
            return True

        # Slice the DataFrame to only dates *after* the zone's formation date
        future_dates = stock_data.index[zone_end_pos + 1:]

        # If any future candle overlaps the zone [distal, proximal], it's not fresh
        for date in future_dates:
            candle_low = stock_data.loc[date, 'Low']
            candle_high = stock_data.loc[date, 'High']
            # Overlap condition for a demand zone:
            # The candle's LOW dips at/below the zone's top (proximal)
            # AND the candle's HIGH reaches/extends above the zone's bottom (distal)
            if candle_low <= proximal and candle_high >= distal:
                return False

        return True
    
    @staticmethod
    def is_fresh_supply_zone(stock_data, zone):
        """
        Check if the price has never entered the supply zone after it was created.

        :param stock_data: DataFrame containing stock OHLC data (must include 'Low' and 'High' columns).
        :param zone: Dict containing zone info with 'proximal', 'distal', and 'dates' (the last date is the formation date).
        :return: True if the supply zone is fresh (not retested), False otherwise.
        """
        proximal = zone['proximal']
        distal = zone['distal']
        zone_end_date = zone['dates'][-1]
        end_date = stock_data.index[-1]

        # If zone_end_date is the last known date, there's no future data to test → zone is fresh
        if zone_end_date >= end_date:
            return True

        # Get the index position of zone_end_date in stock_data
        zone_end_pos = stock_data.index.get_loc(zone_end_date)
        # If this is the last row, there's no future candle to test
        if zone_end_pos == len(stock_data.index) - 1:
            return True

        # Slice the DataFrame to only dates *after* the zone's formation date
        future_dates = stock_data.index[zone_end_pos + 1:]

        # If any future candle overlaps the zone [distal, proximal], it's not fresh
        for date in future_dates:
            candle_low = stock_data.loc[date, 'Low']
            candle_high = stock_data.loc[date, 'High']
            # Overlap condition for a supply zone:
            # The candle's HIGH reaches/extends above the zone's top (proximal)
            # AND the candle's LOW dips at/below the zone's bottom (distal)
            if candle_high >= proximal and candle_low <= distal:
                return False

        return True
    
    @staticmethod
    def generate_demand_zones_info(demand_zones):
        info = "<h3>Demand Zones Information</h3><ul>"
        for zone in demand_zones:
            info += f"<li>Zone {zone['zone_id']}:<br>"
            for candle in zone['candles']:
                date_str = pd.to_datetime(candle['date']).strftime('%Y-%m-%d')  # Convert date to string format YYYY-MM-DD
                ohlc = candle['ohlc']
                info += (f"Date: {date_str}, Type: {candle['type']}, "
                        f"Open: {ohlc['Open']}, High: {ohlc['High']}, "
                        f"Low: {ohlc['Low']}, Close: {ohlc['Close']}<br>")
            info += f"Proximal: {zone['proximal']}, Distal: {zone['distal']}, Score: {zone['score']}</li><br>"
        info += "</ul>"
        return info