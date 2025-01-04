from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
from stock_data.demand_zone_manager import DemandZoneManager
from stock_data.gpt_client import GPTClient  # Import the GPTClient class
import plotly.io as pio

import logging
import os
from datetime import datetime

app = Flask(__name__)

# Secret key for session management. Replace with a strong, random key in production.
app.secret_key = 'your_secret_key_here'  # Keep your secret key secure in production

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s:%(message)s')

# Define the hardcoded intervals in order of higher to lower timeframe
HARDCODED_INTERVALS = ['3mo', '1mo', '1wk', '1d']

# === GPT Enable/Disable Flag ===
ENABLE_GPT = False  # Set to True to enable GPT functionality
# === End GPT Enable/Disable Flag ===

# === OpenAI API Configuration ===
# Only configure GPT if ENABLE_GPT is True
if ENABLE_GPT:
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
else:
    gpt_client = None  # GPTClient is not initialized when GPT is disabled
    logging.debug("GPT functionality is disabled via ENABLE_GPT flag.")

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

        # Initialize chat history if not present
        if 'chat_history' not in session:
            session['chat_history'] = []

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
    if not ENABLE_GPT:
        logging.debug("customgpt: GPT functionality is disabled via ENABLE_GPT flag.")
        session['gpt_answer'] = "GPT functionality is disabled."
        return redirect(url_for('index'))

    user_query = request.form.get('gpt_query', '').strip()
    stock_code = request.form.get('stock_code', 'General')  # Assuming stock_code is passed in the form

    if not user_query:
        session['gpt_answer'] = "Please enter a valid query."
        return redirect(url_for('index'))

    # Grab the fresh zones from session (stored in index()).
    demand_zones_fresh_dict = session.get('demand_zones_fresh_dict', {})

    # Call GPT via GPTClient
    gpt_answer = gpt_client.call_gpt(user_query, demand_zones_fresh_dict) if gpt_client else "GPT functionality is not available at the moment."
    logging.debug(f"customgpt: GPT Answer Generated: {gpt_answer}")

    # Append user message and GPT response to chat history
    chat_history = session.get('chat_history', [])

    # Create a new chat session for the GPT query
    chat_session = {
        'stock_code': stock_code,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'user_query': user_query,
        'gpt_answer': gpt_answer
        # Removed 'charts' from the session
    }

    chat_history.append(chat_session)
    session['chat_history'] = chat_history  # Save back to session

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
    # Check if user has entered their name and email
    if 'name' not in session or 'email' not in session:
        logging.debug("User not authenticated. Redirecting to /user_info")
        return redirect(url_for('user_info'))

    name = session.get('name')
    email = session.get('email')
    logging.debug(f"User Info from Session: Name={name}, Email={email}")

    # === GPT Integration ===
    if ENABLE_GPT and gpt_client:
        if request.method == 'GET':
            # Retrieve and remove GPT answers from session for GET requests
            gpt_answer = session.pop('gpt_answer', None)
            gpt_auto_answer = session.pop('gpt_auto_answer', None)
            logging.debug(f"index(GET): Retrieved GPT answers from session: gpt_answer={gpt_answer}, gpt_auto_answer={gpt_auto_answer}")
        else:
            # For POST requests, retrieve without removing
            gpt_answer = session.get('gpt_answer')
            gpt_auto_answer = session.get('gpt_auto_answer')
            logging.debug(f"index(POST): Retrieved GPT answers from session: gpt_answer={gpt_answer}, gpt_auto_answer={gpt_auto_answer}")
    else:
        # If GPT is disabled, set answers to None
        gpt_answer = None
        gpt_auto_answer = None
        logging.debug("GPT functionality is disabled. Setting GPT answers to None.")
    # === End GPT Integration ===

    if request.method == 'POST':
        # Retrieve form data
        stock_code = request.form['stock_code'].strip().upper()
        period = request.form['period']
        logging.debug(f"Form submitted: {stock_code} with period {period}")

        try:
            # Initialize DemandZoneManager
            dz_manager = DemandZoneManager(stock_code)

            # Process all intervals using the refactored DemandZoneManager
            (
                charts,
                demand_zones_info,
                all_demand_zones_fresh,
                monthly_fresh_zones,
                daily_all_zones,
                current_market_price
            ) = dz_manager.process_all_intervals(HARDCODED_INTERVALS, period)

            # After processing, prepare data for GPT
            final_zones_for_gpt = gpt_client.prepare_zones(monthly_fresh_zones, daily_all_zones) if ENABLE_GPT and gpt_client else {}
            if current_market_price is not None:
                final_zones_for_gpt['current_market_price'] = current_market_price

            logging.debug(f"Final zones prepared for GPT: {final_zones_for_gpt}")

            if ENABLE_GPT and gpt_client and final_zones_for_gpt:
                final_query = (
                    "Provide an analysis based on the 1mo fresh demand zones and the 1d all demand zones "
                    "that lie within the 1mo zones' proximal-distal range. "
                    f"The current market price of the stock is {current_market_price}."
                )
                logging.debug(f"Final GPT Query: {final_query}")

                # Now call GPT just once
                final_gpt_answer = gpt_client.call_gpt(final_query, final_zones_for_gpt)
                logging.debug(f"Automatic GPT Analysis Generated: {final_gpt_answer}")

                # Store that final GPT answer in session
                session['gpt_auto_answer'] = final_gpt_answer

                # Assign the final GPT answer to the local variable for immediate rendering
                gpt_auto_answer = final_gpt_answer

            elif ENABLE_GPT:
                logging.debug("No valid zones data to generate GPT auto answer.")
                gpt_auto_answer = "No sufficient data available for automatic analysis."
            else:
                # GPT is disabled
                gpt_auto_answer = None

            # Serialize and store the fresh demand zones in session (if needed elsewhere)
            serialized_fresh = gpt_client.serialize_demand_zones(all_demand_zones_fresh) if ENABLE_GPT and gpt_client else {}
            session['demand_zones_fresh_dict'] = serialized_fresh

            # Store current_stock_code in session
            session['current_stock_code'] = stock_code

            # === Create a new chat session for this stock search ===
            chat_history = session.get('chat_history', [])
            chat_session = {
                'stock_code': stock_code,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'user_query': f"Searched {stock_code} with period {period}",
                'gpt_answer': gpt_auto_answer if gpt_auto_answer else ""
                # Removed 'charts' from the session
            }
            chat_history.append(chat_session)
            session['chat_history'] = chat_history

            # Make this newly created chat active by default
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

    # Handle GET requests by rendering the template with existing chat history
    logging.debug("Handling GET request for index.")

    # By default, show the last chat if any
    chat_history = session.get('chat_history', [])
    if chat_history:
        active_chat_id = len(chat_history) - 1
    else:
        active_chat_id = 0

    return render_template(
        'index.html',
        charts=None,  # No charts to display on GET
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
    """
    Optional: Handle chat messages via AJAX
    """
    if not ENABLE_GPT:
        return jsonify({'error': 'GPT functionality is disabled.'}), 403

    user_message = request.form.get('message', '').strip()
    stock_code = request.form.get('stock_code', 'General')

    if not user_message:
        return jsonify({'error': 'Empty message.'}), 400

    # Append user message to the latest chat
    chat_history = session.get('chat_history', [])
    if not chat_history:
        # Create a new chat if none exist
        chat_session = {
            'stock_code': stock_code,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_query': user_message,
            'gpt_answer': ""
            # Removed 'charts' from the session
        }
        chat_history.append(chat_session)
    else:
        # Use the latest chat
        latest_chat = chat_history[-1]
        # We'll append the user message and GPT response in a combined string
        existing_answer = latest_chat.get('gpt_answer', '')
        if existing_answer:
            updated_answer = existing_answer + "\n\n---\n\n" + f"User: {user_message}\nGPT: "
        else:
            updated_answer = f"User: {user_message}\nGPT: "
        latest_chat['gpt_answer'] = updated_answer
        chat_history[-1] = latest_chat

    # Call GPT via GPTClient
    gpt_response = gpt_client.call_gpt(user_message, session.get('demand_zones_fresh_dict', {})) if gpt_client else "GPT functionality is not available at the moment."

    # Update the latest chat with the GPT response
    latest_chat = chat_history[-1]
    existing_answer = latest_chat.get('gpt_answer', '')
    latest_chat['gpt_answer'] = existing_answer + gpt_response
    chat_history[-1] = latest_chat

    session['chat_history'] = chat_history

    return jsonify({'message': gpt_response})

if __name__ == '__main__':
    app.run(debug=True)