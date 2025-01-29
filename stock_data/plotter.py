import logging
import plotly.graph_objects as go
from stock_data.candlestick_utils import CandleStickUtils

class Plotter:
    @staticmethod
    def create_candlestick_chart(stock_data, stock_code, interval):
        logging.debug("Starting to create candlestick chart")
        base_candle_threshold = 0.5
        exciting_candle_threshold = 0.5

        # Calculate candle components
        stock_data['Body'] = abs(stock_data['Close'] - stock_data['Open'])
        stock_data['UpperWick'] = stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)
        stock_data['LowerWick'] = stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']

        # Add candle identifiers
        stock_data = CandleStickUtils.add_candle_identifiers(
            stock_data,
            base_candle_threshold,
            exciting_candle_threshold
        )

        # Calculate the 20-period Exponential Moving Average (EMA)
        stock_data['EMA20'] = stock_data['Close'].ewm(span=20, adjust=False).mean()
        logging.debug("Calculated EMA20")

        # Create initial candlestick chart with highlighted candles
        fig = CandleStickUtils.highlightCandlesAsExcitingOrBase(stock_data)

        # Add EMA20 to the candlestick chart
        fig.add_trace(
            go.Scatter(
                x=stock_data.index,
                y=stock_data['EMA20'],
                mode='lines',
                name='EMA20',
                line=dict(color='blue', width=2)
            )
        )
        logging.debug("Added EMA20 to the chart")

        # Update layout for TradingView-like tracer and price highlighting
        fig.update_layout(
            template='plotly_white',
            title=dict(
                text=f'Candlestick Chart for {stock_code}',
                font=dict(color='black')
            ),
            hovermode='x unified',
            spikedistance=-1,
            hoverlabel=dict(
                bgcolor="white",
                font_color="black",
                font_size=12,
                font_family="Arial"
            ),
            dragmode='zoom',  # Enables zooming by dragging
            xaxis=dict(
                showspikes=True,
                spikemode='across',
                spikesnap='cursor',
                spikecolor='black',
                spikedash='solid',
                spikethickness=1,
                showline=True,
                showgrid=False,
                tickformat='%Y-%m-%d',
                tickfont=dict(color='black'),
                title_font=dict(color='black'),
                fixedrange=False,  # Allow horizontal zooming
                rangeslider=dict(
                    visible=False  # Hide the range slider
                )
            ),
            yaxis=dict(
                side='right',
                showspikes=True,
                spikemode='across',
                spikesnap='cursor',
                spikecolor='rgba(0,0,0,0.3)',  # Semi-transparent spike
                spikedash='solid',
                spikethickness=1,
                showline=True,
                showgrid=False,
                tickformat='.2f',
                tickfont=dict(color='black'),
                title_font=dict(color='black'),
                fixedrange=False  # Allow vertical zooming
            ),
            xaxis_rangeslider_visible=False,
            autosize=True,
            height=800,
            width=1600,
            margin=dict(l=50, r=50, t=50, b=50),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            modebar=dict(
                orientation='h',  # Horizontal modebar
                bgcolor='rgba(0,0,0,0)',  # Transparent background
                color='black',  # Icon color
                activecolor='blue',  # Active icon color
                # No custom buttons added
            )
        )

        logging.debug("Configured layout without custom buttons")

        # Remove Range Selector buttons by not adding them
        # Ensure no updatemenus or range selectors are present

        logging.debug("Candlestick chart created successfully with EMA20 and price tracking")
        return fig
