# File: app.py

import pprint
from flask import Flask, request, render_template
from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
from stock_data.demand_zone_manager import DemandZoneManager
import plotly.io as pio

import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Define the hardcoded intervals in order of higher to lower timeframe
HARDCODED_INTERVALS = ['1mo', '1wk', '1d']

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Retrieve form data
        stock_code = request.form['stock_code']
        period = request.form['period']
        logging.debug(f"Form submitted: {stock_code} with period {period}")

        try:
            charts = {}
            demand_zones_info = {}
            stock_data_combined = ""
            plotter = Plotter()  # Initialize Plotter instance

            # Initialize a single DemandZoneManager instance
            # Note: Pass the first figure or None; we'll update 'fig' as needed
            dz_manager_all = DemandZoneManager(stock_code, None)

            for interval in HARDCODED_INTERVALS:
                logging.debug(f"Processing interval: {interval}")

                # Fetch stock data for the current interval
                stock_data = DataFetcher.fetch_stock_data(stock_code, interval=interval, period=period)
                logging.debug(f"Data fetched successfully for interval {interval}")

                # Generate a string representation of the stock data
                stock_data_str = "\n".join([
                    f"{idx.date()} Open: {row['Open']} High: {row['High']} Low: {row['Low']} Close: {row['Close']}"
                    for idx, row in stock_data.iterrows()
                ])
                logging.debug(f"Initial Stock Data for {interval}:\n{stock_data_str}")
                stock_data_combined += f"\n--- {interval} ---\n{stock_data_str}"

                # Step 1: Create the base candlestick chart
                base_fig = plotter.create_candlestick_chart(stock_data, stock_code, interval)
                dz_manager_all.fig = base_fig  # Update the figure in the manager

                # Step 2: Identify and mark all demand zones
                demand_zones_all = dz_manager_all.identify_demand_zones(stock_data, interval, fresh=False)
                logging.debug(f"Data fetched successfully for demandzonesall {demand_zones_all}")

                # Use the updated method to handle merging
                demand_zones_all = dz_manager_all.includeHigherTfDzInLDailyDz(interval, demand_zones_all)

                # Proceed to mark the zones on the chart
                fig_all_zones = dz_manager_all.mark_demand_zones_on_chart(demand_zones_all)
                chart_all_zones = pio.to_html(fig_all_zones, full_html=False)
                demand_zones_info_all = dz_manager_all.generate_demand_zones_info(demand_zones_all)

                # Step 3: Identify and mark fresh demand zones
                # Create a fresh copy of the base figure to avoid overlap
                fresh_fig = plotter.create_candlestick_chart(stock_data, stock_code, interval)
                dz_manager_fresh = DemandZoneManager(stock_code, fresh_fig)
                demand_zones_fresh = dz_manager_fresh.identify_demand_zones(stock_data, interval, fresh=True)
                fig_fresh_zones = dz_manager_fresh.mark_demand_zones_on_chart(demand_zones_fresh)
                chart_fresh_zones = pio.to_html(fig_fresh_zones, full_html=False)
                demand_zones_info_fresh = dz_manager_fresh.generate_demand_zones_info(demand_zones_fresh)

                # Store charts and info in dictionaries
                charts[interval] = {
                    'all_zones': chart_all_zones,
                    'fresh_zones': chart_fresh_zones
                }
                demand_zones_info[interval] = {
                    'all_zones_info': demand_zones_info_all,
                    'fresh_zones_info': demand_zones_info_fresh
                }

            return render_template('index.html', 
                                   charts=charts, 
                                   demand_zones_info=demand_zones_info,
                                   stock_data_str=stock_data_combined)
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return render_template('index.html', chart=None, error=str(e))

    # For GET requests, render the template without any charts
    return render_template('index.html', chart=None)

if __name__ == '__main__':
    app.run(debug=True)