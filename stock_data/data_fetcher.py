import yfinance as yf
import pandas as pd
import logging

class DataFetcher:
    @staticmethod
    def fetch_stock_data(stock_code, interval='1d', period='1y'):
        # Mapping for known indices
        index_mapping = {
            "NIFTY50": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
            "NIFTYAUTO": "^CNXAUTO",
            "NIFTYMETAL": "^CNXMETAL",
            "NIFTY FMCG": "^CNXFMCG",
            "NIFTY PHARMA": "^CNXPHARMA",
            "NIFTY IT": "^CNXIT",
            "NIFTY ENERGY": "^CNXENERGY",
            "NIFTY MEDIA": "^CNXMEDIA",
            "NIFTY REALTY": "^CNXREALTY",
            "NIFTY PSU BANK": "^CNXPSUBANK"
            # Add more as needed…
        }

        # Determine the correct ticker symbol
        if stock_code.upper() in index_mapping:
            ticker_symbol = index_mapping[stock_code.upper()]
        else:
            ticker_symbol = f"{stock_code}.NS"

        logging.debug(f"Fetching data for {ticker_symbol} from Yahoo Finance with interval {interval} and period {period}")
        data = yf.Ticker(ticker_symbol).history(period=period, interval=interval)

        if not data.empty:
            logging.debug("Data fetched successfully")
            return data
        else:
            logging.error(f"Failed to fetch data for {stock_code}")
            raise ValueError(f"Failed to fetch data for {stock_code}")

# Example usage:
# For a stock:
# df_stock = DataFetcher.fetch_stock_data('RELIANCE', period='1mo')

# For an index:
# df_nifty = DataFetcher.fetch_stock_data('NIFTY50', period='1mo')
# df_banknifty = DataFetcher.fetch_stock_data('BANKNIFTY', period='1mo')