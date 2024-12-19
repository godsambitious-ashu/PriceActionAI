# File: app.py

import pprint
from flask import Flask, request, render_template, redirect, url_for, session
from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
from stock_data.demand_zone_manager import DemandZoneManager
import plotly.io as pio

import logging

app = Flask(__name__)

# Secret key for session management. Replace with a strong, random key in production.
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

logging.basicConfig(level=logging.DEBUG)

# Define the hardcoded intervals in order of higher to lower timeframe
HARDCODED_INTERVALS = ['3mo', '1mo', '1wk', '1d']

@app.route('/user_info', methods=['GET', 'POST'])
def user_info():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form.get('name')
        email = request.form.get('email')
        logging.debug(f"User Info Submitted: Name={name}, Email={email}")

        # Store in session
        session['name'] = name
        session['email'] = email

        # Redirect to the main visualization page
        return redirect(url_for('index'))

    # For GET requests, render the user info form
    return render_template('user_info.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    # Check if user has entered their name and email
    if 'name' not in session or 'email' not in session:
        logging.debug("User not authenticated. Redirecting to /user_info")
        return redirect(url_for('user_info'))

    name = session.get('name')
    email = session.get('email')
    logging.debug(f"User Info from Session: Name={name}, Email={email}")

    if request.method == 'POST':
        # Retrieve form data
        stock_code = request.form['stock_code']
        period = request.form['period']
        logging.debug(f"Form submitted: {stock_code} with period {period}")

        try:
            charts = {}
            demand_zones_info = {}
            plotter = Plotter()  # Initialize Plotter instance

            # Initialize a single DemandZoneManager instance
            dz_manager_all = DemandZoneManager(stock_code, None)

            for interval in HARDCODED_INTERVALS:
                logging.debug(f"Processing interval: {interval}")

                # Fetch stock data for the current interval
                stock_data = DataFetcher.fetch_stock_data(stock_code, interval=interval, period=period)
                logging.debug(f"Data fetched successfully for interval {interval}")

                # Step 1: Create the base candlestick chart
                base_fig = plotter.create_candlestick_chart(stock_data, stock_code, interval)
                dz_manager_all.fig = base_fig  # Update the figure in the manager

                # Step 2: Identify and mark all demand zones
                demand_zones_all = dz_manager_all.identify_demand_zones(stock_data, interval, fresh=False)

                # Use the updated method to handle merging for "all zones"
                demand_zones_all = dz_manager_all.include_higher_tf_zones_in_lower_tf_zones(interval, demand_zones_all, zone_type='all')

                # Proceed to mark the "all zones" on the chart
                fig_all_zones = dz_manager_all.mark_demand_zones_on_chart(demand_zones_all)
                chart_all_zones = pio.to_html(fig_all_zones, full_html=False)
                demand_zones_info_all = dz_manager_all.generate_demand_zones_info(demand_zones_all)

                # Step 3: Identify and mark fresh demand zones
                # Create a fresh copy of the base figure to avoid overlap
                fresh_fig = plotter.create_candlestick_chart(stock_data, stock_code, interval)
                dz_manager_fresh = DemandZoneManager(stock_code, fresh_fig)
                demand_zones_fresh = dz_manager_fresh.identify_demand_zones(stock_data, interval, fresh=True)
                logging.debug(f"Data fetched successfully for demand_zones_fresh: {demand_zones_fresh}")

                # Use the updated method to handle merging for "fresh zones"
                demand_zones_fresh = dz_manager_all.include_higher_tf_zones_in_lower_tf_zones(interval, demand_zones_fresh, zone_type='fresh')

                # Proceed to mark the "fresh zones" on the chart
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
                                   name=name,
                                   email=email)
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return render_template('index.html', chart=None, error=str(e), name=name, email=email)

    # For GET requests, render the template without any charts
    return render_template('index.html', chart=None, name=name, email=email)

if __name__ == '__main__':
    app.run(debug=True)