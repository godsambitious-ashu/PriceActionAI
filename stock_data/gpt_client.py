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
            raise ValueError("OpenAI API key is required.")
        
        self.client = OpenAI(api_key=api_key)

    def call_gpt(self, user_query, demand_zones_combined):
        """
        Calls OpenAI's GPT API using the ChatCompletion endpoint.
        Returns the GPT response text.

        Args:
            user_query (str): The user's query string.
            demand_zones_fresh_dict (dict): Dictionary containing fresh demand zones data.

        Returns:
            str: GPT-generated analysis or error message.
        """
        try:
            demand_zones_combined_json = self.serialize_demand_zones(demand_zones_combined)
        except Exception as e:
            return f"Sorry, there was an error processing your data: {e}"

        messages = [
            {"role": "system", "content": "You are a financial assistant specializing in analyzing stock data and recommending entry points based on demand zones."},
            {"role": "user", "content": f"User Query: {user_query}"},
            {"role": "user", "content": f"Here are the demand zones (demand_zones_fresh):\n{demand_zones_combined_json}"},
            {"role": "user", "content": "Please provide the analysis with the entry point and stop-loss calculation as per the instructions."},
        ]

        for msg in messages:
            if not isinstance(msg['content'], str):
                return "An error occurred while preparing the GPT request."

        try:
            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=256,
                temperature=0.7
            )
            gpt_answer = completion.choices[0].message.content.strip()
            return gpt_answer
        except Exception as e:
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
                      "1mo": [...],
                      "1d": [...]
                  }
                  or an empty dict if nothing matches.
        """
    
        #logging.debug(f"monthly all zones: {monthly_fresh_zones}")
        #logging.debug(f"daily fresh zones: {daily_all_zones}")
    
        if not monthly_fresh_zones or not daily_all_zones:
            return {}
    
        if not isinstance(monthly_fresh_zones, list):
            return {}
    
        # Flatten nested structures in daily_all_zones if it's a dict
        if isinstance(daily_all_zones, dict):
            flattened = []
            for value in daily_all_zones.values():
                # If value is a list, extend flattened list
                if isinstance(value, list):
                    flattened.extend(value)
                # If nested dicts exist, further flatten if needed
                elif isinstance(value, dict):
                    flattened.extend(value.values() if isinstance(value.values(), list) else [])
            daily_all_zones = flattened
        elif not isinstance(daily_all_zones, list):
            return {}
    
        result = {
            "1mo": monthly_fresh_zones,
            "1d": []
        }
    
        for monthly_zone in monthly_fresh_zones:
            if not isinstance(monthly_zone, dict):
                continue
            
            mo_proximal = monthly_zone.get('proximal')
            mo_distal = monthly_zone.get('distal')
    
            if mo_proximal is None or mo_distal is None:
                continue
            
            for daily_zone in daily_all_zones:
                if not isinstance(daily_zone, dict):
                    continue
                
                daily_prox = daily_zone.get('proximal')
                daily_dist = daily_zone.get('distal')
    
                if daily_prox is None or daily_dist is None:
                    continue
                
                try:
                    in_range = (float(daily_prox) <= float(mo_proximal)) and (float(daily_dist) >= float(mo_distal))
                except (TypeError, ValueError):
                    continue
                
                if in_range:
                    result["1d"].append(daily_zone)
    
        return result
    def serialize_demand_zones(self, demand_zones_dict):
        """
        Recursively serialize the demand zones dictionary to ensure all components are JSON-serializable,
        excluding 'dates', 'zone_id', and 'candles' data. All float values are rounded to two decimals.
    
        Args:
            demand_zones_dict (dict): The original demand zones data.
    
        Returns:
            str: A JSON-formatted string of the serialized demand zones.
        """
        if not isinstance(demand_zones_dict, dict):
            return "{}"
    
        serialized = {}
        for key, value in demand_zones_dict.items():
            if isinstance(value, list):
                serialized_zones = []
                for zone in value:
                    if not isinstance(zone, dict):
                        continue
                    serialized_zone = {}
                    for zone_key, zone_value in zone.items():
                        # Skip unwanted keys at the zone level
                        if zone_key in ["dates", "zone_id", "candles"]:
                            continue
                        
                        if isinstance(zone_value, pd.DatetimeIndex):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S').tolist()
                        elif isinstance(zone_value, pd.Timestamp):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(zone_value, datetime):
                            serialized_zone[zone_key] = zone_value.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(zone_value, (np.float64, np.float32)):
                            # Round float values to two decimals
                            serialized_zone[zone_key] = round(float(zone_value), 2)
                        elif isinstance(zone_value, (np.int64, np.int32)):
                            serialized_zone[zone_key] = int(zone_value)
                        elif isinstance(zone_value, list):
                            serialized_list = []
                            for item in zone_value:
                                if isinstance(item, (np.float64, np.float32)):
                                    serialized_list.append(round(float(item), 2))
                                elif isinstance(item, (np.int64, np.int32)):
                                    serialized_list.append(int(item))
                                elif isinstance(item, datetime):
                                    serialized_list.append(item.strftime('%Y-%m-%d %H:%M:%S'))
                                else:
                                    serialized_list.append(item)
                            serialized_zone[zone_key] = serialized_list
                        else:
                            serialized_zone[zone_key] = zone_value
                    serialized_zones.append(serialized_zone)
                serialized[key] = serialized_zones
            else:
                if isinstance(value, pd.Timestamp):
                    serialized[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, datetime):
                    serialized[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, (np.float64, np.float32)):
                    serialized[key] = round(float(value), 2)
                elif isinstance(value, (np.int64, np.int32)):
                    serialized[key] = int(value)
                else:
                    serialized[key] = value
    
        try:
            serialized_json = json.dumps(serialized, indent=2)
        except (TypeError, Exception):
            return "{}"
    
        return serialized_json