import pandas as pd

class DemandZoneIdentifier:
    @staticmethod
    def identify_demand_zones(stock_data, interval, gap_threshold=0.03):
        # Define Gap-Up Candles

        # Define extended intervals that allow up to 6 base candles
        extended_intervals = ['1mo', '3mo', '6mo', '1y', '2y', '5y', '10y']
        max_base_candles = 5 if interval in extended_intervals else 3

        patterns = []
        zone_id = 1
        n = len(stock_data)
        i = 1  # Start from 1 because we use shift(1) for gap-up calculation

        while i < n - 1:
            # Check the "first candle" conditions
            first_candle_condition = DemandZoneIdentifier._is_first_candle_condition(stock_data, i)
            
            # Attempt Red Exciting Candle -> Green Exciting Candle pattern
            red_green_pattern_created, zone_id, i = DemandZoneIdentifier._attempt_red_green_pattern(
                stock_data, i, n, zone_id, patterns, interval
            )
            if red_green_pattern_created:
                # If the pattern was created, we've already advanced `i` by 2. Continue the main loop.
                continue

            # Otherwise, if first_candle_condition is True, proceed to find base candles and second candle
            if first_candle_condition:
                first_candle_is_green = stock_data.iloc[i]['Close'] > stock_data.iloc[i]['Open']
                
                base_candles, j = DemandZoneIdentifier._collect_base_candles(
                    stock_data, i, n, max_base_candles
                )

                # If we have at least 1 base candle, check for a valid second candle
                if len(base_candles) >= 1:
                    DemandZoneIdentifier._check_and_create_pattern_after_base(
                        stock_data, i, j, n, first_candle_is_green, base_candles, 
                        patterns, zone_id, interval
                    )
                    # If a pattern was found, zone_id is incremented inside the helper; 
                    # we need the updated zone_id value.
                    if len(patterns) > 0:
                        zone_id = patterns[-1]['zone_id'] + 1
                    i = j  # Move to the index after checking second candle
                else:
                    # No base candles collected; pattern invalid
                    i = j  # Move past the first candle and any non-base candles
            else:
                i += 1  # Move to the next candle

        return patterns

    @staticmethod
    def _is_first_candle_condition(stock_data, i):
        """
        Check if the candle at index i qualifies as the 'first candle' in the pattern:
        either ExcitingCandle or GapUpCandle.
        """
        return bool(stock_data.iloc[i]['ExcitingCandle'] or stock_data.iloc[i]['GapUp'])

    @staticmethod
    def _attempt_red_green_pattern(stock_data, i, n, zone_id, patterns, interval):
        """
        Attempt to identify the Red Exciting Candle followed by Green Exciting Candle pattern.
        Returns a tuple: (pattern_created (bool), updated_zone_id, updated_i).
        """
        is_red_exciting = (
            stock_data.iloc[i]['ExcitingCandle'] and 
            stock_data.iloc[i]['Close'] < stock_data.iloc[i]['Open']
        )
        # If not red exciting or there's no next candle, return immediately.
        if not (is_red_exciting and (i + 1 < n)):
            return False, zone_id, i

        next_candle = stock_data.iloc[i + 1]
        is_green_exciting = (
            next_candle['ExcitingCandle'] and 
            next_candle['Close'] > next_candle['Open']
        )
        closes_above_first_open = next_candle['Close'] > stock_data.iloc[i]['Open']

        # Check the Red->Green condition
        if is_green_exciting and closes_above_first_open:
            proximal = next_candle['Open']
            distal = min(stock_data.iloc[i]['Low'], next_candle['Low'])

            score = DemandZoneIdentifier._calculate_score(stock_data, i + 2, n)

            # Append the identified pattern
            pattern = {
                'zone_id': zone_id,
                'dates': stock_data.index[i:i+2],
                'proximal': proximal,
                'distal': distal,
                'score': score,
                'interval': interval,
                'zoneType': "Demand",
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
            }
            patterns.append(pattern)
            return True, zone_id + 1, i + 1

        return False, zone_id, i

    @staticmethod
    def _collect_base_candles(stock_data, start_idx, n, max_base_candles):
        """
        Collect up to `max_base_candles` base candles starting from start_idx+1.
        Returns (list_of_base_candles, next_index_after_base_candles).
        """
        base_candles = []
        j = start_idx + 1

        while j < n and len(base_candles) < max_base_candles:
            if (
                stock_data.iloc[j]['BaseCandle'] and 
                not stock_data.iloc[j]['ExcitingCandle'] and 
                not stock_data.iloc[j]['GapUp']
            ):
                base_candles.append(stock_data.iloc[j])
                j += 1
            else:
                # Stop collecting base candles if a non-base or exciting candle is encountered
                break

        return base_candles, j

    @staticmethod
    def _check_and_create_pattern_after_base(
        stock_data, 
        i, 
        j, 
        n, 
        first_candle_is_green, 
        base_candles, 
        patterns, 
        zone_id, 
        interval
    ):
        """
        Given the first candle and collected base candles, check if the next candle
        qualifies to complete a pattern. If so, create that pattern and append to 'patterns'.
        """
        # Define extended intervals within the method
        extended_intervals = ['1wk' ,'1mo', '3mo', '6mo', '1y', '2y', '5y', '10y']

        # Check if at least one more candle exists for the second candle
        if j < n and DemandZoneIdentifier._is_first_candle_condition(stock_data, j):
            second_candle_is_green = stock_data.iloc[j]['Close'] > stock_data.iloc[j]['Open']
            # We only proceed if the second candle is either green or GapUp
            if second_candle_is_green or stock_data.iloc[j]['GapUp']:
                # **Add the following block for the additional condition**
                if interval in extended_intervals:
                    # Calculate the minimum low of the base candles
                    min_low = min(candle['Low'] for candle in base_candles)
                    # Check if the closing price of the second candle is above the minimum low
                    if stock_data.iloc[j]['Close'] <= min_low:
                        return  # Do not identify the pattern

                # Proceed to identify and create the pattern
                zone_dates = stock_data.index[i:j+1]
                proximal = max(stock_data.iloc[j - 1][['Open', 'Close']])

                # Build the low_values array for distal
                low_values = []
                if first_candle_is_green or stock_data.iloc[i]['GapUp']:
                    # Include 'Low' of base candles and second candle
                    low_values.extend(candle['Low'] for candle in base_candles)
                    low_values.append(stock_data.iloc[j]['Low'])
                else:
                    # Include 'Low' of first candle, base candles, and second candle
                    low_values.append(stock_data.iloc[i]['Low'])
                    low_values.extend(candle['Low'] for candle in base_candles)
                    low_values.append(stock_data.iloc[j]['Low'])

                distal = min(low_values)
                score = DemandZoneIdentifier._calculate_score(stock_data, j + 1, n)

                # Construct the pattern dict
                pattern = {
                    'zone_id': zone_id,
                    'dates': zone_dates,
                    'proximal': proximal,
                    'distal': distal,
                    'score': score,
                    'interval': interval,
                    'zoneType': "Demand",
                    'candles': (
                        [{
                            'date': stock_data.index[i],
                            'type': 'First',
                            'ohlc': stock_data.iloc[i][['Open', 'High', 'Low', 'Close']].round(2).to_dict()
                        }] +
                        [{
                            'date': stock_data.index[idx],
                            'type': 'Base',
                            'ohlc': stock_data.iloc[idx][['Open', 'High', 'Low', 'Close']].round(2).to_dict()
                        } for idx in range(i + 1, j)] +
                        [{
                            'date': stock_data.index[j],
                            'type': 'Second',
                            'ohlc': stock_data.iloc[j][['Open', 'High', 'Low', 'Close']].round(2).to_dict()
                        }]
                    )
                }
                patterns.append(pattern)
            else:
                # Second candle is not green or a gap-up; pattern breaks
                pass
        else:
            # No valid second candle found; pattern incomplete
            pass

    @staticmethod
    def _calculate_score(stock_data, start_idx, n):
        """
        Calculate the 'score' based on subsequent exciting or gap-up candles
        starting from `start_idx` until a candle that doesn't fit those criteria is encountered.
        """
        score = 0
        k = start_idx
        while k < n:
            if stock_data.iloc[k]['ExcitingCandle'] and stock_data.iloc[k]['Close'] > stock_data.iloc[k]['Open']:
                score += 1
            elif stock_data.iloc[k]['GapUp']:
                score += 1
            else:
                break
            k += 1
        return score