import yfinance as yf
import pandas as pd
import logging

class DataFetcher:
    @staticmethod
    def fetch_stock_data(stock_code, interval='1d', period='1y'):
        logging.debug(f"Fetching data for {stock_code} from Yahoo Finance with interval {interval} and period {period}")
        ticker = f"{stock_code}.NS"
        data = yf.Ticker(ticker).history(period=period, interval=interval)
        
        if not data.empty:
            logging.debug("Data fetched successfully")
            return data
        else:
            logging.error(f"Failed to fetch data for {stock_code}")
            raise ValueError(f"Failed to fetch data for {stock_code}")

# Example usage:
# df = DataFetcher.fetch_stock_data('RELIANCE', period='1mo')
