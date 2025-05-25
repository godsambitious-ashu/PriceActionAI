# app.py – production-ready with proxy support, secure cookies, HSTS, and full routes
import os
import logging
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

from stock_data.data_fetcher import DataFetcher
from stock_data.plotter import Plotter
from stock_data.demand_zone_manager import DemandZoneManager
from stock_data.gpt_client import GPTClient
from datetime import datetime
import requests  # Added for Flowise API calls

# ──── Load secrets from environment (must-have) ──────────────────────────────
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("FLASK_SECRET_KEY environment variable not set")

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logging.warning("OPENAI_API_KEY not set; GPT functionality will be disabled.")

FLOWISE_API_URL = os.environ.get(
    'FLOWISE_API_URL',
    'http://localhost:3000/api/v1/prediction/5ddc4cb7-3544-4bce-8068-34e28f12529d'
)

# ──── Flask app setup ───────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Trust proxy headers (ensure request.is_secure, url_for _external reflect HTTPS)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Apply security headers and HSTS only in production environment
if app.config.get('ENV') == 'production':
    try:
        from flask_talisman import Talisman
        Talisman(app,
                 force_https=True,
                 strict_transport_security=True,
                 strict_transport_security_max_age=31536000,
                 strict_transport_security_include_subdomains=True)
    except ImportError:
        logging.warning("Flask-Talisman not installed; skipping security headers.")

# Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session/'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
# Secure cookie flags
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
Session(app)

# Logging configuration
log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s %(levelname)s:%(message)s')

# AI & Flowise flags
HARDCODED_INTERVALS = ['3mo', '1mo', '1wk', '1d']
ENABLE_GPT = bool(OPENAI_API_KEY)
USE_FLOWISE = os.environ.get('USE_FLOWISE', 'False').lower() in ('true', '1')

# Initialize GPT client
gpt_client = None
if ENABLE_GPT:
    try:
        gpt_client = GPTClient(api_key=OPENAI_API_KEY)
        logging.debug("GPTClient initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize GPTClient: {e}")

# Stock codes list
MULTI_STOCK_CODES = [
    'NIFTY50', 'BANKNIFTY', 'NIFTYAUTO', 'NIFTYMETAL',
    'NIFTY FMCG', 'NIFTY PHARMA', 'NIFTY IT', 'NIFTY ENERGY',
    'NIFTY MEDIA', 'NIFTY REALTY', 'NIFTY PSU BANK'
]

# Helper: Call Flowise
def call_flowise(query, zones):
    zones_context = ''.join(f"{k}: {v}\n" for k, v in zones.items())
    payload = {"question": f"{query}\n{zones_context}"}
    try:
        response = requests.post(FLOWISE_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get('answer') or data.get('text', '')
    except Exception as e:
        logging.error(f"Error calling Flowise API: {e}")
        return "Error calling Flowise API."

# Helper: unified AI call
def call_ai(query, zones):
    if USE_FLOWISE:
        return call_flowise(query, zones)
    if ENABLE_GPT and gpt_client:
        return gpt_client.call_gpt(query, zones)
    return "AI functionality is disabled."

# Process multi-stock AI replies
def process_multi_stock_gpt_replies(period='2y'):
    replies = {}
    for code in MULTI_STOCK_CODES:
        try:
            dz = DemandZoneManager(code)
            (charts, dz_info, sz_info, adz, asz,
             monthly_zones, daily_zones,
             price, fresh1d, wk_zones) = dz.process_all_intervals(HARDCODED_INTERVALS, period)
            if USE_FLOWISE or (ENABLE_GPT and gpt_client):
                zones = gpt_client.prepare_zones(
                    monthly_zones, fresh1d, price, wk_zones,
                    f"Stock Data for {code}"
                )
                reply = call_ai(f"The current market price of {code} is {price}.", {'main': zones})
            else:
                reply = "AI functionality is disabled."
            replies[code] = reply
        except Exception as e:
            logging.error(f"Error processing stock {code}: {e}")
            replies[code] = f"Error processing stock {code}."
    return replies

# ──── Routes ───────────────────────────────────────────────────────────────
@app.route('/user_info', methods=['GET', 'POST'])
def user_info():
    if request.method == 'POST':
        session['name'] = request.form.get('name')
        session['email'] = request.form.get('email')
        logging.debug(f"User Info Submitted: {session['name']}, {session['email']}")
        session.setdefault('chat_history', [])
        if (USE_FLOWISE or (ENABLE_GPT and gpt_client)) and 'multi_stock' not in session:
            session['multi_stock'] = process_multi_stock_gpt_replies()
        return redirect(url_for('index'))
    return render_template('user_info.html')

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    return jsonify({'chat_history': session.get('chat_history', [])})

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    session['chat_history'] = []
    logging.debug("Chat history cleared.")
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'name' not in session or 'email' not in session:
        return redirect(url_for('user_info'))
    name, email = session['name'], session['email']
    if request.method == 'POST':
        stock_code = request.form['stock_code'].strip().upper()
        period = request.form['period']
        prev = session.get('current_stock')
        if prev and prev != stock_code:
            session['chat_history'] = []
        dz = DemandZoneManager(stock_code)
        index_code = dz.get_stock_codes_to_process(stock_code)
        (main_charts, main_dz, main_sz, main_adz, main_asz,
         main_monthly, main_daily, main_price,
         main_fresh, main_wk) = dz.process_all_intervals(HARDCODED_INTERVALS, period)
        index_data = None
        if index_code:
            dz2 = DemandZoneManager(index_code)
            index_data = dz2.process_all_intervals(HARDCODED_INTERVALS, period)
        zones = {}
        ai_answer = None
        if USE_FLOWISE or (ENABLE_GPT and gpt_client):
            mz = gpt_client.prepare_zones(main_monthly, main_fresh, main_price, main_wk, "Main Stock Data")
            zones['main'] = mz
            if index_code:
                iz = gpt_client.prepare_zones(index_data[5], index_data[8], index_data[7], index_data[9], "Index Data")
                zones['index'] = iz
            ai_answer = call_ai(
                f"Price {main_price}." + (f" Index {index_code} price {index_data[7]}.") if index_code else "",
                zones
            )
            session['gpt_auto'] = ai_answer
        session['current_stock'] = stock_code
        session['gpt_dto'] = zones
        chat = session.get('chat_history')
        chat.append({
            'stock': stock_code,
            'time': datetime.utcnow().isoformat(),
            'query': f"Searched {stock_code} period {period}",
            'answer': ai_answer or ''
        })
        session['chat_history'] = chat
        return render_template(
            'index.html', charts=main_charts, demand_zones_info=main_dz,
            supply_zones_info=main_sz, name=name, email=email,
            chat_history=chat, gpt_auto_answer=ai_answer,
            index_code=index_code, index_data=index_data
        )
    return render_template(
        'index.html', charts=None, demand_zones_info=None,
        supply_zones_info=None, name=name, email=email,
        chat_history=session.get('chat_history', []),
        gpt_auto_answer=session.get('gpt_auto')
    )

@app.route('/send_message', methods=['POST'])
def send_message():
    if not (USE_FLOWISE or (ENABLE_GPT and gpt_client)):
        return jsonify({'error': 'AI disabled.'}), 403
    user_message = request.form.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Empty message.'}), 400
    ai_response = call_ai(user_message, session.get('gpt_dto', {}))
    return jsonify({'message': ai_response})

@app.route('/multi_stock', methods=['GET'])
def multi_stock():
    if 'name' not in session:
        return redirect(url_for('user_info'))
    replies = session.get('multi_stock') or process_multi_stock_gpt_replies()
    session['multi_stock'] = replies
    return render_template('multi_stock.html', gpt_replies=replies)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    logging.error(f"Internal server error: {e}")
    return render_template('500.html'), 500

# Local development fallback
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=app.config['DEBUG'])
