import json
import logging
from openai import OpenAI
from datetime import datetime
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
import math

class GPTClient:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self.client = OpenAI(api_key=api_key)

    def call_gpt(self, user_query, zone_dto):
        
        try:
            zone_dto_json = self.serialize_demand_zones(zone_dto)
        except Exception as e:
            logging.error(f"Serialization error in call_gpt: {e}")
            return f"Sorry, there was an error processing your data: {e}"
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly and knowledgeable financial assistant specializing in stock analysis. "
                    "Your task is to recommend optimal entry points and target prices based on the provided demand zones data. "
                    "Please adhere to the following guidelines without directly referencing or revealing any technical details from the data:\n\n"
                    "1. Identify the main buying range by checking the '3mo_demand_zone' first; if that’s not available or is empty, use the '1mo_demand_zone'.\n\n"
                    "2. Emphasize this chosen demand zone as the primary buying zone in your response.\n\n"
                    "3. When 'entries' are provided, offer multiple entry points within this range along with their respective stop-loss levels. Vary your wording each time you provide these recommendations. For example:\n"
                    "   **Example Response:**\n"
                    "   This stock shows excellent promise—I’m spotting a **{trade_score} out of 6** opportunity with a buying range between 130.00 and 120.00. Within this zone, I recommend entry points at 142.08 (Stop Loss: 137.00) and 145.50 (Stop Loss: 139.00). Set your target at 180.27. Happy investing!\n\n"
                    "4. If there are no 'entries' provided, please randomly choose one of the following friendly variations (do not always pick the first):\n"
                    "   Variation A: 'The stock is in a promising buying range, but I’m not seeing the ideal entry points at the moment. It might be best to wait for more price action.'\n"
                    "   Variation B: 'Although the stock is positioned within a solid buying range, there are currently no optimal entry points. Consider holding off until clearer opportunities arise.'\n"
                    "   Variation C: 'While the stock sits in a favorable buying range, the perfect entry points are not apparent right now. Keep an eye on price movements for the best entry signals.'\n\n"
                    "5. In cases where 'data_type' is 'Index Data':\n"
                    "   a. If there are any 'entries' or available demand zones, append one of these supportive comments (choose one at random):\n"
                    "      - 'I also observe that the sector is moving into a potential buying range, which adds confidence to entering this stock.'\n"
                    "      - 'Additionally, the sector appears to be entering a buying range, which strengthens the case for a confident entry.'\n"
                    "      - 'Moreover, the sector’s shift into a buying range further supports a confident entry into this stock.'\n"
                    "   b. If both 'entries' are absent and all demand zones are empty, append one of these pro tips (again, choose one at random):\n"
                    "      - 'Pro tip: Consider reviewing the sector chart; it can be a valuable indicator if the sector supports the stock.'\n"
                    "      - 'Pro tip: Analyzing the sector chart might reveal additional support for the stock, which can be advantageous.'\n"
                    "      - 'Pro tip: A quick look at the sector chart could be beneficial, especially if it shows backing for the stock.'\n\n"
                    "6. If neither '3mo_demand_zone' nor '1mo_demand_zone' is provided, please randomly choose one of these variations:\n"
                    "   Variation A: 'At this point, I don't see a potential buying opportunity for this stock. There are many others that might have one—try a different one. Happy investing!'\n"
                    "   Variation B: 'Currently, it appears that this stock doesn't present a clear buying opportunity. Consider exploring other stocks for better prospects.'\n"
                    "   Variation C: 'It seems that the ideal buying conditions are not present for this stock right now. You might want to check out other stocks for more promising opportunities. Happy investing!'\n\n"
                    "7. Do not mention, reference, or summarize any of the specific zones data provided.\n\n"
                    "8. Keep your language clear, friendly, and free of technical jargon or calculations—focus solely on providing clear recommendations.\n\n"
                    "Important: For steps 4, 5a, 5b, and 6, ensure that you do not always pick the first option. Simulate a random selection each time so that your responses vary from one request to another."
                )
            },
            {
                "role": "user",
                "content": f"{user_query}"
            },
            {
                "role": "user",
                "content": (
                    f"Here is the zones data:\n{zone_dto_json}"
                )
            },
            {
                "role": "user",
                "content": (
                    "Please provide an analysis with the recommended entry points, stop-loss levels, and target price based on the above zones data."
                )
            },
        ]
        
        for msg in messages:
            if not isinstance(msg['content'], str):
                logging.error("Non-string content found in message: %s", msg)
                return "An error occurred while preparing the GPT request."
        
        logging.info("Sending GPT request with messages: %s", messages)
        return self.get_gpt_response(messages)

    def get_gpt_response(self, messages):
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=messages,
                max_tokens=800,
                temperature=0.4
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error during GPT call: {e}")
            return f"Sorry, there was an error processing your request: {e}"


    def serialize_demand_zones(self, demand_zones_dict):
        """
        Serializes the zone_dto to a JSON string with rounded float values.

        Parameters:
            demand_zones_dict (dict): The DTO dictionary to serialize. 
                Expected structure can include multiple zone categories, such as:
                {
                    "main": {
                        "3mo_demand_zone": "130-120",
                        "1mo_demand_zone": "159.94-137.0",
                        "entries": [
                            {"entry": 142.08, "stoploss": 137.0},
                            {"entry": 145.5, "stoploss": 139.0}
                        ],
                        "target": 180.27
                    },
                    "index": {
                        "3mo_demand_zone": "130-120",
                        "1mo_demand_zone": "159.94-137.0",
                        "entries": [
                            {"entry": 142.08, "stoploss": 137.0},
                            {"entry": 145.5, "stoploss": 139.0}
                        ],
                        "target": 180.27
                    }
                }

        Returns:
            str: A JSON-formatted string representing the DTO.
        """
        if not isinstance(demand_zones_dict, dict):
            return "{}"

        def round_floats(obj):
            if isinstance(obj, dict):
                return {k: round_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [round_floats(item) for item in obj]
            elif isinstance(obj, float):
                return round(obj, 2)
            elif isinstance(obj, (np.float64, np.float32)):
                return round(float(obj), 2)
            else:
                return obj

        rounded_dict = round_floats(demand_zones_dict)

        try:
            serialized_json = json.dumps(rounded_dict, indent=2)
        except (TypeError, Exception):
            return "{}"

        return serialized_json


    def prepare_zones(self, monthly_fresh_zones, daily_all_zones, current_market_price, wk_demand_zones, data_type):
        logging.debug(f"monthly fresh zones: {monthly_fresh_zones}")
        logging.debug(f"current market price is : {current_market_price}")

        # Early exit if required inputs are missing or not in expected format
        if not monthly_fresh_zones or not daily_all_zones:
            return {}

        if not isinstance(monthly_fresh_zones, list):
            return {}

        # Flatten nested structures in daily_all_zones if it's a dict
        if isinstance(daily_all_zones, dict):
            flattened = []
            for key, value in daily_all_zones.items():
                if isinstance(value, list):
                    flattened.extend(value)
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, list):
                            flattened.extend(sub_value)
            daily_all_zones = flattened
        elif not isinstance(daily_all_zones, list):
            return {}

        # Filter monthly zones based on 'zoneType' and 'distal' compared to current_market_price
        filtered_monthly = []
        for zone in monthly_fresh_zones:
            if not isinstance(zone, dict):
                continue
            if zone.get('zoneType') == "Demand":
                distal = zone.get('distal')
                try:
                    distal_value = float(distal)
                    if distal_value > current_market_price:
                        continue
                except (TypeError, ValueError):
                    continue
            filtered_monthly.append(zone)
        logging.debug(f"Filtered monthly zones: {filtered_monthly}")

        result = {
            "1mo": filtered_monthly,
            "1d": []
        }

        # Helper function to extract a single date from various formats
        def extract_single_date(date_obj, label):
            if isinstance(date_obj, pd.DatetimeIndex):
                return date_obj[0] if len(date_obj) > 0 else None
            elif isinstance(date_obj, list):
                return date_obj[0] if len(date_obj) > 0 else None
            elif isinstance(date_obj, pd.Timestamp):
                return date_obj
            else:
                return None

        # Iterate through each filtered monthly zone
        for monthly_zone in filtered_monthly:
            if not isinstance(monthly_zone, dict):
                continue
            
            mo_proximal = monthly_zone.get('proximal')
            mo_distal = monthly_zone.get('distal')
            monthly_candles = monthly_zone.get("candles", [])

            # Ensure monthly zone has at least two candles for reference
            if not monthly_candles or len(monthly_candles) < 2:
                continue
            
            # Extract month/year for the first two monthly candles
            first_month_year = None
            second_month_year = None
            first_candle_date = monthly_candles[0].get("date")
            second_candle_date = monthly_candles[1].get("date")

            if first_candle_date:
                first_month_year = (first_candle_date.month, first_candle_date.year)
            if second_candle_date:
                second_month_year = (second_candle_date.month, second_candle_date.year)

            if mo_proximal is None or mo_distal is None:
                continue
            
            # Iterate through each daily zone
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
                
                # Extract single dates using the helper function
                daily_first_date = extract_single_date(daily_candles[0].get("date"), "daily_first_date")
                monthly_first_date = extract_single_date(monthly_candles[0].get("date"), "monthly_first_date")
                monthly_last_date = extract_single_date(monthly_candles[-1].get("date"), "monthly_last_date")

                # Verify that all necessary dates were successfully extracted
                if not all([daily_first_date, monthly_first_date, monthly_last_date]):
                    continue
                
                # Check if the daily zone's first date falls within the allowed monthly months
                # Avoid ambiguous boolean check on daily_dates (DatetimeIndex) by checking None & length
                if daily_dates is not None and len(daily_dates) > 0 and first_month_year and second_month_year:
                    daily_dates_single = extract_single_date(daily_dates, "daily_dates")
                    if daily_dates_single:
                        daily_month_year = (daily_dates_single.month, daily_dates_single.year)
                        if daily_month_year not in [first_month_year, second_month_year]:

                            continue
                        
                # Verify proximal and distal values are present
                if daily_prox is None or daily_dist is None:
                    continue
                
                # Compare proximal and distal values as floats
                try:
                    mo_proximal_float = float(mo_proximal)
                    mo_distal_float = float(mo_distal)
                    daily_prox_float = float(daily_prox)
                    daily_dist_float = float(daily_dist)
                    in_range = (
                        daily_prox_float <= mo_proximal_float and
                        daily_dist_float >= mo_distal_float
                    )
                except (TypeError, ValueError) as e:
                    continue
                
                if not in_range:
                    continue
                
                # Compare dates to ensure daily_first_date is within the monthly date range
                try:
                    # Ensure all dates are pd.Timestamp objects
                    if not (
                        isinstance(monthly_first_date, pd.Timestamp) and
                        isinstance(daily_first_date, pd.Timestamp) and
                        isinstance(monthly_last_date, pd.Timestamp)
                    ):
                        continue
                    
                    # Perform the comparison: monthly_first_date <= daily_first_date < monthly_last_date
                    if not (monthly_first_date <= daily_first_date < monthly_last_date):
                        continue
                except Exception as e:
                    logging.error(f"Error comparing dates: {e}")
                    continue
                
                # Additional filter for Demand zones based on current_market_price
                if daily_zone.get("zoneType") == "Demand":
                    try:
                        daily_dist_value = float(daily_dist)
                        if daily_dist_value > current_market_price:

                            continue
                    except (TypeError, ValueError):
                        logging.error(f"Invalid distal value in daily zone: {daily_dist}")
                        continue
                    
                # Append the valid daily zone to the result
                logging.debug(f"Adding daily zone to result: {daily_zone}")
        
                result["1d"].append(daily_zone)
        logging.debug("Near weekly DZ method")
        # Handle weekly demand zones if daily zones are absent
        self.addWeeklyDzIfDailyAreAbsent(current_market_price, wk_demand_zones, filtered_monthly, result)

        # Retain only the nearest supply zone after processing all zones
        result = self.retain_nearest_supply_zone(result, current_market_price)

        # Build the final zones DTO (Data Transfer Object)
        dto = self.build_zones_dto(result, current_market_price, data_type)

        logging.debug(f"Final DTO: {dto}")
        return dto

    def addWeeklyDzIfDailyAreAbsent(
            self,
            current_market_price: float,
            wk_demand_zones: List[Dict[str, Any]],
            filtered_monthly: List[Dict[str, Any]],
            result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """
            Adds weekly demand zones to the result if daily demand zones are absent.
            After adding, retains only the nearest supply zone.

            Parameters:
            - current_market_price (float): The current market price.
            - wk_demand_zones (list): List of weekly demand zones.
            - filtered_monthly (list): List of filtered monthly zones.
            - result (dict): Existing result dictionary to be updated.

            Returns:
            - dict: Updated result dictionary.
            """
            # Check if '1d' key exists and is a non-empty list
            daily_zones_present = bool(result.get("1d"))

            if not daily_zones_present and wk_demand_zones and isinstance(wk_demand_zones, list):
                for monthly_zone in filtered_monthly:
                    if not isinstance(monthly_zone, dict):
                        continue
                    
                    mo_proximal = monthly_zone.get('proximal')
                    mo_distal = monthly_zone.get('distal')
                    monthly_candles = monthly_zone.get("candles", [])

                    # Ensure monthly zone has at least two candles for reference
                    if not monthly_candles or len(monthly_candles) < 2:
                        continue

                    # Get month/year for the first two monthly candles
                    first_month_year = None
                    second_month_year = None
                    if monthly_candles[0].get("date"):
                        first_month_year = (
                            monthly_candles[0]["date"].month,
                            monthly_candles[0]["date"].year
                        )
                    if monthly_candles[1].get("date"):
                        second_month_year = (
                            monthly_candles[1]["date"].month,
                            monthly_candles[1]["date"].year
                        )

                    if mo_proximal is None or mo_distal is None:
                        continue

                    for wk_zone in wk_demand_zones:
                        if not isinstance(wk_zone, dict):
                            continue
                        
                        wk_dist = wk_zone.get('distal')
                        wk_dates = wk_zone.get("dates")
                        wk_candles = wk_zone.get("candles", [])

                        # Ensure weekly zone has at least two candles for comparison
                        if not wk_candles or len(wk_candles) < 2:
                            continue

                        # Extract the first date in wk_dates
                        wk_first_date = None
                        if isinstance(wk_dates, pd.DatetimeIndex) and len(wk_dates) > 0:
                            wk_first_date = wk_dates[0]
                        elif isinstance(wk_dates, list) and len(wk_dates) > 0:
                            wk_first_date = wk_dates[0]
                        elif isinstance(wk_dates, pd.Timestamp):
                            wk_first_date = wk_dates
                        else:
                            continue

                        # Determine if the weekly zone's first date is within the monthly timeframe or within the last two months
                        within_monthly_timeframe = False
                        within_last_two_months = False

                        if isinstance(wk_first_date, (datetime, pd.Timestamp)):
                            # Ensure wk_first_date is timezone-aware
                            if wk_first_date.tzinfo is None or wk_first_date.tz is None:
                                # Optionally, localize to a default timezone or skip
                                # For example, assuming UTC:
                                wk_first_date = wk_first_date.replace(tzinfo=pd.Timestamp.now().tz)

                            # Get the timezone from wk_first_date
                            wk_timezone = wk_first_date.tz

                            # Define two_months_ago as timezone-aware
                            two_months_ago = pd.Timestamp.now(tz=wk_timezone) - pd.Timedelta(days=60)

                            # Check within monthly timeframe
                            monthly_first_date = monthly_candles[0].get("date")
                            monthly_last_date = monthly_candles[-1].get("date")

                            # Handle DatetimeIndex if necessary
                            if isinstance(monthly_first_date, pd.DatetimeIndex) and len(monthly_first_date) > 0:
                                monthly_first_date = monthly_first_date[0]
                            if isinstance(monthly_last_date, pd.DatetimeIndex) and len(monthly_last_date) > 0:
                                monthly_last_date = monthly_last_date[-1]

                            # Ensure monthly_first_date and monthly_last_date are timezone-aware
                            if isinstance(monthly_first_date, (datetime, pd.Timestamp)):
                                if monthly_first_date.tzinfo is None or monthly_first_date.tz is None:
                                    # Optionally, localize to the same timezone as wk_first_date
                                    monthly_first_date = monthly_first_date.replace(tzinfo=wk_timezone)
                            else:
                                continue

                            if isinstance(monthly_last_date, (datetime, pd.Timestamp)):
                                if monthly_last_date.tzinfo is None or monthly_last_date.tz is None:
                                    # Optionally, localize to the same timezone as wk_first_date
                                    monthly_last_date = monthly_last_date.replace(tzinfo=wk_timezone)
                            else:
                                continue

                            # Compare dates
                            if monthly_first_date <= wk_first_date < monthly_last_date:
                                within_monthly_timeframe = True

                            # Check within last two months
                            if wk_first_date >= two_months_ago:
                                within_last_two_months = True

                            # Proceed only if either condition is met
                            if not (within_monthly_timeframe or within_last_two_months):
                                continue
                        else:
                            continue

                        if wk_dist is None:
                            continue

                        try:
                            # New distal condition: monthly_distal < weekly_distal < monthly_proximal
                            if not (float(mo_distal) < float(wk_dist) < float(mo_proximal)):
                                continue
                        except (TypeError, ValueError):
                            logging.error(f"Invalid proximal/distal values in weekly zone: {wk_zone}")
                            continue

                        # c) At least one weekly candle's low is less than the monthly zone's proximal
                        candle_low_below_proximal = False
                        for candle in wk_candles:
                            candle_low = None
                            if "ohlc" in candle:
                                candle_low = candle["ohlc"].get("Low")
                            elif "low" in candle:
                                candle_low = candle["low"]
                            # If we still don't have a low, skip
                            if candle_low is None or mo_proximal is None:
                                continue
                            try:
                                if float(candle_low) < float(mo_proximal):
                                    candle_low_below_proximal = True
                                    break
                            except (TypeError, ValueError):
                                continue

                        if not candle_low_below_proximal:
                            continue

                        # Demand Zone Specific Condition:
                        if wk_zone.get("zoneType") == "Demand":
                            try:
                                if float(wk_dist) > current_market_price:
                                    continue
                            except (TypeError, ValueError):
                                logging.error(f"Invalid distal value in weekly zone: {wk_zone}")
                                continue

                        # Append the valid weekly zone to the result
                        result.setdefault("1d", []).append(wk_zone)
                        
            logging.debug("Exiting weekly DZ method")

            return result

    def retain_nearest_supply_zone(self, result: Dict[str, Any], current_market_price: float) -> Dict[str, Any]:
        """
        Retains only the supply zone with the proximal price nearest to the current market price.
        Removes all other supply zones from the result.

        Parameters:
        - result (dict): The dictionary containing demand and supply zones.
        - current_market_price (float): The current market price.

        Returns:
        - dict: The modified result with only the nearest supply zone retained.
        """
        try:
            logging.debug("Entering retain_nearest_supply_zone")
            logging.debug(f"Initial result: {result}")
            logging.debug(f"Current Market Price: {current_market_price}")

            if current_market_price is None:
                logging.warning("current_market_price is None. Returning result unchanged.")
                return result

            # Collect all zone_ids to check uniqueness
            all_zone_ids = []
            for interval, zones in result.items():
                if interval == 'current_market_price':
                    continue
                if isinstance(zones, list):
                    for zone in zones:
                        if isinstance(zone, dict):
                            zone_id = zone.get('zone_id')
                            if zone_id is not None:
                                all_zone_ids.append(zone_id)
            unique_zone_ids = set(all_zone_ids)
            is_zone_id_unique = len(all_zone_ids) == len(unique_zone_ids)
            logging.debug(f"Zone ID uniqueness: {is_zone_id_unique} (Unique Zone IDs: {unique_zone_ids})")

            # Iterate through each top-level interval (e.g., '1mo', '1d')
            for top_interval, zones in result.items():
                logging.debug(f"Processing top-level interval: '{top_interval}' with zones: {zones}")
                logging.debug(f"Type of zones for interval '{top_interval}': {type(zones)}")

                # Skip 'current_market_price' if it's stored in result
                if top_interval == 'current_market_price':
                    logging.debug(f"Skipping top-level interval '{top_interval}' as it is 'current_market_price'")
                    continue

                if not isinstance(zones, list):
                    logging.error(f"Expected list of zones for top-level interval '{top_interval}', got {type(zones)}. Skipping.")
                    continue

                # Group zones by their 'interval' field (sub-intervals)
                sub_interval_groups = {}
                for idx, zone in enumerate(zones):
                    logging.debug(f"Processing zone {idx} in top-level interval '{top_interval}': {zone}")
                    logging.debug(f"Type of zone: {type(zone)}")

                    if not isinstance(zone, dict):
                        logging.error(f"Expected zone to be a dict, got {type(zone)}. Skipping this zone.")
                        continue

                    zone_type = zone.get('zoneType')
                    sub_interval = zone.get('interval')

                    logging.debug(f"zoneType: {zone_type}, interval: {sub_interval}")

                    if zone_type != 'Supply':
                        logging.debug(f"Zone is not a Supply zone (zoneType='{zone_type}'). Skipping.")
                        continue

                    if sub_interval is None:
                        logging.warning(f"Supply zone missing 'interval' value: {zone}. Skipping.")
                        continue

                    if sub_interval not in sub_interval_groups:
                        sub_interval_groups[sub_interval] = []
                    sub_interval_groups[sub_interval].append(zone)

                logging.debug(f"Grouped Supply zones in top-level interval '{top_interval}' by sub-interval: {sub_interval_groups}")

                # Find the nearest Supply zone per sub-interval
                nearest_zones_per_sub_interval = {}
                for sub_interval, supply_zones in sub_interval_groups.items():
                    nearest_zone = None
                    min_distance_sub = float('inf')
                    logging.debug(f"Finding nearest Supply zone in sub-interval '{sub_interval}' with supply_zones: {supply_zones}")

                    for zone in supply_zones:
                        proximal = zone.get('proximal')
                        distal = zone.get('distal')
                        logging.debug(f"Evaluating Supply zone: proximal={proximal} (type: {type(proximal)}), distal={distal} (type: {type(distal)})")

                        if proximal is None or distal is None:
                            logging.warning(f"Supply zone missing 'proximal' or 'distal': {zone}. Skipping.")
                            continue

                        try:
                            proximal_float = float(proximal)
                            current_price_float = float(current_market_price)
                            distance = abs(proximal_float - current_price_float)
                            logging.debug(f"Calculated distance: {distance} between proximal {proximal_float} and current_market_price {current_price_float}")
                        except (TypeError, ValueError) as e:
                            logging.error(f"Error converting proximal or current_market_price to float: {e}. Skipping this zone.")
                            continue

                        if distance < min_distance_sub:
                            logging.debug(f"New nearest Supply zone in sub-interval '{sub_interval}': {zone} with distance {distance}")
                            min_distance_sub = distance
                            nearest_zone = zone

                    if nearest_zone:
                        nearest_zones_per_sub_interval[sub_interval] = nearest_zone
                        logging.debug(f"Nearest Supply zone in sub-interval '{sub_interval}': {nearest_zone} with distance {min_distance_sub}")
                    else:
                        logging.warning(f"No valid Supply zones found in sub-interval '{sub_interval}' within top-level interval '{top_interval}'.")

                # Retain only the nearest Supply zones per sub-interval
                for sub_interval, nearest_zone in nearest_zones_per_sub_interval.items():
                    logging.debug(f"Retaining nearest Supply zone for sub-interval '{sub_interval}': {nearest_zone}")

                # Create a new list of zones, keeping only the nearest Supply zones per sub-interval
                filtered_zones = list(nearest_zones_per_sub_interval.values())

                # Additionally, retain all non-Supply zones unchanged
                non_supply_zones = [z for z in zones if z.get('zoneType') != 'Supply']
                logging.debug(f"Non-Supply zones in top-level interval '{top_interval}': {non_supply_zones}")

                # Combine the nearest Supply zones and non-Supply zones
                try:
                    result[top_interval] = filtered_zones + non_supply_zones
                    logging.debug(f"Filtered zones for top-level interval '{top_interval}': {result[top_interval]}")
                except Exception as e:
                    logging.error(f"Error assigning filtered zones for top-level interval '{top_interval}': {e}")
                    logging.error(traceback.format_exc())

            logging.debug(f"Final result after retaining nearest Supply zones: {result}")
            logging.debug("Exiting retain_nearest_supply_zone")

            return result

        except Exception as e:
            logging.error(f"Error processing request: {e}")
            logging.error(traceback.format_exc())
            return result  # Or handle appropriately


    def build_zones_dto(self, zones_result: Dict[str, List[Dict]], current_market_price: float, data_type) -> Dict:
        """
        Constructs a Data Transfer Object (DTO) from the provided zones_result.
        """
        logging.debug("Entering build_zones_dto")
        logging.debug(f"zones_result: {zones_result}")
        logging.debug(f"current_market_price: {current_market_price}")
        logging.debug(f"data_type: {data_type}")

        # DTO structure to be returned
        dto = {
            "data_type": data_type,
            "3mo_demand_zone": None,
            "1mo_demand_zone": None,
            "entries": [],
            "target": None,
            "trade_score": 0
        }

        # 1) Find the closest (only one) 3mo Demand Zone
        three_mo_zones = self._get_zones(zones_result.get("1mo", []), zone_type="Demand", interval="3mo")
        logging.debug(f"three_mo_zones: {three_mo_zones}")
        closest_three_mo_zones = self._get_closest_zones(three_mo_zones, current_market_price, top_n=1)
        logging.debug(f"closest_three_mo_zones: {closest_three_mo_zones}")
        single_three_mo_zone = closest_three_mo_zones[0] if closest_three_mo_zones else None

        if single_three_mo_zone:
            proximal = single_three_mo_zone.get("proximal")
            distal = single_three_mo_zone.get("distal")
            logging.debug(f"3mo Demand Zone - proximal: {proximal}, distal: {distal}")

            if proximal is not None and distal is not None:
                if not isinstance(proximal, (float, int)) or not isinstance(distal, (float, int)):
                    logging.error(f"proximal or distal is not a scalar: proximal={proximal} (type: {type(proximal)}), distal={distal} (type: {type(distal)})")
                else:
                    try:
                        proximal = float(proximal)
                        distal = float(distal)
                        dto["3mo_demand_zone"] = f"{proximal:.2f}-{distal:.2f}"
                        logging.debug(f"Set 3mo_demand_zone: {dto['3mo_demand_zone']}")
                    except (TypeError, ValueError) as e:
                        logging.error(f"Error converting proximal/distal to float for 3mo Demand Zone: {e}")
            else:
                logging.warning("3mo Demand Zone found but proximal or distal is missing.")
        else:
            logging.warning("No 3mo Demand Zones found.")

        # 2) Find the closest (only one) 1mo Demand Zone
        one_mo_zones = self._get_zones(zones_result.get("1mo", []), zone_type="Demand", interval="1mo")
        logging.debug(f"one_mo_zones: {one_mo_zones}")
        closest_one_mo_zones = self._get_closest_zones(one_mo_zones, current_market_price, top_n=1)
        logging.debug(f"closest_one_mo_zones: {closest_one_mo_zones}")
        single_one_mo_zone = closest_one_mo_zones[0] if closest_one_mo_zones else None

        if single_one_mo_zone:
            proximal = single_one_mo_zone.get("proximal")
            distal = single_one_mo_zone.get("distal")
            logging.debug(f"1mo Demand Zone - proximal: {proximal}, distal: {distal}")

            if proximal is not None and distal is not None:
                if not isinstance(proximal, (float, int)) or not isinstance(distal, (float, int)):
                    logging.error(f"proximal or distal is not a scalar: proximal={proximal} (type: {type(proximal)}), distal={distal} (type: {type(distal)})")
                else:
                    try:
                        proximal = float(proximal)
                        distal = float(distal)
                        dto["1mo_demand_zone"] = f"{proximal:.2f}-{distal:.2f}"
                        logging.debug(f"Set 1mo_demand_zone: {dto['1mo_demand_zone']}")
                    except (TypeError, ValueError) as e:
                        logging.error(f"Error converting proximal/distal to float for 1mo Demand Zone: {e}")
            else:
                logging.warning("1mo Demand Zone found but proximal or distal is missing.")
        else:
            logging.warning("No 1mo Demand Zones found.")

        # Convert single 3mo and 1mo zone boundaries to floats if they exist (for comparison with daily zones)
        three_mo_prox, three_mo_dist = None, None
        if single_three_mo_zone:
            try:
                three_mo_prox = float(single_three_mo_zone["proximal"])
                three_mo_dist = float(single_three_mo_zone["distal"])
                logging.debug(f"three_mo_prox: {three_mo_prox}, three_mo_dist: {three_mo_dist}")
            except (TypeError, ValueError, KeyError) as e:
                logging.error(f"Error converting 3mo proximal/distal to float: {e}")

        one_mo_prox, one_mo_dist = None, None
        if single_one_mo_zone:
            try:
                one_mo_prox = float(single_one_mo_zone["proximal"])
                one_mo_dist = float(single_one_mo_zone["distal"])
                logging.debug(f"one_mo_prox: {one_mo_prox}, one_mo_dist: {one_mo_dist}")
            except (TypeError, ValueError, KeyError) as e:
                logging.error(f"Error converting 1mo proximal/distal to float: {e}")

        # 3) Collect entries from the 1d Demand Zones, but only if they lie within either the single 1mo or 3mo demand zone
        daily_zones = zones_result.get("1d", [])
        logging.debug(f"daily_zones: {daily_zones}")
        for dz in daily_zones:
            if dz.get("zoneType") == "Demand":
                entry_price = dz.get("proximal")
                stop_loss = dz.get("distal")
                logging.debug(f"Processing Daily Demand Zone - entry_price: {entry_price}, stop_loss: {stop_loss}")

                if entry_price is not None and stop_loss is not None:
                    if not isinstance(entry_price, (float, int)) or not isinstance(stop_loss, (float, int)):
                        logging.error(f"entry_price or stop_loss is not a scalar: entry_price={entry_price} (type: {type(entry_price)}), stop_loss={stop_loss} (type: {type(stop_loss)})")
                        continue
                    try:
                        # Ensure entry_price and stop_loss are floats
                        entry_price_f = float(entry_price)
                        stop_loss_f = float(stop_loss)
                        logging.debug(f"Converted entry_price_f: {entry_price_f}, stop_loss_f: {stop_loss_f}")

                        # Check if the daily zone is within the 3mo or 1mo zone range
                        in_three_mo = (
                            three_mo_prox is not None and three_mo_dist is not None and 
                            (three_mo_dist <= stop_loss_f) and (entry_price_f <= three_mo_prox)
                        )
                        in_one_mo = (
                            one_mo_prox is not None and one_mo_dist is not None and 
                            (one_mo_dist <= stop_loss_f) and (entry_price_f <= one_mo_prox)
                        )
                        logging.debug(f"in_three_mo: {in_three_mo}, in_one_mo: {in_one_mo}")

                        # Add only if in either the 1mo or 3mo demand zone
                        if in_three_mo or in_one_mo:
                            dto["entries"].append({
                                "entry": round(entry_price_f, 2),
                                "stoploss": round(stop_loss_f, 2)
                            })
                            logging.debug(f"Added entry: {{'entry': {entry_price_f}, 'stoploss': {stop_loss_f}}}")
                    except (TypeError, ValueError) as e:
                        logging.error(f"Error converting entry_price/stop_loss to float in entries: {e}")
                else:
                    logging.warning("Daily Demand Zone found but entry_price or stop_loss is missing.")

        # 4) Determine the target from the nearest Supply Zone (either 1mo or 3mo)
        supply_candidates = [
            z for z in zones_result.get("1mo", [])
            if z.get("zoneType") == "Supply" and z.get("interval") in ("1mo", "3mo")
        ]
        logging.debug(f"supply_candidates: {supply_candidates}")

        if supply_candidates:
            try:
                # Pick the zone with proximal closest to current_market_price
                target_zone = min(
                    supply_candidates,
                    key=lambda z: abs(float(z.get("proximal", math.inf)) - current_market_price)
                )
                proximal = target_zone.get("proximal")
                logging.debug(f"Selected target_zone: {target_zone}")
                if proximal is not None:
                    proximal = float(proximal)
                    dto["target"] = round(proximal, 2)
                    logging.debug(f"Set target: {dto['target']}")
                else:
                    logging.warning("Supply Zone found but proximal is missing.")
            except (TypeError, ValueError) as e:
                logging.error(f"Error determining target from Supply Zones: {e}")
        else:
            logging.warning("No Supply Zones found with intervals '1mo' or '3mo'.")

        # 5) Calculate trade score
        trade_score = 0
        if single_three_mo_zone:  # 3mo zone exists
            trade_score += 2
            logging.debug("Trade score incremented by 2 for existing 3mo Demand Zone.")
        if single_one_mo_zone:    # 1mo zone exists
            trade_score += 1
            logging.debug("Trade score incremented by 1 for existing 1mo Demand Zone.")
        if len(dto["entries"]) > 0:  # At least one entry
            trade_score += 1
            logging.debug(f"Trade score incremented by 1 for {len(dto['entries'])} entry(ies).")
        dto["trade_score"] = trade_score
        logging.debug(f"Calculated trade_score: {trade_score}")

        logging.debug(f"Final DTO: {dto}")
        logging.debug("Exiting build_zones_dto")
        return dto

    def _get_zones(self, zones: List[Dict], zone_type: str, interval: str) -> List[Dict]:
        """
        Returns all zones from 'zones' matching zone_type and interval.

        Parameters:
            zones (list): List of zone dictionaries.
            zone_type (str): The type of zone to search for ('Demand' or 'Supply').
            interval (str): The interval of the zone ('1mo', '3mo', etc.).

        Returns:
            list: A list of matching zone dictionaries.
        """
        logging.debug(f"Entering _get_zones with zone_type='{zone_type}' and interval='{interval}'")
        matching_zones = [z for z in zones if z.get("zoneType") == zone_type and z.get("interval") == interval]
        logging.debug(f"Found {len(matching_zones)} zones matching zone_type='{zone_type}' and interval='{interval}': {matching_zones}")
        return matching_zones

    def _get_closest_zones(self, zones: List[Dict], current_market_price: float, top_n: int = 2) -> List[Dict]:
        """
        Returns the top_n zones with proximal prices closest to the current_market_price.

        Parameters:
            zones (list): List of zone dictionaries.
            current_market_price (float): The current market price.
            top_n (int): Number of closest zones to retrieve.

        Returns:
            list: A list of the top_n closest zone dictionaries.
        """
        logging.debug(f"Entering _get_closest_zones with current_market_price={current_market_price} and top_n={top_n}")
        valid_zones = []
        for z in zones:
            proximal = z.get("proximal")
            if proximal is not None:
                if isinstance(proximal, (float, int)):
                    valid_zones.append(z)
                else:
                    logging.error(f"proximal is not a scalar in zone: {z}")
            else:
                logging.warning(f"Zone missing 'proximal': {z}")

        logging.debug(f"Valid zones for closest calculation: {valid_zones}")

        try:
            sorted_zones = sorted(valid_zones, key=lambda z: abs(float(z["proximal"]) - current_market_price))
            logging.debug(f"sorted_zones: {sorted_zones}")
        except Exception as e:
            logging.error(f"Error sorting zones: {e}")
            return []

        closest_zones = sorted_zones[:top_n]
        logging.debug(f"closest_zones (top {top_n}): {closest_zones}")
        return closest_zones
