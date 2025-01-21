import json
import logging
from openai import OpenAI
from datetime import datetime
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class GPTClient:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self.client = OpenAI(api_key=api_key)

    def call_gpt(self, user_query, demand_zones_combined):
        # Log the type before serialization
        logging.debug("Type before calling serialize_demand_zones: %s", type(demand_zones_combined))
        logging.debug("Original demand_zones_combined: %s", demand_zones_combined)
        
        try:
            demand_zones_combined_json = self.serialize_demand_zones(demand_zones_combined)
            logging.debug("Serialized zones JSON: %s", demand_zones_combined_json)
        except Exception as e:
            logging.error(f"Serialization error in call_gpt: {e}")
            return f"Sorry, there was an error processing your data: {e}"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a financial assistant specializing in analyzing stock data to recommend entry points based on demand zones. "
                    "Follow these guidelines strictly:\n"
                    "1. Only consider zones where 'zoneType' is 'demand'. If no such zones exist, do not provide a recommendation.\n"
                    "2. If multiple 1-day demand zones have similar prices, combine them into one zone.\n"
                    "4. You will first look at 1d as interval and if not found then 1wk as interval for finding entry in zonetype as demand\\n"
                    "5. Recommend the target as nearest lowest point of zoneType as supply from the current market price\n"
                    "5. Calculate the entry point as 2% above the highest point of the combined zone and the stop-loss as 2% below the lowest point.\n"
                    "6. Respond in plain, friendly English with a greeting and a clear final recommendation. "
                    "   Do not include technical details, calculations, or jargon.\n"
                    "7. If the user message contains technical details, ignore those details and only use the final computed values for your recommendation."
                )
            },
            {"role": "user", "content": f"{user_query}"},
            {"role": "user", "content": f"Here is the zones data:\n{demand_zones_combined_json}"},
            {"role": "user", "content": "Please provide the analysis with the entry point and stop-loss calculation as per the instructions."},
        ]

        for msg in messages:
            if not isinstance(msg['content'], str):
                logging.error("Non-string content found in message: %s", msg)
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
            logging.error(f"Error during GPT call: {e}")
            return f"Sorry, there was an error processing your request: {e}"

    def serialize_demand_zones(self, demand_zones_dict):
        # Check for non-dictionary input and log the type
        if not isinstance(demand_zones_dict, dict):
            logging.error(f"serialize_demand_zones expected dict but got type: {type(demand_zones_dict)}")
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
            logging.debug("Serialized dict before json.dumps: %s", serialized)
            serialized_json = json.dumps(serialized, indent=2)
        except (TypeError, Exception) as e:
            logging.error(f"Serialization error: {e}")
            return "{}"
        
        logging.debug("Successfully serialized JSON: %s", serialized_json)
        return serialized_json
    
    def prepare_zones(self, monthly_fresh_zones, daily_all_zones, current_market_price, wk_demand_zones):

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
    
        # Process daily zones with filtering logic
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
    
        if not result["1d"] and wk_demand_zones and isinstance(wk_demand_zones, list):
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
                
                for wk_zone in wk_demand_zones:
                    if not isinstance(wk_zone, dict):
                        continue
                    
                    wk_prox = wk_zone.get('proximal')
                    wk_dist = wk_zone.get('distal')
                    wk_dates = wk_zone.get("dates")
                    wk_candles = wk_zone.get("candles", [])

                    # Ensure weekly zone has at least two candles for comparison
                    if not wk_candles or len(wk_candles) < 2:
                        continue
                    
                    # Check if weekly zone's first date falls within allowed monthly months
                    if wk_dates is not None and len(wk_dates) > 0 and first_month_year and second_month_year:
                        wk_month_year = (wk_dates[0].month, wk_dates[0].year)
                        # Allow weekly if its month/year matches the first or second month of the monthly zone
                        if wk_month_year != first_month_year and wk_month_year != second_month_year:
                            continue
                        
                    if wk_prox is None or wk_dist is None:
                        continue
                    
                    try:
                        in_range = (int(wk_prox) <= int(mo_proximal)) and (int(wk_dist) >= int(mo_distal))
                    except (TypeError, ValueError):
                        continue
                    
                    if not in_range:
                        continue
                    
                    monthly_first_date = monthly_candles[0].get("date")
                    wk_first_date = wk_candles[0].get("date")  # Use first candle of weekly zone
                    monthly_last_date = monthly_candles[-1].get("date")

                    # Lower bound: weekly first date must be on/after monthly first date.
                    # Upper bound: weekly first date must be before the last monthly candle date.
                    if not (monthly_first_date <= wk_first_date < monthly_last_date):
                        continue
                    
                    # Additional new checks:

                    # a) Formation Within Last 2 Months
                    two_months_ago = datetime.now() - timedelta(days=60)  # Roughly 2 months ago
                    if wk_first_date < two_months_ago:
                        continue
                    
                    # b) Weekly zone formed below the current market price
                    try:
                        if float(wk_prox) > current_market_price:
                            continue
                    except (TypeError, ValueError):
                        continue
                    
                    # c) At least one weekly candle's low is less than the monthly zone's proximal
                    candle_low_below_proximal = False
                    for candle in wk_candles:
                        # Assuming each candle dict has a "low" field indicating its low price.
                        candle_low = candle.get("low")
                        if candle_low is not None and mo_proximal is not None:
                            try:
                                if float(candle_low) < float(mo_proximal):
                                    candle_low_below_proximal = True
                                    break
                            except (TypeError, ValueError):
                                continue
                    if not candle_low_below_proximal:
                        continue
                    
                    # Check zone type Demand condition as before
                    if wk_zone.get("zoneType") == "Demand":
                        try:
                            if float(wk_dist) > current_market_price:
                                continue
                        except (TypeError, ValueError):
                            continue
                        
                    result["1d"].append(wk_zone)

        return result
