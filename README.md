# 🧠 AI-Powered Stock Zone Identifier & Visualizer

This project is a production-ready Flask web application designed to analyze and visualize demand and supply zones on stock price charts using candlestick data. It integrates OpenAI's GPT API for AI-based insights and supports multi-stock visualization with responsive, interactive charts.

---

## 🚀 Features

* 📊 **Candlestick Chart Visualization** with demand and supply zone overlays (using Plotly)
* 🔍 **AI-Powered Trade Analysis** via GPT integration
* 📈 **Fresh vs. All Zone Toggle** for focused technical analysis
* ⏱️ **Multi-Timeframe Support** (1D, 1W, 1M, 3M, etc.)
* 📁 **User Input Handling** through a clean UI (via Flask + HTML templates)
* ⚙️ **Modular Python Backend** with utilities for fetching, plotting, and zone detection
* 💬 **Multi-stock GPT replies** displayed in a dedicated view
* 📦 Lightweight and deployable on platforms like Render or Northflank

---

## 🧹 Tech Stack

* **Backend:** Flask (Python 3.12)
* **Frontend:** HTML + CSS + JavaScript (Plotly.js for charts)
* **AI:** OpenAI GPT API
* **Data Handling:** `pandas`, `requests`
* **Deployment:** Linux-compatible, supports cloud deployment (Render, Northflank)

---

## 📁 Project Structure

```
🔹 app.py                         # Main Flask app entrypoint
🔹 data_fetcher.py               # Handles stock price fetching
🔹 candlestick_utils.py         # Candlestick data utilities
🔹 demand_zone_identifier.py    # Demand zone identification logic
🔹 supply_zone_identifier.py    # Supply zone identification logic
🔹 demand_zone_manager.py       # Merges, filters, and organizes zones
🔹 demand_zone_utils.py         # Helper functions for zone processing
🔹 gpt_client.py                # GPT API interaction wrapper
🔹 templates/
🔺┃🔹 index.html               # Main dashboard UI
   ┗🔹 user_info.html           # User data form
   ┗🔹 multi_stock.html         # Multi-stock GPT replies
🔹 static/
🔺┃🔹 css/styles.css           # Custom CSS
   ┗🔹 js/main.js               # Frontend JS logic
   ┗🔹 plotly.min.js            # Plotly charting library
🔹 stocks_config.py             # Stocks metadata/configuration
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

### 2. Install dependencies

Make sure you're using Python 3.12 and a virtual environment:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> *Note: Generate `requirements.txt` using `pip freeze > requirements.txt` if missing.*

### 3. Add your OpenAI API Key

Set your OpenAI API key securely using environment variables:

```bash
export OPENAI_API_KEY=your-key-here
```

Or include it in a `.env` file and load it using `python-dotenv`.

### 4. Run the Flask app

```bash
python app.py
```

Visit [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🧠 AI Usage

* The GPT model is used to generate trade-related insights.
* Prompts include candle pattern context, zone characteristics, and timeframe awareness.

---

## 📌 Deployment Notes

* The app is optimized for Linux servers with **1 vCPU and 2GB RAM**.
* Ensure your deployment platform supports long-running Flask apps (e.g., Render, Northflank).
* Use `gunicorn` for production:

```bash
pip install gunicorn
gunicorn app:app --bind 0.0.0.0:5000
```

---

## 📬 Contributing

PRs are welcome! For major changes, open an issue first to discuss the scope.

