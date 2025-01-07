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
            demand_zones_fresh_json = self.serialize_demand_zones(demand_zones_fresh_dict)
            logging.debug("demand_zones_fresh_dict serialized successfully.")
        except Exception as e:
            logging.error(f"Serialization error: {e}")
            return f"Sorry, there was an error processing your data: {e}"

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

    def prepare_zones(self, monthly_fresh_zones, daily_all_zones):
        """
        Combines 1mo fresh zones with 1d ALL zones that fall within the 1mo proximal-distal range.
    
        Args:
            monthly_fresh_zones (list): List of fresh demand zone dicts for the 1mo interval.
            daily_all_zones (list or dict): List or dict of ALL demand zone dicts for the 1d interval.
    
        Returns:
            dict: A dictionary in the expected format, e.g.:
                  {
                      "1mo": [...],  # Fresh monthly zones
                      "1d": [...]    # Only those 1d zones that fall within the monthly range
                  }
                  or an empty dict if nothing matches.
        """
        logging.debug("Entering prepare_zones method.")
    
        # Handle empty inputs
        if not monthly_fresh_zones or not daily_all_zones:
            logging.debug("One or both zone lists are empty. Returning empty dictionary.")
            return {}
    
        # Ensure monthly_fresh_zones is a list
        if not isinstance(monthly_fresh_zones, list):
            logging.error(f"Expected monthly_fresh_zones to be a list, got {type(monthly_fresh_zones)}.")
            return {}
    
        # Convert daily_all_zones to list if it's a dict
        if isinstance(daily_all_zones, dict):
            logging.debug("Converting daily_all_zones from dict to list.")
            daily_all_zones = list(daily_all_zones.values())
        elif not isinstance(daily_all_zones, list):
            logging.error(f"Expected daily_all_zones to be a list or dict, got {type(daily_all_zones)}.")
            return {}
    
        result = {
            "1mo": monthly_fresh_zones,
            "1d": []
        }
    
        for idx, monthly_zone in enumerate(monthly_fresh_zones):
            if not isinstance(monthly_zone, dict):
                logging.error(f"Monthly zone at index {idx} is not a dictionary: {monthly_zone}")
                continue
            
            mo_proximal = monthly_zone.get('proximal')
            mo_distal = monthly_zone.get('distal')
    
            if mo_proximal is None or mo_distal is None:
                logging.warning(f"Monthly zone at index {idx} missing 'proximal' or 'distal': {monthly_zone}")
                continue  # Skip zones with missing data
            
            logging.debug(f"Processing monthly zone {idx}: proximal={mo_proximal}, distal={mo_distal}")
    
            for daily_idx, daily_zone in enumerate(daily_all_zones):
                if not isinstance(daily_zone, dict):
                    logging.error(f"Daily zone at index {daily_idx} is not a dictionary: {daily_zone}")
                    continue
                
                daily_prox = daily_zone.get('proximal')
                daily_dist = daily_zone.get('distal')
    
                if daily_prox is None or daily_dist is None:
                    logging.warning(f"Daily zone at index {daily_idx} missing 'proximal' or 'distal': {daily_zone}")
                    continue  # Skip zones with missing data
                
                logging.debug(f"Comparing daily zone {daily_idx}: proximal={daily_prox}, distal={daily_dist} with monthly zone {idx}")
    
                # Adjust logic based on how proximal and distal are defined
                # Assuming proximal is the higher price and distal is the lower price
                # So, daily_prox <= mo_proximal and daily_dist >= mo_distal
                try:
                    in_range = (float(daily_prox) <= float(mo_proximal)) and (float(daily_dist) >= float(mo_distal))
                except (TypeError, ValueError) as e:
                    logging.error(f"Error converting proximal/distal to float for zones: {e}")
                    continue
                
                if in_range:
                    result["1d"].append(daily_zone)
                    logging.debug(f"Daily zone {daily_idx} is within monthly zone {idx}. Added to result.")
    
        logging.debug(f"prepare_zones final result: {result}")
        return result

    def serialize_demand_zones(self, demand_zones_dict):
        """
        Recursively serialize the demand zones dictionary to ensure all components are JSON-serializable.

        Args:
            demand_zones_dict (dict): The original demand zones data.

        Returns:
            str: A JSON-formatted string of the serialized demand zones.
        """
        logging.debug("Entering serialize_demand_zones method.")
        if not isinstance(demand_zones_dict, dict):
            logging.warning(f"Input demand_zones_dict is not a dictionary. Type received: {type(demand_zones_dict)}. Returning empty JSON.")
            return "{}"

        serialized = {}
        for key, value in demand_zones_dict.items():
            logging.debug(f"Serializing key '{key}' with value: {value}")
            if isinstance(value, list):
                serialized_zones = []
                for zone_idx, zone in enumerate(value):
                    if not isinstance(zone, dict):
                        logging.error(f"Zone at index {zone_idx} under key '{key}' is not a dictionary: {zone}")
                        continue
                    serialized_zone = {}
                    for zone_key, zone_value in zone.items():
                        if isinstance(zone_value, pd.DatetimeIndex):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S').tolist()
                            logging.debug(f"Serialized pd.DatetimeIndex for key '{zone_key}': {serialized_zone[zone_key]}")
                        elif isinstance(zone_value, pd.Timestamp):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S')
                            logging.debug(f"Serialized pd.Timestamp for key '{zone_key}': {serialized_zone[zone_key]}")
                        elif isinstance(zone_value, datetime):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S')
                            logging.debug(f"Serialized datetime for key '{zone_key}': {serialized_zone[zone_key]}")
                        elif isinstance(zone_value, (np.float64, np.float32)):
                            serialized_zone[zone_key] = float(zone_value)
                            logging.debug(f"Serialized numpy float for key '{zone_key}': {serialized_zone[zone_key]}")
                        elif isinstance(zone_value, (np.int64, np.int32)):
                            serialized_zone[zone_key] = int(zone_value)
                            logging.debug(f"Serialized numpy int for key '{zone_key}': {serialized_zone[zone_key]}")
                        elif isinstance(zone_value, list):
                            # Recursively serialize each item in the nested list
                            serialized_list = []
                            for item_idx, item in enumerate(zone_value):
                                if isinstance(item, dict):
                                    serialized_item = {}
                                    for sub_key, sub_value in item.items():
                                        if isinstance(sub_value, pd.Timestamp):
                                            serialized_item[sub_key] = sub_value.strftime('%Y-%m-%d %H:%M:%S')
                                            logging.debug(f"Serialized pd.Timestamp in list for sub_key '{sub_key}': {serialized_item[sub_key]}")
                                        elif isinstance(sub_value, datetime):
                                            serialized_item[sub_key] = sub_value.strftime('%Y-%m-%d %H:%M:%S')
                                            logging.debug(f"Serialized datetime in list for sub_key '{sub_key}': {serialized_item[sub_key]}")
                                        elif isinstance(sub_value, (np.float64, np.float32)):
                                            serialized_item[sub_key] = float(sub_value)
                                            logging.debug(f"Serialized numpy float in list for sub_key '{sub_key}': {serialized_item[sub_key]}")
                                        elif isinstance(sub_value, (np.int64, np.int32)):
                                            serialized_item[sub_key] = int(sub_value)
                                            logging.debug(f"Serialized numpy int in list for sub_key '{sub_key}': {serialized_item[sub_key]}")
                                        else:
                                            serialized_item[sub_key] = sub_value
                                            logging.debug(f"Unhandled type in list for sub_key '{sub_key}'. Converted to original value: {serialized_item[sub_key]}")
                                    serialized_list.append(serialized_item)
                                    logging.debug(f"Serialized dict item at index {item_idx} in list for key '{zone_key}': {serialized_item}")
                                else:
                                    # Handle non-dict items in the list
                                    if isinstance(item, (np.float64, np.float32)):
                                        serialized_list.append(float(item))
                                        logging.debug(f"Serialized numpy float in list item {item_idx}: {item}")
                                    elif isinstance(item, (np.int64, np.int32)):
                                        serialized_list.append(int(item))
                                        logging.debug(f"Serialized numpy int in list item {item_idx}: {item}")
                                    elif isinstance(item, datetime):
                                        serialized_list.append(item.strftime('%Y-%m-%d %H:%M:%S'))
                                        logging.debug(f"Serialized datetime in list item {item_idx}: {serialized_list[-1]}")
                                    else:
                                        serialized_list.append(item)
                                        logging.debug(f"Unhandled type in list item {item_idx}. Appended original item: {item}")
                            serialized_zone[zone_key] = serialized_list
                            logging.debug(f"Serialized list for key '{zone_key}': {serialized_zone[zone_key]}")
                        else:
                            serialized_zone[zone_key] = zone_value
                            logging.debug(f"Unhandled type for key '{zone_key}'. Converted to original value: {zone_value}")
                    serialized_zones.append(serialized_zone)
                    logging.debug(f"Serialized zone at index {zone_idx} under key '{key}': {serialized_zone}")
                serialized[key] = serialized_zones
                logging.debug(f"Serialized zones for key '{key}': {serialized_zones}")
            else:
                # Handle single values (e.g., current_market_price)
                if isinstance(value, pd.Timestamp):
                    serialized[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    logging.debug(f"Serialized pd.Timestamp for key '{key}': {serialized[key]}")
                elif isinstance(value, datetime):
                    serialized[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    logging.debug(f"Serialized datetime for key '{key}': {serialized[key]}")
                elif isinstance(value, (np.float64, np.float32)):
                    serialized[key] = float(value)
                    logging.debug(f"Serialized numpy float for key '{key}': {serialized[key]}")
                elif isinstance(value, (np.int64, np.int32)):
                    serialized[key] = int(value)
                    logging.debug(f"Serialized numpy int for key '{key}': {serialized[key]}")
                else:
                    # Handle other possible types or leave as-is
                    serialized[key] = value
                    logging.debug(f"Unhandled type for key '{key}'. Converted to original value: {value}")
        # Convert the entire serialized dictionary to a JSON string
        try:
            serialized_json = json.dumps(serialized, indent=2)
            logging.debug("Entire demand_zones_dict serialized to JSON successfully.")
        except TypeError as te:
            logging.error(f"TypeError during JSON serialization: {te}")
            return "{}"
        except Exception as e:
            logging.error(f"Unexpected error during JSON serialization: {e}")
            return "{}"

        return serialized_json