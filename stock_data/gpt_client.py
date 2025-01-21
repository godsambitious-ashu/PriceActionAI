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
            {
                "role": "system",
                "content": (
                    "You are a financial assistant specializing in analyzing stock data to recommend entry points based on demand zones. "
                    "Follow these guidelines strictly:\n"
                    "1. Only consider zones where 'zoneType' is 'demand'. If no such zones exist, do not provide a recommendation.\n"
                    "2. If multiple 1-day demand zones have similar prices, combine them into one zone.\n"
                    "3. Calculate the entry point as 2% above the highest point of the combined zone and the stop-loss as 2% below the lowest point.\n"
                    "4. Respond in plain, friendly English with a greeting and a clear final recommendation. "
                    "   Do not include technical details, calculations, or jargon.\n"
                    "5. If the user message contains technical details, ignore those details and only use the final computed values for your recommendation."
                )
            },
            {"role": "user", "content": f"{user_query}"},
            {"role": "user", "content": f"Here is the zones data:\n{demand_zones_combined_json}"},
            {"role": "user", "content": "Please provide the analysis with the entry point and stop-loss calculation as per the instructions."},
        ]
        


        for msg in messages:
            if not isinstance(msg['content'], str):
                return "An error occurred while preparing the GPT request."
        
        logging.info("Sending GPT request with messages: %s", messages)

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            gpt_answer = completion.choices[0].message.content.strip()
            return gpt_answer
        except Exception as e:
            return f"Sorry, there was an error processing your request: {e}"

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
    
    def prepare_zones(self, monthly_fresh_zones, daily_all_zones, current_market_price):
        """
        Combines 1mo fresh zones with 1d ALL zones that fall within the 1mo proximal-distal range.
        Removes demand zones whose distal line is greater than the current market price.
        Allows daily zones whose first date is in the month of the monthly zone's first candle 
        or in the month of the monthly zone's second candle.
        
        Candle Patterns for Zones:
            - Pattern 1: 
                Candles list consists of exactly two items:
                [
                    {
                        'date': <First Date>,
                        'type': 'First (Red Exciting)',
                        ...
                    },
                    {
                        'date': <Second Date>,
                        'type': 'Second (Green Exciting)',
                        ...
                    }
                ]
            - Pattern 2:
                Candles list starts with a 'First' candle, followed by one or more 'Base' candles, 
                and ends with a 'Second' candle.
                Example:
                [
                    { 'date': <First Date>, 'type': 'First', ... },
                    { 'date': <Base Date 1>, 'type': 'Base', ... },
                    { 'date': <Base Date 2>, 'type': 'Base', ... },
                    ...,
                    { 'date': <Second Date>, 'type': 'Second', ... }
                ]
    
        Note:
            - The function uses the first two candles in the list to determine date ranges, 
              which is compatible with both patterns as long as at least two candles exist.
            - If additional handling based on candle types is needed, further logic can be added.
        
        Args:
            monthly_fresh_zones (list): List of fresh demand zone dicts for the 1mo interval.
            daily_all_zones (list or dict): List or dict of ALL demand zone dicts for the 1d interval.
            current_market_price (float): The current market price to filter demand zones.
    
        Returns:
            dict: A dictionary in the expected format, e.g.:
                  {
                      "1mo": [...],
                      "1d": [...]
                  }
                  or an empty dict if nothing matches.
        """
        logging.debug(f"daily 1d fresh zones: {daily_all_zones}")
        if not monthly_fresh_zones or not daily_all_zones:
            return {}
    
        if not isinstance(monthly_fresh_zones, list):
            return {}
    
        # Flatten nested structures in daily_all_zones if it's a dict
        if isinstance(daily_all_zones, dict):
            flattened = []
            for value in daily_all_zones.values():
                if isinstance(value, list):
                    flattened.extend(value)
                elif isinstance(value, dict):
                    for v in value.values():
                        if isinstance(v, list):
                            flattened.extend(v)
            daily_all_zones = flattened
        elif not isinstance(daily_all_zones, list):
            return {}
    
        # Filter monthly zones based on current market price for demand zones
        filtered_monthly = []
        for zone in monthly_fresh_zones:
            if not isinstance(zone, dict):
                continue
            if zone.get('zoneType') == "Demand":
                try:
                    if float(zone.get('distal', float('inf'))) > current_market_price:
                        continue
                except (TypeError, ValueError):
                    continue
            filtered_monthly.append(zone)
    
        result = {
            "1mo": filtered_monthly,
            "1d": []
        }
    
        for monthly_zone in filtered_monthly:
            if not isinstance(monthly_zone, dict):
                continue
            
            mo_proximal = monthly_zone.get('proximal')
            mo_distal = monthly_zone.get('distal')
            monthly_dates = monthly_zone.get("dates")
            monthly_candles = monthly_zone.get("candles", [])
    
            # Ensure monthly zone has at least two candles for reference
            if not monthly_candles or len(monthly_candles) < 2:
                continue
            
            # Get month/year for the first two monthly candles
            first_month_year = None
            second_month_year = None
            if monthly_candles[0].get("date"):
                first_month_year = (monthly_candles[0]["date"].month, monthly_candles[0]["date"].year)
            if monthly_candles[1].get("date"):
                second_month_year = (monthly_candles[1]["date"].month, monthly_candles[1]["date"].year)
    
            if mo_proximal is None or mo_distal is None:
                continue
            
            for daily_zone in daily_all_zones:
                if not isinstance(daily_zone, dict):
                    continue
                
                daily_prox = daily_zone.get('proximal')
                daily_dist = daily_zone.get('distal')
                daily_dates = daily_zone.get("dates")
                daily_candles = daily_zone.get("candles", [])
    
                # Ensure daily zone has at least two candles for comparison
                if not daily_candles or len(daily_candles) < 2:
                    continue
                
                # Check if daily zone's first date falls within allowed monthly months
                if daily_dates is not None and len(daily_dates) > 0 and first_month_year and second_month_year:
                    daily_month_year = (daily_dates[0].month, daily_dates[0].year)
                    # Allow daily if its month/year matches the first or second month of the monthly zone
                    if daily_month_year != first_month_year and daily_month_year != second_month_year:
                        continue
                    
                if daily_prox is None or daily_dist is None:
                    continue
                
                # Example modification to in_range check:
                try:
                    in_range = (int(daily_prox) <= int(mo_proximal)) and (int(daily_dist) >= int(mo_distal))
                except (TypeError, ValueError):
                    continue
                
                
                if not in_range:
                    continue
                
                monthly_first_date = monthly_candles[0].get("date")
                daily_first_date = daily_candles[0].get("date")  # Use first candle of daily zone
                monthly_last_date = monthly_candles[-1].get("date")

                # Lower bound: daily first date must be on/after monthly first date.
                # Upper bound: daily first date must be before the last monthly candle date.
                if not (monthly_first_date <= daily_first_date < monthly_last_date):
                    continue

                if daily_zone.get("zoneType") == "Demand":
                    try:
                        if float(daily_dist) > current_market_price:
                            continue
                    except (TypeError, ValueError):
                        continue
                    
                result["1d"].append(daily_zone)
    
        return result
    