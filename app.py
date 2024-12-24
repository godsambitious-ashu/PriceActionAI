# File: app.py

from flask import Flask, request, render_template, redirect, url_for, session
from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
from stock_data.demand_zone_manager import DemandZoneManager
import plotly.io as pio

import logging
from stock_data.gpt_client import GPTClient  # Import the GPTClient class

import json
from datetime import datetime  # Make sure to import datetime
import pandas as pd
import numpy as np

app = Flask(__name__)

# Secret key for session management. Replace with a strong, random key in production.
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s:%(message)s')

# Define the hardcoded intervals in order of higher to lower timeframe
HARDCODED_INTERVALS = ['3mo', '1mo', '1wk', '1d']

# === OpenAI API Configuration ===
# Hardcoded OpenAI API key for testing purposes.
# IMPORTANT: Do NOT commit this key to any public repository.
OPENAI_API_KEY = "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"  # Replace with your actual OpenAI API key

# Initialize GPTClient
try:
    gpt_client = GPTClient(api_key=OPENAI_API_KEY)
    logging.debug("GPTClient initialized successfully in app.py.")
except ValueError as ve:
    logging.error(f"GPTClient initialization failed: {ve}")
    gpt_client = None  # Handle gracefully if GPTClient fails to initialize


def call_openai_gpt(user_query, demand_zones_fresh_dict):
    """
    Wrapper function to call GPTClient's method.
    
    Args:
        user_query (str): The user's query.
        demand_zones_fresh_dict (dict): Fresh demand zones data.
    
    Returns:
        str: GPT-generated response or error message.
    """
    if not gpt_client:
        return "GPT functionality is not available at the moment."
    return gpt_client.call_gpt(user_query, demand_zones_fresh_dict)


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


@app.route('/customgpt', methods=['POST'])
def customgpt():
    """
    Handles GPT queries by calling the OpenAI API with the user's query
    plus any fresh demand zones data.
    """
    user_query = request.form.get('gpt_query', '').strip()

    if not user_query:
        session['gpt_answer'] = "Please enter a valid query."
        return redirect(url_for('index'))

    # Grab the fresh zones from session (stored in index()).
    demand_zones_fresh_dict = session.get('demand_zones_fresh_dict', {})

    # Call OpenAI GPT with user_query and demand_zones_fresh_dict
    gpt_answer = call_openai_gpt(user_query, demand_zones_fresh_dict)

    # Store the GPT answer in session, then redirect to index so it displays
    session['gpt_answer'] = gpt_answer
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
    # Check if user has entered their name and email
    if 'name' not in session or 'email' not in session:
        logging.debug("User not authenticated. Redirecting to /user_info")
        return redirect(url_for('user_info'))

    name = session.get('name')
    email = session.get('email')
    logging.debug(f"User Info from Session: Name={name}, Email={email}")

    # === GPT Integration ===
    # Pull the GPT answer from the session if it exists
    gpt_answer = session.pop('gpt_answer', None)
    # Pull the automatic GPT answer if exists
    gpt_auto_answer = session.pop('gpt_auto_answer', None)
    # === End GPT Integration ===

    if request.method == 'POST':
        # Retrieve form data
        stock_code = request.form['stock_code'].strip().upper()
        period = request.form['period']
        logging.debug(f"Form submitted: {stock_code} with period {period}")

        try:
            charts = {}
            demand_zones_info = {}
            plotter = Plotter()  # Initialize Plotter instance

            # Initialize a single DemandZoneManager instance
            dz_manager_all = DemandZoneManager(stock_code, None)

            # Dictionary to store fresh demand zones for all intervals
            all_demand_zones_fresh = {}

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
                demand_zones_all = dz_manager_all.include_higher_tf_zones_in_lower_tf_zones(
                    interval, demand_zones_all, zone_type='all'
                )

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
                demand_zones_fresh = dz_manager_all.include_higher_tf_zones_in_lower_tf_zones(
                    interval, demand_zones_fresh, zone_type='fresh'
                )

                # **Call GPT only when interval is '1d'**
                if interval == '1d':
                    # Store the fresh demand zones for '1d' interval
                    all_demand_zones_fresh[interval] = demand_zones_fresh

                    # === Automatic GPT Call ===
                    # Define a user query for the automatic GPT call
                    auto_gpt_query = (
                        f"Provide an analysis based on the fresh demand zones for stock {stock_code} "
                        f"over the {period} period."
                    )

                    # Call OpenAI GPT with the automatic query and demand zones
                    #gpt_auto_answer = call_openai_gpt(auto_gpt_query, all_demand_zones_fresh)

                    # Store the automatic GPT answer to pass to the template
                    session['gpt_auto_answer'] = gpt_auto_answer
                    # === End Automatic GPT Call ===

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

            # After processing all intervals, serialize and store the fresh demand zones in session
            serialized_fresh = gpt_client.serialize_demand_zones(all_demand_zones_fresh)
            session['demand_zones_fresh_dict'] = serialized_fresh

            return render_template(
                'index.html',
                charts=charts,
                demand_zones_info=demand_zones_info,
                name=name,
                email=email,
                # === GPT Integration ===
                gpt_answer=gpt_answer,
                gpt_auto_answer=gpt_auto_answer
                # === End GPT Integration ===
            )
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return render_template(
                'index.html',
                chart=None,
                error="An unexpected error occurred while processing your request.",
                name=name,
                email=email,
                # === GPT Integration ===
                gpt_answer=gpt_answer,
                gpt_auto_answer=gpt_auto_answer
                # === End GPT Integration ===
            )

    # For GET requests, render the template without any charts
    return render_template(
        'index.html',
        chart=None,
        name=name,
        email=email,
        # === GPT Integration ===
        gpt_answer=gpt_answer,
        gpt_auto_answer=gpt_auto_answer
        # === End GPT Integration ===
    )


if __name__ == '__main__':
    app.run(debug=True)