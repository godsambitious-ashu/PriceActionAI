import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import itertools
import logging
from stock_data.pattern_identifier import PatternIdentifier
from .demand_zone_identifier import DemandZoneIdentifier

class CandlestickChart:
    @staticmethod
    def create_chart(stock_data, stock_code):
        logging.debug("Starting to create candlestick chart")
        
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

        return fig


class CandleHighlighter:
    @staticmethod
    def highlight_base_candles(fig, stock_data):
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
        return fig

    @staticmethod
    def highlight_exciting_candles(fig, stock_data):
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
        return fig


class DemandZonePlotter:
    @staticmethod
    def add_demand_zones(fig, demand_zones):
        logging.debug("Adding demand zones to the chart")
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
        return fig


class DemandZoneInfoGenerator:
    @staticmethod
    def generate_info(demand_zones):
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


class Plotter:
    @staticmethod
    def create_candlestick_chart(stock_data, stock_code):
        logging.debug("Starting the full plotting process")

        # Calculate body and wicks
        stock_data['Body'] = abs(stock_data['Close'] - stock_data['Open'])
        stock_data['UpperWick'] = stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)
        stock_data['LowerWick'] = stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']

        base_candle_threshold = 0.5
        exciting_candle_threshold = 0.5
        stock_data = PatternIdentifier.add_candle_identifiers(stock_data, base_candle_threshold * 100, exciting_candle_threshold * 100)

        # Create candlestick chart
        fig = CandlestickChart.create_chart(stock_data, stock_code)

        # Highlight base and exciting candles
        fig = CandleHighlighter.highlight_base_candles(fig, stock_data)
        fig = CandleHighlighter.highlight_exciting_candles(fig, stock_data)

        # Identify and plot demand zones
        demand_zones = DemandZoneIdentifier.identify_demand_zones(stock_data)
        fig = DemandZonePlotter.add_demand_zones(fig, demand_zones)

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
        demand_zones_info = DemandZoneInfoGenerator.generate_info(demand_zones)
        
        return chart_html, demand_zones_info
