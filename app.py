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
        logging.debug(f"Form submitted: {stock_code} with interval {interval}")
        
        try:
            stock_data = DataFetcher.fetch_stock_data(stock_code, interval)
            logging.debug("Data fetched successfully")
            
            # Print the initial data in the format "date OHLC"
            stock_data_str = "\n".join([f"{idx.date()} Open: {row['Open']} High: {row['High']} Low: {row['Low']} Close: {row['Close']}" for idx, row in stock_data.iterrows()])
            logging.debug("Initial Stock Data:\n" + stock_data_str)
            
            chart, demand_zones_info = Plotter.create_candlestick_chart(stock_data, stock_code)
            logging.debug("Chart created successfully")
            
            return render_template('index.html', chart=chart, demand_zones_info=demand_zones_info, stock_data_str=stock_data_str)
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return render_template('index.html', chart=None, error=str(e))
    
    return render_template('index.html', chart=None)

if __name__ == '__main__':
    app.run(debug=True)
