import logging
import pandas as pd

class DemandZoneIdentifier:
    @staticmethod
    def identify_demand_zones(stock_data, interval, gap_threshold=0.01):
        logging.debug("Starting to identify demand zones")
        patterns = []
        zone_id = 1
        n = len(stock_data)

        # Define Gap-Up Candles
        stock_data['GapUpCandle'] = stock_data['Open'] > stock_data['Close'].shift(1) * (1 + gap_threshold)

        # Define Exciting Candles (Assuming 'ExcitingCandle' is pre-defined in stock_data)
        # If not, define criteria for ExcitingCandle here
        # Example: stock_data['ExcitingCandle'] = (stock_data['Close'] > stock_data['Open'] * 1.02) | (stock_data['Close'] < stock_data['Open'] * 0.98)

        # Define the intervals that allow up to 6 base candles
        extended_intervals = ['1m', '3m', '6m', '1y', '2y', '5y', '10y']

        # Set the maximum number of base candles based on the interval
        if interval in extended_intervals:
            max_base_candles = 6
        else:
            max_base_candles = 3

        i = 1  # Start from 1 because we use shift(1) for gap-up calculation
        while i < n - 1:
            logging.debug(f"Checking candle at index {i}, date: {stock_data.index[i]}, Open: {stock_data.iloc[i]['Open']}, Close: {stock_data.iloc[i]['Close']}, High: {stock_data.iloc[i]['High']}, Low: {stock_data.iloc[i]['Low']}")

            # Check if the first candle is an exciting candle or a gap-up candle
            first_candle_condition = stock_data.iloc[i]['ExcitingCandle'] or stock_data.iloc[i]['GapUpCandle']

            # New Condition: Check for Red Exciting Candle followed by Green Exciting Candle
            is_red_exciting = stock_data.iloc[i]['ExcitingCandle'] and (stock_data.iloc[i]['Close'] < stock_data.iloc[i]['Open'])
            if is_red_exciting and (i + 1 < n):
                next_candle = stock_data.iloc[i + 1]
                is_green_exciting = next_candle['ExcitingCandle'] and (next_candle['Close'] > next_candle['Open'])
                closes_above_first_open = next_candle['Close'] > stock_data.iloc[i]['Open']
                if is_green_exciting and closes_above_first_open:
                    logging.debug(f"Found red exciting candle at index {i} and green exciting candle at index {i+1}")

                    proximal = next_candle['Open']  # Proximal line is opening price of green exciting candle
                    distal = min(stock_data.iloc[i]['Low'], next_candle['Low'])  # Distal line is lowest wick of the two candles

                    # Calculate score based on subsequent exciting or gap-up candles
                    score = 0
                    k = i + 2
                    while k < n:
                        if stock_data.iloc[k]['ExcitingCandle'] and stock_data.iloc[k]['Close'] > stock_data.iloc[k]['Open']:
                            score += 1
                        elif stock_data.iloc[k]['GapUpCandle']:
                            score += 2
                        else:
                            break
                        k += 1

                    # Append the identified pattern
                    patterns.append({
                        'zone_id': zone_id,
                        'dates': stock_data.index[i:i+2],
                        'proximal': proximal,
                        'distal': distal,
                        'score': score,
                        'candles': [
                            {
                                'date': stock_data.index[i],
                                'type': 'First (Red Exciting)',
                                'ohlc': stock_data.iloc[i][['Open', 'High', 'Low', 'Close']].round(2).to_dict()
                            },
                            {
                                'date': stock_data.index[i+1],
                                'type': 'Second (Green Exciting)',
                                'ohlc': stock_data.iloc[i+1][['Open', 'High', 'Low', 'Close']].round(2).to_dict()
                            }
                        ]
                    })
                    logging.debug(f"Pattern identified with dates: {stock_data.index[i:i+2]} and prices: proximal={proximal}, distal={distal}, score={score}")
                    zone_id += 1
                    i += 2  # Move past the two candles of the identified pattern
                    continue  # Proceed to the next iteration

            if first_candle_condition:
                logging.debug(f"Found first candle at index {i} with date {stock_data.index[i]}")

                first_candle_is_green = stock_data.iloc[i]['Close'] > stock_data.iloc[i]['Open']

                base_candles = []
                j = i + 1
                # Collect up to a maximum of max_base_candles
                while j < n and len(base_candles) < max_base_candles:
                    if stock_data.iloc[j]['BaseCandle'] and not stock_data.iloc[j]['ExcitingCandle'] and not stock_data.iloc[j]['GapUpCandle']:
                        logging.debug(f"Found base candle at index {j}, date: {stock_data.index[j]}")
                        base_candles.append(stock_data.iloc[j])
                        j += 1
                    else:
                        # Stop collecting base candles if a non-base or exciting candle is encountered
                        break

                # Check if at least one base candle has been collected
                if len(base_candles) >= 1:
                    # Check if the next candle is an exciting candle or a gap-up candle
                    if j < n and (stock_data.iloc[j]['ExcitingCandle'] or stock_data.iloc[j]['GapUpCandle']):
                        second_candle_is_green = stock_data.iloc[j]['Close'] > stock_data.iloc[j]['Open']
                        if second_candle_is_green or stock_data.iloc[j]['GapUpCandle']:
                            logging.debug(f"Found second candle at index {j}, date: {stock_data.index[j]}")
                            zone_dates = stock_data.index[i:j+1]

                            # Proximal line is the highest open or close of the base candle immediately before the second candle
                            proximal = max(stock_data.iloc[j - 1][['Open', 'Close']])

                            # Calculate distal
                            low_values = []
                            if first_candle_is_green or stock_data.iloc[i]['GapUpCandle']:
                                # Include 'Low' of base candles and second candle
                                low_values.extend(candle['Low'] for candle in base_candles)
                                low_values.append(stock_data.iloc[j]['Low'])
                            else:
                                # Include 'Low' of first candle, base candles, and second candle
                                low_values.append(stock_data.iloc[i]['Low'])
                                low_values.extend(candle['Low'] for candle in base_candles)
                                low_values.append(stock_data.iloc[j]['Low'])

                            distal = min(low_values)

                            # Calculate score based on subsequent exciting or gap-up candles
                            score = 0
                            k = j + 1
                            while k < n:
                                if stock_data.iloc[k]['ExcitingCandle'] and stock_data.iloc[k]['Close'] > stock_data.iloc[k]['Open']:
                                    score += 1
                                elif stock_data.iloc[k]['GapUpCandle']:
                                    score += 2
                                else:
                                    break
                                k += 1

                            # Append the identified pattern
                            patterns.append({
                                'zone_id': zone_id,
                                'dates': zone_dates,
                                'proximal': proximal,
                                'distal': distal,
                                'score': score,
                                'candles': (
                                    [{'date': stock_data.index[i], 'type': 'First', 'ohlc': stock_data.iloc[i][['Open', 'High', 'Low', 'Close']].round(2).to_dict()}] +
                                    [{'date': stock_data.index[idx], 'type': 'Base', 'ohlc': stock_data.iloc[idx][['Open', 'High', 'Low', 'Close']].round(2).to_dict()} for idx in range(i + 1, j)] +
                                    [{'date': stock_data.index[j], 'type': 'Second', 'ohlc': stock_data.iloc[j][['Open', 'High', 'Low', 'Close']].round(2).to_dict()}]
                                )
                            })
                            logging.debug(f"Pattern identified with dates: {zone_dates} and prices: proximal={proximal}, distal={distal}, score={score}")
                            zone_id += 1
                            i = j  # Move to the last candle of the identified pattern
                            continue  # Proceed to the next iteration
                        else:
                            # Second candle is not green or a gap-up; pattern breaks
                            logging.debug(f"Second candle at index {j} is not valid; pattern breaks")
                            i = j
                    else:
                        # No valid second candle found; pattern incomplete
                        logging.debug(f"Pattern not completed at index {j}")
                        i = j  # Move past the base candles
                else:
                    # No base candles collected; pattern invalid
                    logging.debug(f"No base candles collected after first candle at index {i}; pattern invalid")
                    i = j  # Move past the first candle and any non-base candles
            else:
                i += 1  # Move to the next candle

        logging.debug("Demand zones identification completed")
        return patterns
