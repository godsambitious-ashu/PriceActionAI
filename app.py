from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_session import Session
from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
from stock_data.demand_zone_manager import DemandZoneManager
from stock_data.gpt_client import GPTClient
import logging
from datetime import datetime
import requests  # Added for Flowise API calls

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

# Flag to choose between ChatGPT and Flowise.
# If USE_FLOWISE is True, Flowise will be used instead of ChatGPT.
USE_FLOWISE = False  # Set to True to use Flowise
FLOWISE_API_URL = "http://localhost:3000/api/v1/prediction/5ddc4cb7-3544-4bce-8068-34e28f12529d"

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

# Define the stock codes to be processed for the multi-stock AI replies
MULTI_STOCK_CODES = [
    'NIFTY50', 'BANKNIFTY', 'NIFTYAUTO', 'NIFTYMETAL',
    'NIFTY FMCG', 'NIFTY PHARMA', 'NIFTY IT', 'NIFTY ENERGY',
    'NIFTY MEDIA', 'NIFTY REALTY', 'NIFTY PSU BANK'
]

def call_flowise(query, zones):
    """
    Calls the Flowise API with a combined query and context.
    """
    zones_context = ""
    if zones:
        for key, value in zones.items():
            zones_context += f"{key}: {value}\n"
    combined_query = f"{query}\n{zones_context}"
    payload = {"question": combined_query}
    logging.debug(f"Calling Flowise API with payload: {payload}")
    try:
        response = requests.post(FLOWISE_API_URL, json=payload)
        logging.debug(f"Flowise API response status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        logging.debug(f"Flowise API response data: {data}")
        # Check for 'answer', if not available, fallback to 'text'
        flowise_reply = data.get("answer") or data.get("text", "")
        logging.debug(f"Flowise reply extracted: {flowise_reply}")
        return flowise_reply
    except Exception as e:
        logging.error(f"Error calling Flowise API: {e}")
        return "Error calling Flowise API."

def call_ai(query, zones):
    """
    Wrapper to call either Flowise or GPTClient based on the USE_FLOWISE flag.
    """
    if USE_FLOWISE:
        logging.debug("USE_FLOWISE flag is True. Calling Flowise.")
        return call_flowise(query, zones)
    else:
        logging.debug("USE_FLOWISE flag is False. Using GPTClient.")
        if ENABLE_GPT and gpt_client:
            return gpt_client.call_gpt(query, zones)
        else:
            return "AI functionality is disabled."

def process_multi_stock_gpt_replies(period='2y'):
    """
    Process AI replies for all stocks defined in MULTI_STOCK_CODES.
    Returns a dictionary mapping each stock code to its AI reply.
    """
    multi_gpt_replies = {}
    for stock_code in MULTI_STOCK_CODES:
        try:
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
                fresh_1d_zones, 
                wk_demand_zones
            ) = dz_manager.process_all_intervals(HARDCODED_INTERVALS, period)
            
            if USE_FLOWISE or (ENABLE_GPT and gpt_client):
                zones = gpt_client.prepare_zones(
                    monthly_all_zones,
                    fresh_1d_zones,
                    current_market_price,
                    wk_demand_zones,
                    f"Stock Data for {stock_code}"
                )
                final_query = f"The current market price of {stock_code} is {current_market_price}."
                ai_reply = call_ai(final_query, {"main": zones})
                multi_gpt_replies[stock_code] = ai_reply
            else:
                multi_gpt_replies[stock_code] = "AI functionality is disabled."
        except Exception as e:
            logging.error(f"Error processing stock {stock_code}: {e}")
            multi_gpt_replies[stock_code] = f"Error processing stock {stock_code}."
    return multi_gpt_replies

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

        # Process multi-stock AI replies once at login and store them in session.
        if (USE_FLOWISE or (ENABLE_GPT and gpt_client)) and 'multi_stock_gpt_replies' not in session:
            session['multi_stock_gpt_replies'] = process_multi_stock_gpt_replies()

        return redirect(url_for('index'))

    return render_template('user_info.html')

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

    if (USE_FLOWISE or (ENABLE_GPT and gpt_client)):
        if request.method == 'GET':
            gpt_answer = session.pop('gpt_answer', None)
            gpt_auto_answer = session.pop('gpt_auto_answer', None)
        else:
            gpt_answer = session.get('gpt_answer')
            gpt_auto_answer = session.get('gpt_auto_answer')
    else:
        gpt_answer = None
        gpt_auto_answer = None
        logging.debug("AI functionality is disabled. Setting AI answers to None.")

    if request.method == 'POST':
        try:
            stock_code = request.form['stock_code'].strip().upper()
            period = request.form['period']
            logging.debug(f"Form submitted: {stock_code} with period {period}")

            previous_stock = session.get('current_stock_code')
            if previous_stock and previous_stock != stock_code:
                logging.debug("New stock searched. Clearing previous conversation history.")
                session['chat_history'] = []

            # Process Main Stock
            dz_manager = DemandZoneManager(stock_code)
            index_code = dz_manager.get_stock_codes_to_process(stock_code)
            (
                main_charts,
                main_demand_zones_info,
                main_supply_zones_info,
                main_all_demand_zones_fresh,
                main_all_supply_zones_fresh,
                main_monthly_all_zones,
                main_daily_all_zones,
                main_current_market_price,
                main_fresh_1d_zones, 
                main_wk_demand_zones
            ) = dz_manager.process_all_intervals(HARDCODED_INTERVALS, period)

            # Initialize Index Data Variables
            index_charts = None
            index_demand_zones_info = None
            index_supply_zones_info = None
            index_all_demand_zones_fresh = None
            index_all_supply_zones_fresh = None
            index_monthly_all_zones = None
            index_daily_all_zones = None
            index_current_market_price = None
            index_fresh_1d_zones = None
            index_wk_demand_zones = None

            # Process Index Stock if index_code exists
            if index_code:
                dz_manager_index = DemandZoneManager(index_code)
                (
                    index_charts,
                    index_demand_zones_info,
                    index_supply_zones_info,
                    index_all_demand_zones_fresh,
                    index_all_supply_zones_fresh,
                    index_monthly_all_zones,
                    index_daily_all_zones,
                    index_current_market_price,
                    index_fresh_1d_zones, 
                    index_wk_demand_zones
                ) = dz_manager_index.process_all_intervals(HARDCODED_INTERVALS, period)
                logging.debug(f"Processed index_code: {index_code}")
            else:
                logging.debug("No index_code found for the given stock_code.")

            # Prepare Zones for AI using Main Stock Data
            final_zones_for_gpt = {}
            if USE_FLOWISE or (ENABLE_GPT and gpt_client):
                # Prepare zones for main stock
                main_zones = gpt_client.prepare_zones(
                    main_monthly_all_zones,
                    main_fresh_1d_zones,
                    main_current_market_price,
                    main_wk_demand_zones, 
                    "Main Stock Data"
                )
                final_zones_for_gpt['main'] = main_zones
                logging.debug(f"Main zones prepared for AI: {main_zones}")

                # Prepare zones for index stock if available
                if index_code and index_monthly_all_zones and index_current_market_price:
                    index_zones = gpt_client.prepare_zones(
                        index_monthly_all_zones,
                        index_fresh_1d_zones,
                        index_current_market_price,
                        index_wk_demand_zones, 
                        "Index Data"
                    )
                    final_zones_for_gpt['index'] = index_zones
                    logging.debug(f"Index zones prepared for AI: {index_zones}")
                else:
                    logging.debug("No valid index zones data to prepare for AI.")

            # Generate AI Auto Answer using Combined Zones
            if (USE_FLOWISE or (ENABLE_GPT and gpt_client)) and final_zones_for_gpt:
                final_query = f"The current market price of the stock is {main_current_market_price}."
                if index_current_market_price:
                    final_query += f" The current market price of the index {index_code} is {index_current_market_price}."
                final_ai_answer = call_ai(final_query, final_zones_for_gpt)
                session['gpt_auto_answer'] = final_ai_answer
                gpt_auto_answer = final_ai_answer
                logging.debug(f"AI auto answer generated successfully: {final_ai_answer}")
            elif ENABLE_GPT:
                logging.debug("No valid zones data to generate AI auto answer.")
                gpt_auto_answer = "No sufficient data available for automatic analysis."
            else:
                gpt_auto_answer = None

            session['gpt_dto'] = final_zones_for_gpt
            logging.debug(f"Serialized fresh zones stored in session: {final_zones_for_gpt}")

            # Store Current Stock Code in Session
            session['current_stock_code'] = stock_code

            # Update Chat History
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

            # Prepare Data to Pass to Frontend
            frontend_data = {
                'main_stock': {
                    'charts': main_charts,
                    'demand_zones_info': main_demand_zones_info,
                    'supply_zones_info': main_supply_zones_info,
                    'all_demand_zones_fresh': main_all_demand_zones_fresh,
                    'all_supply_zones_fresh': main_all_supply_zones_fresh,
                    'monthly_all_zones': main_monthly_all_zones,
                    'daily_all_zones': main_daily_all_zones,
                    'current_market_price': main_current_market_price,
                    'fresh_1d_zones': main_fresh_1d_zones,
                    'wk_demand_zones': main_wk_demand_zones
                },
                'index_stock': {
                    'charts': index_charts,
                    'demand_zones_info': index_demand_zones_info,
                    'supply_zones_info': index_supply_zones_info,
                    'all_demand_zones_fresh': index_all_demand_zones_fresh,
                    'all_supply_zones_fresh': index_all_supply_zones_fresh,
                    'monthly_all_zones': index_monthly_all_zones,
                    'daily_all_zones': index_daily_all_zones,
                    'current_market_price': index_current_market_price,
                    'fresh_1d_zones': index_fresh_1d_zones,
                    'wk_demand_zones': index_wk_demand_zones
                }
            }

            return render_template(
                'index.html',
                charts=frontend_data['main_stock']['charts'],
                demand_zones_info=frontend_data['main_stock']['demand_zones_info'],
                supply_zones_info=frontend_data['main_stock']['supply_zones_info'],
                name=name,
                email=email,
                chat_history=session.get('chat_history', []),
                gpt_answer=gpt_answer,
                gpt_auto_answer=gpt_auto_answer,
                enable_gpt=ENABLE_GPT,
                active_chat_id=active_chat_id,
                index_code=index_code,
                index_charts=frontend_data['index_stock']['charts'],
                index_demand_zones_info=frontend_data['index_stock']['demand_zones_info'],
                index_supply_zones_info=frontend_data['index_stock']['supply_zones_info'],
                index_current_market_price=frontend_data['index_stock']['current_market_price'],
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

    # Retrieve Frontend Data from Session if Needed
    frontend_data = session.get('frontend_data', {})
    main_stock = frontend_data.get('main_stock', {})
    index_stock = frontend_data.get('index_stock', {})

    return render_template(
        'index.html',
        charts=main_stock.get('charts'),
        demand_zones_info=main_stock.get('demand_zones_info'),
        supply_zones_info=main_stock.get('supply_zones_info'),
        name=name,
        email=email,
        chat_history=chat_history,
        gpt_answer=gpt_answer,
        gpt_auto_answer=gpt_auto_answer,
        enable_gpt=ENABLE_GPT,
        active_chat_id=active_chat_id,
        index_code=None,  # No index_code on GET
        index_charts=index_stock.get('charts'),
        index_demand_zones_info=index_stock.get('demand_zones_info'),
        index_supply_zones_info=index_stock.get('supply_zones_info'),
        index_current_market_price=index_stock.get('current_market_price'),
    )

@app.route('/send_message', methods=['POST'])
def send_message():
    if not (USE_FLOWISE or (ENABLE_GPT and gpt_client)):
        return jsonify({'error': 'AI functionality is disabled.'}), 403

    user_message = request.form.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Empty message.'}), 400

    gpt_dto = session.get('gpt_dto', {})
    logging.debug(f"send_message - User message: {user_message} | gpt_dto: {gpt_dto}")
    ai_response = call_ai(user_message, gpt_dto)
    logging.debug(f"send_message - AI response: {ai_response}")
    
    return jsonify({'message': ai_response})

# New route: multi-stock display using cached AI replies
@app.route('/multi_stock', methods=['GET'])
def multi_stock():
    if 'name' not in session or 'email' not in session:
        logging.debug("User not authenticated. Redirecting to /user_info")
        return redirect(url_for('user_info'))
    
    # Retrieve the stored multi-stock AI replies from session.
    multi_gpt_replies = session.get('multi_stock_gpt_replies')
    if not multi_gpt_replies:
        multi_gpt_replies = process_multi_stock_gpt_replies()
        session['multi_stock_gpt_replies'] = multi_gpt_replies
    
    return render_template('multi_stock.html', gpt_replies=multi_gpt_replies)

if __name__ == '__main__':
    app.run(debug=True)
