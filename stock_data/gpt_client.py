# File: stock_data/gpt_client.py

import json
import logging
from openai import OpenAI
from datetime import datetime
import pandas as pd
import numpy as np

class GPTClient:
    def __init__(self, api_key):
        """
        Initializes the GPTClient with the provided OpenAI API key.
        
        Args:
            api_key (str): Your OpenAI API key.
        """
        if not api_key:
            logging.error("OpenAI API key not provided.")
            raise ValueError("OpenAI API key is required.")
        
        self.client = OpenAI(api_key=api_key)
        logging.debug("GPTClient initialized successfully.")

    def call_gpt(self, user_query, demand_zones_fresh_dict):
        """
        Calls OpenAI's GPT API using the ChatCompletion endpoint.
        Returns the GPT response text.

        Args:
            user_query (str): The user's query string.
            demand_zones_fresh_dict (dict): Dictionary containing fresh demand zones data.

        Returns:
            str: GPT-generated analysis or error message.
        """
        # Serialize demand_zones_fresh_dict to a JSON-serializable format
        try:
            serialized_dict = self.serialize_demand_zones(demand_zones_fresh_dict)
            logging.debug(f"Serialized dict: {serialized_dict}")
            demand_zones_fresh_json = json.dumps(serialized_dict, indent=2)
            logging.debug("demand_zones_fresh_dict serialized successfully.")
        except Exception as e:
            logging.error(f"Serialization error: {e}")
            return f"Sorry, there was an error processing your data: {e}"

        # Log the type to ensure it's a string
        logging.debug(f"demand_zones_fresh_json type: {type(demand_zones_fresh_json)}")

        # Compose the messages for the ChatCompletion API
        messages = [
            {"role": "system", "content": "You are a financial assistant specializing in analyzing stock data."},
            {"role": "user", "content": f"User Query: {user_query}"},
            {"role": "user", "content": f"Here are the fresh demand zones (demand_zones_fresh):\n{demand_zones_fresh_json}"},
            {"role": "user", "content": "Please provide your analysis based on the provided data."},
        ]

        # Verify that all message contents are strings
        for msg in messages:
            if not isinstance(msg['content'], str):
                logging.error(f"Message content is not a string: {msg['content']}")
                return "An error occurred while preparing the GPT request."

        try:
            # Call the ChatCompletion endpoint
            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Choose the desired model
                messages=messages,
                max_tokens=256,
                temperature=0.7
            )
            # Extract the assistant's response
            gpt_answer = completion.choices[0].message.content.strip()
            logging.debug("GPT API call successful.")
            return gpt_answer
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return f"Sorry, there was an error processing your request: {e}"

    def serialize_demand_zones(self, demand_zones_dict):
        """
        Recursively serialize the demand zones dictionary to ensure all components are JSON-serializable.
        
        Args:
            demand_zones_dict (dict): The original demand zones data.
        
        Returns:
            dict: A JSON-serializable version of the demand zones data.
        """
        if not isinstance(demand_zones_dict, dict):
            logging.warning("Input demand_zones_dict is not a dictionary.")
            return {}
        
        serialized = {}
        for key, value in demand_zones_dict.items():
            if isinstance(value, list):
                # Handle list of zones
                serialized_zones = []
                for zone in value:
                    serialized_zone = {}
                    for zone_key, zone_value in zone.items():
                        if isinstance(zone_value, pd.DatetimeIndex):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S').tolist()
                            logging.debug(f"Serialized pd.DatetimeIndex for key '{zone_key}'.")
                        elif isinstance(zone_value, pd.Timestamp):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S')
                            logging.debug(f"Serialized pd.Timestamp for key '{zone_key}'.")
                        elif isinstance(zone_value, datetime):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S')
                            logging.debug(f"Serialized datetime for key '{zone_key}'.")
                        elif isinstance(zone_value, (np.float64, np.float32)):
                            serialized_zone[zone_key] = float(zone_value)
                            logging.debug(f"Serialized numpy float for key '{zone_key}': {zone_value}")
                        elif isinstance(zone_value, (np.int64, np.int32)):
                            serialized_zone[zone_key] = int(zone_value)
                            logging.debug(f"Serialized numpy int for key '{zone_key}': {zone_value}")
                        elif isinstance(zone_value, list):
                            # Recursively serialize each item in the nested list
                            serialized_list = []
                            for item in zone_value:
                                if isinstance(item, dict):
                                    serialized_item = {}
                                    for sub_key, sub_value in item.items():
                                        if isinstance(sub_value, pd.Timestamp):
                                            serialized_item[sub_key] = sub_value.strftime('%Y-%m-%d %H:%M:%S')
                                            logging.debug(f"Serialized pd.Timestamp in list for sub_key '{sub_key}'.")
                                        elif isinstance(sub_value, datetime):
                                            serialized_item[sub_key] = sub_value.strftime('%Y-%m-%d %H:%M:%S')
                                            logging.debug(f"Serialized datetime in list for sub_key '{sub_key}'.")
                                        elif isinstance(sub_value, (np.float64, np.float32)):
                                            serialized_item[sub_key] = float(sub_value)
                                            logging.debug(f"Serialized numpy float in list for sub_key '{sub_key}': {sub_value}")
                                        elif isinstance(sub_value, (np.int64, np.int32)):
                                            serialized_item[sub_key] = int(sub_value)
                                            logging.debug(f"Serialized numpy int in list for sub_key '{sub_key}': {sub_value}")
                                        else:
                                            serialized_item[sub_key] = sub_value
                                            logging.debug(f"Unhandled type in list for sub_key '{sub_key}'. Converted to original value.")
                                    serialized_list.append(serialized_item)
                                else:
                                    # Handle non-dict items in the list
                                    if isinstance(item, (np.float64, np.float32)):
                                        serialized_list.append(float(item))
                                        logging.debug("Serialized numpy float in list.")
                                    elif isinstance(item, (np.int64, np.int32)):
                                        serialized_list.append(int(item))
                                        logging.debug("Serialized numpy int in list.")
                                    elif isinstance(item, datetime):
                                        serialized_list.append(item.strftime('%Y-%m-%d %H:%M:%S'))
                                        logging.debug("Serialized datetime in list.")
                                    else:
                                        serialized_list.append(item)
                                        logging.debug("Unhandled type in list. Appended original item.")
                            serialized_zone[zone_key] = serialized_list
                        else:
                            serialized_zone[zone_key] = zone_value
                            logging.debug(f"Unhandled type for key '{zone_key}'. Converted to original value.")
                    serialized_zones.append(serialized_zone)
                    logging.debug(f"Serialized zone: {serialized_zone}")
                serialized[key] = serialized_zones
                logging.debug(f"Serialized zones for key '{key}': {serialized_zones}")
            else:
                # Handle single values (e.g., current_market_price)
                if isinstance(value, pd.Timestamp):
                    serialized[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    logging.debug(f"Serialized pd.Timestamp for key '{key}'.")
                elif isinstance(value, datetime):
                    serialized[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    logging.debug(f"Serialized datetime for key '{key}'.")
                elif isinstance(value, (np.float64, np.float32)):
                    serialized[key] = float(value)
                    logging.debug(f"Serialized numpy float for key '{key}': {value}")
                elif isinstance(value, (np.int64, np.int32)):
                    serialized[key] = int(value)
                    logging.debug(f"Serialized numpy int for key '{key}': {value}")
                else:
                    # Handle other possible types or leave as-is
                    serialized[key] = value
                    logging.debug(f"Unhandled type for key '{key}'. Converted to original value.")
        return serialized