
import plotly.graph_objects as go
import logging


class CandleStickUtils:

    @staticmethod
    def add_candle_identifiers(stock_data, base_candle_threshold, exciting_candle_threshold):
    
       stock_data['Body'] = abs(stock_data['Close'] - stock_data['Open'])
       stock_data['UpperWick'] = stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)
       stock_data['LowerWick'] = stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']
    
       stock_data['BaseCandle'] = (
           (stock_data['UpperWick'] > base_candle_threshold * stock_data['Body']) | 
           (stock_data['LowerWick'] > base_candle_threshold * stock_data['Body'])
       )
    
       stock_data['GapUp'] = (
           stock_data['Open'] >= stock_data['Close'].shift(1) * 1.03
       )
    
       # Add GapDown identifier
       stock_data['GapDown'] = (
           stock_data['Open'] <= stock_data['Close'].shift(1) * 0.97
       )
    
       stock_data['ExcitingCandle'] = (
           ((stock_data['UpperWick'] < exciting_candle_threshold * stock_data['Body']) & 
           (stock_data['LowerWick'] < exciting_candle_threshold * stock_data['Body'])) | 
           stock_data['GapUp']
       )
    
       return stock_data

    @staticmethod
    def highlightCandlesAsExcitingOrBase(stock_data):
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
        
        return fig
    
    @staticmethod
    def markDemandZoneInfoOnChart(stock_code, fig, demand_zones, colors):
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