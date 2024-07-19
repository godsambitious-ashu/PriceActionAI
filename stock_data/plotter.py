import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import itertools
import logging
from stock_data.demand_zone_identifier import DemandZoneIdentifier
from stock_data.pattern_identifier import PatternIdentifier

class Plotter:
    @staticmethod
    def create_candlestick_chart(stock_data, stock_code, fresh=False):
        logging.debug("Starting to create candlestick chart")
        base_candle_threshold = 0.5
        exciting_candle_threshold = 0.5

        stock_data['Body'] = abs(stock_data['Close'] - stock_data['Open'])
        stock_data['UpperWick'] = stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)
        stock_data['LowerWick'] = stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']

        stock_data = PatternIdentifier.add_candle_identifiers(stock_data, base_candle_threshold * 100, exciting_candle_threshold * 100)

        fig = go.Figure(data=[go.Candlestick(
            x=stock_data.index,
            open=stock_data['Open'],
            high=stock_data['High'],
            low=stock_data['Low'],
            close=stock_data['Close'],
            increasing_line_color='green',
            decreasing_line_color='red',
            name='Candlesticks'
        )])

        logging.debug("Candlestick chart added")

        # Highlight base candles
        fig.add_trace(go.Scatter(
            x=stock_data[stock_data['BaseCandle']].index,
            y=stock_data[stock_data['BaseCandle']]['High'],
            mode='markers',
            marker=dict(
                color='blue',
                size=12,
                symbol='circle'
            ),
            name='Base Candles'
        ))
        logging.debug("Base candles highlighted")

        # Highlight exciting candles
        fig.add_trace(go.Scatter(
            x=stock_data[stock_data['ExcitingCandle']].index,
            y=stock_data[stock_data['ExcitingCandle']]['High'],
            mode='markers',
            marker=dict(
                color='orange',
                size=12,
                symbol='circle'
            ),
            name='Exciting Candles'
        ))
        logging.debug("Exciting candles highlighted")

        # Identify and mark demand zones
        logging.debug("Identifying demand zones")
        demand_zones = DemandZoneIdentifier.identify_demand_zones(stock_data)
        logging.debug(f"Demand zones identified: {len(demand_zones)} zones found")
        
        if fresh:
            demand_zones = [zone for zone in demand_zones if Plotter.is_fresh_demand_zone(stock_data, zone)]
            logging.debug(f"Fresh demand zones identified: {len(demand_zones)} zones found")

        colors = itertools.cycle(['purple', 'cyan', 'magenta', 'yellow', 'green', 'red'])

        for zone in demand_zones:
            color = next(colors)
            logging.debug(f"Adding shapes for pattern at index {zone['dates'][0]}")
            # Draw rectangle for each zone
            fig.add_shape(
                type='rect',
                x0=zone['dates'][0], y0=zone['distal'],
                x1=zone['dates'][-1], y1=zone['proximal'],
                line=dict(color=color, width=2),
                fillcolor=color, opacity=0.3,
            )
            logging.debug(f"Proximal line added at {zone['dates'][0]}")
            logging.debug(f"Distal line added at {zone['dates'][0]}")

        fig.update_layout(
            title=f'Candlestick Chart for {stock_code}',
            xaxis_title='Date',
            yaxis_title='Price',
            xaxis_rangeslider_visible=False,
            autosize=True,
            height=800,  # Increased figure height for better visibility
            width=1600,  # Increased figure width for better visibility
            margin=dict(l=50, r=50, t=50, b=50),
            font=dict(size=12),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        chart_html = pio.to_html(fig, full_html=False)
        demand_zones_info = Plotter.generate_demand_zones_info(demand_zones)
        
        return chart_html, demand_zones_info

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
            info += f"Proximal: {zone['proximal']}, Distal: {zone['distal']}</li><br>"
        info += "</ul>"
        return info

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