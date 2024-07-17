import logging

class DemandZoneIdentifier:
    @staticmethod
    def identify_demand_zones(stock_data):
        logging.debug("Starting to identify demand zones")
        patterns = []
        zone_id = 1
        n = len(stock_data)
        
        i = 0
        while i < n - 2:
            logging.debug(f"Checking candle at index {i}")
            if stock_data.iloc[i]['ExcitingCandle']:
                logging.debug(f"Found exciting candle at index {i}")
                
                first_exciting_candle_is_green = stock_data.iloc[i]['Close'] > stock_data.iloc[i]['Open']
                
                base_candles = []
                for j in range(1, 4):  # Allow up to 3 base candles
                    if i + j < n and stock_data.iloc[i + j]['BaseCandle']:
                        logging.debug(f"Found base candle at index {i+j}")
                        base_candles.append(stock_data.iloc[i + j])
                    else:
                        break
                
                if base_candles:
                    # Check for the final valid candle after base candles
                    final_candle_idx = i + len(base_candles) + 1
                    if final_candle_idx < n and (stock_data.iloc[final_candle_idx]['ExcitingCandle'] and stock_data.iloc[final_candle_idx]['Close'] > stock_data.iloc[final_candle_idx]['Open']) or stock_data.iloc[final_candle_idx]['GapUp']:
                        logging.debug(f"Found valid final candle at index {final_candle_idx}")
                        zone_dates = stock_data.index[i:i + len(base_candles) + 2]
                        
                        # Proximal line is the highest open or close of the base candle immediately before the last exciting candle
                        proximal = max(stock_data.iloc[i + len(base_candles)][['Open', 'Close']])
                        
                        if first_exciting_candle_is_green:
                            distal = min(candle['Low'] for candle in base_candles + [stock_data.iloc[final_candle_idx]])
                        else:
                            distal = min(stock_data.iloc[i]['Low'], *(candle['Low'] for candle in base_candles + [stock_data.iloc[final_candle_idx]]))
                        
                        patterns.append({
                            'zone_id': zone_id,
                            'dates': zone_dates,
                            'proximal': proximal,
                            'distal': distal,
                            'candles': [{'date': stock_data.index[i], 'type': 'Exciting', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[i][['Open', 'High', 'Low', 'Close']].to_dict().items()}}] +
                                    [{'date': stock_data.index[i + j], 'type': 'Base', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[i + j][['Open', 'High', 'Low', 'Close']].to_dict().items()}} for j in range(1, len(base_candles) + 1)] +
                                    [{'date': stock_data.index[final_candle_idx], 'type': 'Exciting', 'ohlc': {k: round(v, 2) for k, v in stock_data.iloc[final_candle_idx][['Open', 'High', 'Low', 'Close']].to_dict().items()}}]
                        })
                        logging.debug(f"Pattern identified with dates: {zone_dates} and prices: proximal={proximal}, distal={distal}")
                        zone_id += 1
                        i = final_candle_idx  # Move to the last exciting candle of the identified pattern
                    else:
                        i += 1  # Move to the next candle
                else:
                    i += 1  # Move to the next candle
            else:
                i += 1  # Move to the next candle
        
        logging.debug("Demand zones identification completed")
        return patterns
