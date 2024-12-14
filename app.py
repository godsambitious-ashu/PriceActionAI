from flask import Flask, request, render_template
from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
from stock_data.demand_zone_manager import DemandZoneManager
import plotly.io as pio

import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Retrieve form data
        stock_code = request.form['stock_code']
        interval = request.form['interval']
        period = request.form['period']
        logging.debug(f"Form submitted: {stock_code} with interval {interval} and period {period}")

        try:
            # Fetch stock data
            stock_data = DataFetcher.fetch_stock_data(stock_code, interval=interval, period=period)
            logging.debug("Data fetched successfully")

            # Generate a string representation of the stock data
            stock_data_str = "\n".join([
                f"{idx.date()} Open: {row['Open']} High: {row['High']} Low: {row['Low']} Close: {row['Close']}"
                for idx, row in stock_data.iterrows()
            ])
            logging.debug("Initial Stock Data:\n" + stock_data_str)

            # Step 1: Create the candlestick chart
            plotter = Plotter()
            fig = plotter.create_candlestick_chart(stock_data, stock_code, interval)

            # Step 2: Identify and mark all demand zones
            dz_manager_all = DemandZoneManager(stock_code, fig)
            demand_zones_all = dz_manager_all.identify_demand_zones(stock_data, interval, fresh=False)
            fig_all_zones = dz_manager_all.mark_demand_zones_on_chart(demand_zones_all)
            chart_all_zones = pio.to_html(fig_all_zones, full_html=False)
            demand_zones_info_all = dz_manager_all.generate_demand_zones_info(demand_zones_all)

            # Step 3: Identify and mark fresh demand zones
            dz_manager_fresh = DemandZoneManager(stock_code, fig)
            demand_zones_fresh = dz_manager_fresh.identify_demand_zones(stock_data, interval, fresh=True)
            fig_fresh_zones = dz_manager_fresh.mark_demand_zones_on_chart(demand_zones_fresh)
            chart_fresh_zones = pio.to_html(fig_fresh_zones, full_html=False)
            demand_zones_info_fresh = dz_manager_fresh.generate_demand_zones_info(demand_zones_fresh)

            logging.debug("Charts created successfully")

            # Render the template with the generated charts and information
            return render_template('index.html', 
                                   chart_all_zones=chart_all_zones, 
                                   demand_zones_info_all=demand_zones_info_all,
                                   chart_fresh_zones=chart_fresh_zones, 
                                   demand_zones_info_fresh=demand_zones_info_fresh,
                                   stock_data_str=stock_data_str)
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return render_template('index.html', chart=None, error=str(e))

    # For GET requests, render the template without any charts
    return render_template('index.html', chart=None)



if __name__ == '__main__':
    app.run(debug=True)
