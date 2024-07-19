import logging


class DemandZoneIdentifier:
    @staticmethod
    def identify_demand_zones(stock_data):
        logging.debug("Starting to identify demand zones")
        patterns = []
        zone_id = 1
        n = len(stock_data)
        
        i = 0
        while i < n - 4:
            logging.debug(f"Checking candle at index {i}")
            if stock_data.iloc[i]['ExcitingCandle']:
                logging.debug(f"Found exciting candle at index {i}")
                
                first_exciting_candle_is_green = stock_data.iloc[i]['Close'] > stock_data.iloc[i]['Open']
                
                if i + 1 < n and stock_data.iloc[i + 1]['BaseCandle']:
                    logging.debug(f"Found base candle at index {i+1}")
                    base_candles = [stock_data.iloc[i + 1]]
                    if i + 2 < n and stock_data.iloc[i + 2]['BaseCandle']:
                        logging.debug(f"Found base candle at index {i+2}")
                        base_candles.append(stock_data.iloc[i + 2])
                    if i + 3 < n and stock_data.iloc[i + 3]['BaseCandle']:
                        logging.debug(f"Found base candle at index {i+3}")
                        base_candles.append(stock_data.iloc[i + 3])
                    if i + len(base_candles) + 1 < n and stock_data.iloc[i + len(base_candles) + 1]['ExcitingCandle'] and stock_data.iloc[i + len(base_candles) + 1]['Close'] > stock_data.iloc[i + len(base_candles) + 1]['Open']:
                        logging.debug(f"Found green exciting candle at index {i + len(base_candles) + 1}")
                        zone_dates = stock_data.index[i:i + len(base_candles) + 2]
                        
                        # Proximal line is the highest open or close of the base candle immediately before the last green exciting candle
                        proximal = max(stock_data.iloc[i + len(base_candles)][['Open', 'Close']])

                        if first_exciting_candle_is_green:
                            distal = min(candle['Low'] for candle in base_candles + [stock_data.iloc[i + len(base_candles) + 1]])
                        else:
                            distal = min(stock_data.iloc[i]['Low'], *(candle['Low'] for candle in base_candles))
                            if i + len(base_candles) + 1 < n and stock_data.iloc[i + len(base_candles) + 1]['ExcitingCandle']:
                                distal = min(distal, stock_data.iloc[i + len(base_candles) + 1]['Low'])
                        
                        # Calculate score based on green exciting or gap-up candles
                        score = 0
                        j = i + len(base_candles) + 2
                        while j < n:
                            if stock_data.iloc[j]['ExcitingCandle'] and stock_data.iloc[j]['Close'] > stock_data.iloc[j]['Open']:
                                score += 1
                            elif 'GapUpCandle' in stock_data.columns and stock_data.iloc[j]['GapUpCandle']:
                                score += 2
                            else:
                                break
                            j += 1

                        patterns.append({
                            'zone_id': zone_id,
                            'dates': zone_dates,
                            'proximal': proximal,
                            'distal': distal,
                            'score': score,
                            'candles': [{'date': stock_data.index[i], 'type': 'Exciting', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[i][['Open', 'High', 'Low', 'Close']].to_dict().items()}}] +
                                    [{'date': stock_data.index[i + j], 'type': 'Base', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[i + j][['Open', 'High', 'Low', 'Close']].to_dict().items()}} for j in range(1, len(base_candles) + 1)] +
                                    [{'date': stock_data.index[i + len(base_candles) + 1], 'type': 'Exciting', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[i + len(base_candles) + 1][['Open', 'High', 'Low', 'Close']].to_dict().items()}}]
                        })
                        logging.debug(f"Pattern identified with dates: {zone_dates} and prices: proximal={proximal}, distal={distal}, score={score}")
                        zone_id += 1
                        i = i + len(base_candles) + 1  # Move to the last exciting candle of the identified pattern
                    else:
                        logging.debug(f"Pattern not completed at index {i + len(base_candles) + 1}")
                        i += 1  # Move to the next candle
                else:
                    logging.debug(f"No base candle found after exciting candle at index {i}")
                    i += 1  # Move to the next candle
            else:
                i += 1  # Move to the next candle
        
        logging.debug("Demand zones identification completed")
        return patterns