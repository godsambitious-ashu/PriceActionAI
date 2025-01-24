from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_session import Session
from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
from stock_data.demand_zone_manager import DemandZoneManager
from stock_data.gpt_client import GPTClient
import plotly.io as pio

import logging
import os
from datetime import datetime

app = Flask(__name__)

# Secret key for session management. Replace with a strong, random key in production.
app.secret_key = 'your_secret_key_here'

# Configure server-side sessions using Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session/'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

HARDCODED_INTERVALS = ['3mo', '1mo', '1wk', '1d']
ENABLE_GPT = True

if ENABLE_GPT:
    OPENAI_API_KEY = "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"  # Replace with your OpenAI API key.
    try:
        gpt_client = GPTClient(api_key=OPENAI_API_KEY)
        logging.debug("GPTClient initialized successfully in app.py.")
    except ValueError as ve:
        logging.error(f"GPTClient initialization failed: {ve}")
        gpt_client = None
else:
    gpt_client = None
    logging.debug("GPT functionality is disabled via ENABLE_GPT flag.")

@app.route('/user_info', methods=['GET', 'POST'])
def user_info():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        logging.debug(f"User Info Submitted: Name={name}, Email={email}")

        session['name'] = name
        session['email'] = email

        if 'chat_history' not in session:
            session['chat_history'] = []

        return redirect(url_for('index'))

    return render_template('user_info.html')

@app.route('/customgpt', methods=['POST'])
def customgpt():
    # Legacy route; not used with AJAX.
    return redirect(url_for('index'))

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    chat_history = session.get('chat_history', [])
    return jsonify({'chat_history': chat_history})

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    session['chat_history'] = []
    logging.debug("Chat history cleared.")
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'name' not in session or 'email' not in session:
        logging.debug("User not authenticated. Redirecting to /user_info")
        return redirect(url_for('user_info'))

    name = session.get('name')
    email = session.get('email')
    logging.debug(f"User Info from Session: Name={name}, Email={email}")

    if ENABLE_GPT and gpt_client:
        if request.method == 'GET':
            gpt_answer = session.pop('gpt_answer', None)
            gpt_auto_answer = session.pop('gpt_auto_answer', None)
        else:
            gpt_answer = session.get('gpt_answer')
            gpt_auto_answer = session.get('gpt_auto_answer')
    else:
        gpt_answer = None
        gpt_auto_answer = None
        logging.debug("GPT functionality is disabled. Setting GPT answers to None.")

    if request.method == 'POST':
        try:
            stock_code = request.form['stock_code'].strip().upper()
            period = request.form['period']
            logging.debug(f"Form submitted: {stock_code} with period {period}")

            previous_stock = session.get('current_stock_code')
            if previous_stock and previous_stock != stock_code:
                logging.debug("New stock searched. Clearing previous conversation history.")
                session['chat_history'] = []

            dz_manager = DemandZoneManager(stock_code)
            (
                charts,
                demand_zones_info,
                supply_zones_info,
                all_demand_zones_fresh,
                all_supply_zones_fresh,
                monthly_all_zones,
                daily_all_zones,
                current_market_price,
                fresh_1d_zones, wk_demand_zones
            ) = dz_manager.process_all_intervals(HARDCODED_INTERVALS, period)

            final_zones_for_gpt = gpt_client.prepare_zones(monthly_all_zones, fresh_1d_zones, current_market_price, wk_demand_zones) if ENABLE_GPT and gpt_client else {}

            logging.debug(f"Final zones prepared for GPT: {final_zones_for_gpt}")

            if ENABLE_GPT and gpt_client and final_zones_for_gpt:
                final_query = f"The current market price of the stock is {current_market_price}."

                final_gpt_answer = gpt_client.call_gpt(final_query, final_zones_for_gpt)

                session['gpt_auto_answer'] = final_gpt_answer
                gpt_auto_answer = final_gpt_answer
            elif ENABLE_GPT:
                logging.debug("No valid zones data to generate GPT auto answer.")
                gpt_auto_answer = "No sufficient data available for automatic analysis."
            else:
                gpt_auto_answer = None

            serialized_fresh = gpt_client.serialize_demand_zones(final_zones_for_gpt) if ENABLE_GPT and gpt_client else {}
            session['demand_zones_fresh_dict'] = final_zones_for_gpt
            logging.debug(f"Serialized fresh zones stored in session: {final_zones_for_gpt}")

            session['current_stock_code'] = stock_code

            chat_history = session.get('chat_history', [])
            chat_session = {
                'stock_code': stock_code,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'user_query': f"Searched {stock_code} with period {period}",
                'gpt_answer': gpt_auto_answer if gpt_auto_answer else ""
            }
            chat_history.append(chat_session)
            session['chat_history'] = chat_history

            active_chat_id = len(chat_history) - 1

            return render_template(
                'index.html',
                charts=charts,
                demand_zones_info=demand_zones_info,
                name=name,
                email=email,
                chat_history=session.get('chat_history', []),
                gpt_answer=gpt_answer,
                gpt_auto_answer=gpt_auto_answer,
                enable_gpt=ENABLE_GPT,
                active_chat_id=active_chat_id
            )
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return render_template(
                'index.html',
                charts=None,
                error="An unexpected error occurred while processing your request.",
                name=name,
                email=email,
                chat_history=session.get('chat_history', []),
                gpt_answer=gpt_answer,
                gpt_auto_answer=gpt_auto_answer,
                enable_gpt=ENABLE_GPT,
                active_chat_id=0
            )

    logging.debug("Handling GET request for index.")
    chat_history = session.get('chat_history', [])
    active_chat_id = len(chat_history) - 1 if chat_history else 0

    return render_template(
        'index.html',
        charts=None,
        name=name,
        email=email,
        chat_history=chat_history,
        gpt_answer=gpt_answer,
        gpt_auto_answer=gpt_auto_answer,
        enable_gpt=ENABLE_GPT,
        active_chat_id=active_chat_id
    )

@app.route('/send_message', methods=['POST'])
def send_message():
    if not ENABLE_GPT:
        return jsonify({'error': 'GPT functionality is disabled.'}), 403

    user_message = request.form.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Empty message.'}), 400

    gpt_response = "GPT not available."
    if gpt_client:
        demand_zones_fresh_dict = session.get('demand_zones_fresh_dict', {})
        gpt_response = gpt_client.call_gpt(user_message, demand_zones_fresh_dict)
    
    return jsonify({'message': gpt_response})

if __name__ == '__main__':
    app.run(debug=True)
