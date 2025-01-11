
import logging
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

        # Create initial candlestick chart with highlighted candles
        fig = CandleStickUtils.highlightCandlesAsExcitingOrBase(stock_data)

        # Update layout for TradingView-like tracer, aesthetics, and interactions
        fig.update_layout(
            template='plotly_white',      # White theme for a light background
            title=dict(
                text=f'Candlestick Chart for {stock_code}',
                font=dict(color='black')
            ),
            hovermode='x unified',        # Unified hover along x-axis
            spikedistance=-1,             # Activate spikes for entire chart area
            hoverlabel=dict(
                bgcolor="white",
                font_color="black",
                font_size=12,
                font_family="Arial"
            ),
            dragmode='zoom',              # Enable zoom on drag
            xaxis=dict(
                showspikes=True,
                spikemode='across',
                spikesnap='cursor',
                spikecolor='grey',
                spikedash='dot',
                spikethickness=1,
                showline=True,
                showgrid=False,           # Remove x-axis grid
                tickformat='%Y-%m-%d',
                tickfont=dict(color='black'),
                title_font=dict(color='black')
            ),
            yaxis=dict(
                side='right',             # Display y-axis (price) on the right side
                showspikes=True,
                spikemode='across',
                spikesnap='cursor',
                spikecolor='grey',
                spikedash='dot',
                spikethickness=1,
                showline=True,
                showgrid=False,           # Remove y-axis grid
                tickfont=dict(color='black'),
                title_font=dict(color='black')
            ),
            xaxis_rangeslider_visible=False,
            autosize=True,
            height=800,
            width=1600,
            margin=dict(l=50, r=50, t=50, b=50),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        logging.debug("Candlestick chart created successfully")
        return fig