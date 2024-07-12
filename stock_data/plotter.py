import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import itertools
import logging
from stock_data.pattern_identifier import PatternIdentifier

class Plotter:
    @staticmethod
    def create_candlestick_chart(stock_data, stock_code):
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
            decreasing_line_color='red'
        )])

        logging.debug("Candlestick chart added")

        # Highlight base candles
        fig.add_trace(go.Scatter(
            x=stock_data[stock_data['BaseCandle']].index,
            y=stock_data[stock_data['BaseCandle']]['High'],
            mode='markers',
            marker=dict(
                color='blue',
                size=10,
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
                size=10,
                symbol='circle'
            ),
            name='Exciting Candles'
        ))
        logging.debug("Exciting candles highlighted")

        # Identify and mark demand zones
        logging.debug("Identifying demand zones")
        demand_zones = Plotter.identify_demand_zones(stock_data)
        logging.debug(f"Demand zones identified: {len(demand_zones)} zones found")
        
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
            autosize=True
        )
        
        chart_html = pio.to_html(fig, full_html=False)
        
        return chart_html

    @staticmethod
    def identify_demand_zones(stock_data):
        logging.debug("Starting to identify demand zones")
        patterns = []
        zone_id = 1
        n = len(stock_data)
        
        i = 0
        while i < n - 4:
            logging.debug(f"Checking candle at index {i}")
            if stock_data.iloc[i]['ExcitingCandle']:
                logging.debug(f"Found exciting candle at index {i}")
                first_exciting_candle_is_green = stock_data.iloc[i]['Close'] > stock_data.iloc[i]['Open']
                if i + 1 < n and stock_data.iloc[i + 1]['BaseCandle']:
                    logging.debug(f"Found base candle at index {i+1}")
                    base_candles = [stock_data.iloc[i + 1]]
                    if i + 2 < n and stock_data.iloc[i + 2]['BaseCandle']:
                        logging.debug(f"Found base candle at index {i+2}")
                        base_candles.append(stock_data.iloc[i + 2])
                    if i + 3 < n and stock_data.iloc[i + 3]['BaseCandle']:
                        logging.debug(f"Found base candle at index {i+3}")
                        base_candles.append(stock_data.iloc[i + 3])
                    if i + len(base_candles) + 1 < n and stock_data.iloc[i + len(base_candles) + 1]['ExcitingCandle'] and stock_data.iloc[i + len(base_candles) + 1]['Close'] > stock_data.iloc[i + len(base_candles) + 1]['Open']:
                        logging.debug(f"Found green exciting candle at index {i + len(base_candles) + 1}")
                        zone_dates = stock_data.index[i:i + len(base_candles) + 2]
                        proximal = max(max(candle['Open'], candle['Close']) for candle in base_candles)
                        
                        if first_exciting_candle_is_green:
                            distal = min(candle['Low'] for candle in base_candles + [stock_data.iloc[i + len(base_candles) + 1]])
                        else:
                            distal = min(stock_data.iloc[i]['Low'], *(candle['Low'] for candle in base_candles))

                        patterns.append({
                            'zone_id': zone_id,
                            'dates': zone_dates,
                            'proximal': proximal,
                            'distal': distal,
                            'candles': [{'date': stock_data.index[i], 'type': 'Exciting', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[i][['Open', 'High', 'Low', 'Close']].to_dict().items()}}] +
                                       [{'date': stock_data.index[i + j], 'type': 'Base', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[i + j][['Open', 'High', 'Low', 'Close']].to_dict().items()}} for j in range(1, len(base_candles) + 1)] +
                                       [{'date': stock_data.index[i + len(base_candles) + 1], 'type': 'Exciting', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[i + len(base_candles) + 1][['Open', 'High', 'Low', 'Close']].to_dict().items()}}]
                        })
                        logging.debug(f"Pattern identified with dates: {zone_dates} and prices: proximal={proximal}, distal={distal}")
                        zone_id += 1
                        i = i + len(base_candles) + 1  # Move past the identified pattern
                    else:
                        i += 1  # Move to the next candle
                else:
                    i += 1  # Move to the next candle
            else:
                i += 1  # Move to the next candle
        
        logging.debug("Demand zones identification completed")
        return patterns
