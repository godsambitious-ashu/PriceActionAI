
import pandas as pd


class DemandZoneUtils:
    @staticmethod
    def is_fresh_demand_zone(stock_data, zone):
        # Check if the price has never entered the demand zone after it was created
        distal = zone['distal']
        end_date = stock_data.index[-1]
        zone_end_date = zone['dates'][-1]

        # Ensure that the end date of the zone is before the last date in stock_data
        if zone_end_date >= end_date:
            return True  # The zone is fresh because there are no dates after it

        for date in stock_data.loc[zone_end_date:end_date].index:
            if stock_data.loc[date, 'Low'] <= distal:
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