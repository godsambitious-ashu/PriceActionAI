import pandas as pd

class SupplyZoneIdentifier:
    @staticmethod
    def identify_supply_zones(stock_data, interval, gap_threshold=0.03):
        """
        Identify supply zones in the given stock_data DataFrame based on reversed logic 
        from DemandZoneIdentifier:
        
        1. Attempt a Green Exciting Candle -> Red Exciting Candle pattern (quick 2-candle pattern).
        2. Otherwise, if the candle qualifies as a 'first candle' (ExcitingCandle or GapDown), 
           collect base candles and then look for a 'second candle' (red exciting or gap-down) 
           to confirm the supply zone.
        
        Parameters
        ----------
        stock_data : pd.DataFrame
            Must contain columns: 'Open', 'Close', 'High', 'Low', 'ExcitingCandle', 'GapDown', 'BaseCandle'.
        interval : str
            Time interval of the candles (e.g., '1d', '1wk', '1mo').
        gap_threshold : float, optional
            Threshold to define gap-down candles, if needed. (Currently not used in the logic below.)
        
        Returns
        -------
        patterns : list of dict
            List of identified supply zone patterns. Each dict includes:
            'zone_id', 'dates', 'proximal', 'distal', 'score', 'interval', 'candles'
        """
        # Define intervals that allow up to 5 base candles
        extended_intervals = ['1mo', '3mo', '6mo', '1y', '2y', '5y', '10y']
        max_base_candles = 5 if interval in extended_intervals else 3

        patterns = []
        zone_id = 1
        n = len(stock_data)
        i = 1  # start from 1 because we may reference i-1 for GapDown checks if needed

        while i < n - 1:
            # 1) Attempt Green -> Red Exciting Candle pattern
            green_red_pattern_created, zone_id, i = SupplyZoneIdentifier._attempt_green_red_pattern(
                stock_data, i, n, zone_id, patterns, interval
            )
            if green_red_pattern_created:
                # If the pattern was created, we’ve already advanced i. Continue the main loop.
                continue

            # 2) Otherwise, check if the candle at i can be the 'first candle' (ExcitingCandle or GapDown)
            if SupplyZoneIdentifier._is_first_candle_condition(stock_data, i):
                # Determine if the first candle is Green Exciting or GapDown
                first_candle_is_green_exciting = stock_data.iloc[i]['Close'] > stock_data.iloc[i]['Open']
                first_candle_is_gap_down = stock_data.iloc[i]['GapDown']
                first_candle_condition = first_candle_is_green_exciting or first_candle_is_gap_down

                # Collect base candles
                base_candles, j = SupplyZoneIdentifier._collect_base_candles(
                    stock_data, i, n, max_base_candles
                )

                # If we have at least 1 base candle, check for a valid second candle
                if len(base_candles) >= 1 and j < n:
                    SupplyZoneIdentifier._check_and_create_pattern_after_base(
                        stock_data, i, j, n, first_candle_condition, base_candles, 
                        patterns, zone_id, interval
                    )
                    # If a pattern was found, zone_id may be incremented
                    if len(patterns) > 0:
                        zone_id += 1
                    i = j  # move past the candles we just checked
                else:
                    # No valid base candles or end of data
                    i = j
            else:
                i += 1

        return patterns

    # --------------------------------------------------------------------
    #                   HELPER METHODS
    # --------------------------------------------------------------------

    @staticmethod
    def _is_first_candle_condition(stock_data, i):
        """
        For a supply zone, the 'first candle' can be either an ExcitingCandle
        or a GapDown candle.
        """
        return bool(stock_data.iloc[i]['ExcitingCandle'] or stock_data.iloc[i]['GapDown'])

    @staticmethod
    def _attempt_green_red_pattern(stock_data, i, n, zone_id, patterns, interval):
        """
        Attempt to identify a quick 2-candle pattern:
        1) Green Exciting Candle (Close > Open)
        2) Red Exciting Candle (Close < Open) that closes below the first candle's open.
        
        Returns (pattern_created, updated_zone_id, updated_i).
        """
        is_green_exciting = (
            stock_data.iloc[i]['ExcitingCandle'] and
            stock_data.iloc[i]['Close'] > stock_data.iloc[i]['Open']
        )
        if not (is_green_exciting and i + 1 < n):
            return False, zone_id, i

        # Next candle
        next_candle = stock_data.iloc[i + 1]
        is_red_exciting = (
            next_candle['ExcitingCandle'] and 
            next_candle['Close'] < next_candle['Open']
        )
        closes_below_first_open = next_candle['Close'] < stock_data.iloc[i]['Open']

        if is_red_exciting and closes_below_first_open:
            # For supply zone:
            # proximal = next candle's open
            proximal = next_candle['Open']
            # distal = maximum high among the two candles
            distal = max(stock_data.iloc[i]['High'], next_candle['High'])

            score = SupplyZoneIdentifier._calculate_score(stock_data, i + 2, n)

            pattern = {
                'zone_id': zone_id,
                'dates': stock_data.index[i:i+2],
                'proximal': proximal,
                'distal': distal,
                'score': score,
                'interval': interval,
                'zoneType': "Supply",
                'candles': [
                    {
                        'date': stock_data.index[i],
                        'type': 'First (Green Exciting)',
                        'ohlc': stock_data.iloc[i][['Open', 'High', 'Low', 'Close']].round(2).to_dict()
                    },
                    {
                        'date': stock_data.index[i+1],
                        'type': 'Second (Red Exciting)',
                        'ohlc': stock_data.iloc[i+1][['Open', 'High', 'Low', 'Close']].round(2).to_dict()
                    }
                ]
            }
            patterns.append(pattern)

            return True, zone_id + 1, i + 1  # move i by 2 to skip both candles
        else:
            return False, zone_id, i

    @staticmethod
    def _collect_base_candles(stock_data, start_idx, n, max_base_candles):
        """
        Collect up to max_base_candles "BaseCandle" candles, ensuring they 
        are not ExcitingCandle or GapDown. 
        (Mirroring Demand logic but with 'GapDown' instead of 'GapUp'.)
        
        Returns (base_candles_list, next_index).
        """
        base_candles = []
        j = start_idx + 1

        while j < n and len(base_candles) < max_base_candles:
            if (
                stock_data.iloc[j]['BaseCandle'] and
                not stock_data.iloc[j]['ExcitingCandle'] and
                not stock_data.iloc[j]['GapDown']
            ):
                base_candles.append(stock_data.iloc[j])
                j += 1
            else:
                break

        return base_candles, j

    @staticmethod
    def _check_and_create_pattern_after_base(
        stock_data, 
        i, 
        j, 
        n, 
        first_candle_condition, 
        base_candles, 
        patterns, 
        zone_id, 
        interval
    ):
        """
        After collecting base candles, check if the candle at j qualifies as the 'second' candle:
        - Must be either a Red ExcitingCandle or a GapDown.
        - If interval is extended, ensure additional checks as needed.
        
        Then build the supply zone pattern. 
        Proximal = lowest body among the base candles,
        Distal   = highest high among relevant candles.
        """
        extended_intervals = ['1mo', '3mo', '6mo', '1y', '2y', '5y', '10y']

        # Ensure at least one more candle for the 'second candle'
        if j < n:
            second_candle = stock_data.iloc[j]
            is_second_candle_valid = (
                (second_candle['ExcitingCandle'] and second_candle['Close'] < second_candle['Open']) or
                second_candle['GapDown']
            )
            if is_second_candle_valid:
                # For extended intervals, apply additional conditions
                if interval in extended_intervals:
                    max_high = max(candle['High'] for candle in base_candles)
                    if stock_data.iloc[j]['Close'] >= max_high:
                        return  # Do not identify the pattern

                # We have a valid second candle, so let's build the pattern.
                zone_dates = stock_data.index[i:j+1]

                # 1) Proximal = lowest body of the base candles
                proximal = min(
                    min(candle['Open'], candle['Close']) for candle in base_candles
                )

                # 2) Distal = highest high among first candle (if Green Exciting or GapDown), base candles, and second candle
                high_values = []
                if first_candle_condition:
                    high_values.append(stock_data.iloc[i]['High'])
                high_values.extend(candle['High'] for candle in base_candles)
                high_values.append(second_candle['High'])
                distal = max(high_values)

                score = SupplyZoneIdentifier._calculate_score(stock_data, j + 1, n)

                pattern = {
                    'zone_id': zone_id,
                    'dates': zone_dates,
                    'proximal': proximal,
                    'distal': distal,
                    'score': score,
                    'interval': interval,
                    'zoneType': "Supply",
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
                pass
        else:
            pass

    @staticmethod
    def _calculate_score(stock_data, start_idx, n):
        """
        Calculate a supply 'score' based on subsequent Exciting or GapDown candles:
         - If a candle is a Red ExcitingCandle (Close < Open), add +1
         - If a candle is GapDown, add +2
         - Otherwise, stop counting.
        """
        score = 0
        k = start_idx
        while k < n:
            if stock_data.iloc[k]['ExcitingCandle'] and stock_data.iloc[k]['Close'] < stock_data.iloc[k]['Open']:
                score += 1
            elif stock_data.iloc[k].get('GapDown', False):
                score += 1
            else:
                break
            k += 1
        return score