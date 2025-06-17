# app.py – production-ready WSGI entrypoint
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
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
# Secure cookie flags
if app.config.get('ENV') == 'production':
    # in production (behind TLS) set Secure, HttpOnly, SameSite=Strict
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
    )
else:
    # in development (HTTP) disable Secure so the browser will send it
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE=None,
    )
# ────────────────────────────────────────────────────────────────────────
Session(app)

# Logging configuration – always DEBUG to console during development
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
app.logger.setLevel(logging.DEBUG)

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
    'NIFTY50', 'BANKNIFTY', 'NIFTYAUTO', 'NIFTY PSU BANK'
]

def call_flowise(query, zones):
    zones_context = ''.join(f"{k}: {v}\n" for k, v in zones.items())
    payload = {"question": f"{query}\n{zones_context}"}

    # Log the outgoing request
    logging.debug(f"Calling Flowise URL: {FLOWISE_API_URL}")
    logging.debug(f"Flowise request payload: {payload}")

    try:
        response = requests.post(FLOWISE_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        logging.debug(f"Flowise raw response JSON: {data}")

        # Try common fields in order
        for key in ('answer', 'text', 'prediction', 'data', 'result'):
            if key in data and data[key]:
                logging.debug(f"Flowise using field `{key}` with value: {data[key]}")
                return data[key]
        # If nothing found, stringify entire response
        return str(data)
    except Exception as e:
        logging.error(f"Error calling Flowise API: {e}")
        return "Error calling Flowise API."

def call_ai(query, zones):
    if USE_FLOWISE:
        return call_flowise(query, zones)
    if not (ENABLE_GPT and gpt_client):
        return "AI functionality is disabled."
    try:
        return gpt_client.call_gpt(query, zones)
    except Exception as e:
        app.logger.error(f"GPT failed: {e}")
        return "AI temporarily unavailable."


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

        # Main stock data
        dz = DemandZoneManager(stock_code)
        (main_charts, main_dz, main_sz, main_adz, main_asz,
         main_monthly, main_daily, main_price,
         main_fresh, main_wk) = dz.process_all_intervals(HARDCODED_INTERVALS, period)

        # Index stock data (for toggle)
        index_charts = None
        index_code = dz.get_stock_codes_to_process(stock_code)
        if index_code:
            dz2 = DemandZoneManager(index_code)
            (idx_charts, idx_dz, idx_sz, idx_adz, idx_asz,
             idx_monthly, idx_daily, idx_price,
             idx_fresh, idx_wk) = dz2.process_all_intervals(HARDCODED_INTERVALS, period)
            index_charts = idx_charts

        # AI zones & reply
        zones = {}
        ai_answer = None
        if USE_FLOWISE or (ENABLE_GPT and gpt_client):
            mz = gpt_client.prepare_zones(main_monthly, main_fresh, main_price, main_wk, "Main Stock Data")
            zones['main'] = mz
            if index_charts:
                iz = gpt_client.prepare_zones(idx_monthly, idx_fresh, idx_price, idx_wk, "Index Data")
                zones['index'] = iz
            ai_answer = call_ai(
                f"Price {main_price}." + (f" Index {index_code} price {idx_price}.") if index_charts else "",
                zones
            )
            session['gpt_auto'] = ai_answer

        # Save session context
        session['current_stock'] = stock_code
        session['gpt_dto'] = zones
        chat = session.setdefault('chat_history', [])
        chat.append({
            'stock': stock_code,
            'time': datetime.utcnow().isoformat(),
            'query': f"Searched {stock_code} period {period}",
            'gpt_answer': ai_answer or ''
        })
        session['chat_history'] = chat

        return render_template(
            'index.html',
            charts=main_charts,
            index_charts=index_charts,
            demand_zones_info=main_dz,
            supply_zones_info=main_sz,
            name=name,
            email=email,
            chat_history=chat,
            gpt_auto_answer=ai_answer,
            index_code=index_code
        )

    # GET
    return render_template(
        'index.html',
        charts=None,
        index_charts=None,
        demand_zones_info=None,
        supply_zones_info=None,
        name=name,
        email=email,
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

# Expose for WSGI servers (Gunicorn, uWSGI, mod_wsgi…)
application = app

# Local development runner (do NOT use this in prod)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
