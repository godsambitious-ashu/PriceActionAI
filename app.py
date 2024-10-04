from flask import Flask, request, render_template
from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        stock_code = request.form['stock_code']
        interval = request.form['interval']
        period = request.form['period']
        show_higher_timeframe_zones = 'higher_timeframe_toggle' in request.form
        logging.debug(f"Form submitted: {stock_code} with interval {interval} and period {period}, show_higher_timeframe_zones: {show_higher_timeframe_zones}")
        
        try:
            # Fetch data for daily interval
            stock_data_daily = DataFetcher.fetch_stock_data(stock_code, interval='1d', period=period)
            logging.debug("Daily data fetched successfully")
            
            if show_higher_timeframe_zones:
                # Fetch data for weekly and monthly intervals
                stock_data_weekly = DataFetcher.fetch_stock_data(stock_code, interval='1wk', period=period)
                stock_data_monthly = DataFetcher.fetch_stock_data(stock_code, interval='1mo', period=period)
                logging.debug("Weekly and monthly data fetched successfully")
                
                # Identify demand zones on weekly and monthly data
                demand_zones_weekly = DemandZoneIdentifier.identify_demand_zones(stock_data_weekly, interval='1wk')
                demand_zones_monthly = DemandZoneIdentifier.identify_demand_zones(stock_data_monthly, interval='1mo')
                
                # Map higher timeframe zones to daily data
                higher_timeframe_zones = Plotter.map_higher_timeframe_zones_to_daily(stock_data_daily, demand_zones_weekly + demand_zones_monthly)
                
                # Create chart with higher timeframe zones overlaid on daily data
                chart_higher_timeframe_zones = Plotter.create_candlestick_chart_with_zones(stock_data_daily, stock_code, higher_timeframe_zones)
                
                return render_template('index.html',
                                       chart_higher_timeframe_zones=chart_higher_timeframe_zones,
                                       stock_code=stock_code,
                                       show_higher_timeframe_zones=show_higher_timeframe_zones)
            else:
                # Existing functionality
                # Create charts for both all zones and fresh zones
                chart_all_zones, demand_zones_info_all = Plotter.create_candlestick_chart(stock_data_daily, stock_code, interval='1d', fresh=False)
                chart_fresh_zones, demand_zones_info_fresh = Plotter.create_candlestick_chart(stock_data_daily, stock_code, interval='1d', fresh=True)
                logging.debug("Charts created successfully")
                
                return render_template('index.html', 
                                       chart_all_zones=chart_all_zones, 
                                       demand_zones_info_all=demand_zones_info_all,
                                       chart_fresh_zones=chart_fresh_zones, 
                                       demand_zones_info_fresh=demand_zones_info_fresh,
                                       stock_code=stock_code)
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return render_template('index.html', chart=None, error=str(e))
    
    return render_template('index.html', chart=None)
