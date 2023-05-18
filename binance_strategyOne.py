#Binance strategy:

import ccxt
import time
import json

# Replace these with your actual API key and secret key
api_key = '<YOUR_API_KEY>'
secret_key = '<YOUR_SECRET_KEY>'

# Initialize the Binance API client
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
})

initial_budget_usdt = 1000
stop_loss_percent = 0.95
time_interval = 60  # Check every minute

def get_binance_symbols():
    data = exchange.load_markets()
    return set(data.keys())

def place_orders_for_new_pair(symbol, trade_amount_usdt):
    ticker = exchange.fetch_ticker(symbol)
    current_price = ticker['last']

    trade_amount = trade_amount_usdt / current_price
    buy_order = exchange.create_market_buy_order(symbol, trade_amount)
    stop_loss_price = current_price * stop_loss_percent

    stop_loss_order = exchange.create_order(
        symbol, 'stop_loss_limit', 'sell', trade_amount, stop_loss_price, {'stopPrice': stop_loss_price}
    )

    return buy_order, stop_loss_order

def update_stop_loss(symbol, stop_loss_order_id, new_stop_loss_price):
    exchange.cancel_order(stop_loss_order_id, symbol)

    new_stop_loss_order = exchange.create_order(
        symbol, 'stop_loss_limit', 'sell', trade_amount, new_stop_loss_price, {'stopPrice': new_stop_loss_price}
    )

    return new_stop_loss_order

# Load existing trading pairs and traded pairs from JSON files
try:
    with open('trading_pairs.json', 'r') as f:
        trading_pairs = json.load(f)
except FileNotFoundError:
    trading_pairs = set()

try:
    with open('traded_pairs_info.json', 'r') as f:
        traded_pairs_info = json.load(f)
except FileNotFoundError:
    traded_pairs_info = []

# Get the current trading pairs from Binance
current_trading_pairs = get_binance_symbols()

# If the JSON file is empty, store the trading pairs and exit
if not trading_pairs:
    with open('trading_pairs.json', 'w') as f:
        json.dump(list(current_trading_pairs), f)
    print("Trading pairs saved to JSON file. Exiting.")
    exit()
while True:
    # Check for new trading pairs
    current_trading_pairs = get_binance_symbols()
    new_trading_pairs = current_trading_pairs - set(trading_pairs)

    if new_trading_pairs:
        print("New trading pairs detected:", new_trading_pairs)

        # Calculate the trade amount in USDT for each new trading pair
        trade_amount_usdt = initial_budget_usdt / len(new_trading_pairs)

        # Place orders for new trading pairs
        for symbol in new_trading_pairs:
            try:
                buy_order, stop_loss_order = place_orders_for_new_pair(symbol, trade_amount_usdt)
                print(f"Placed orders for {symbol}: Buy order - {buy_order}, Stop-loss order - {stop_loss_order}")

                # Update the trading pairs and save them to the JSON file
                trading_pairs.append(symbol)
                with open('trading_pairs.json', 'w') as f:
                    json.dump(trading_pairs, f)

                # Save the traded pair information to the JSON file
                traded_pair_info = {
                    'pair': symbol,
                    'amount': buy_order['amount'],
                    'buy_price': buy_order['price'],
                    'stop_loss': stop_loss_order['price'],
                   'stop_loss_order_id': stop_loss_order['id'],
                    'closed': False
                }
                traded_pairs_info.append(traded_pair_info)
                with open('traded_pairs_info.json', 'w') as f:
                    json.dump(traded_pairs_info, f)

            except Exception as e:
                print(f"Error placing orders for {symbol}: {e}")

    # Update stop loss for each traded pair
    for traded_pair in traded_pairs_info:
        if not traded_pair['closed']:
            try:
                symbol = traded_pair['pair']
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                stop_loss_price = current_price * stop_loss_percent

                if stop_loss_price > traded_pair['stop_loss']:
                    stop_loss_order_id = traded_pair['stop_loss_order_id']
                    new_stop_loss_order = update_stop_loss(symbol, stop_loss_order_id, stop_loss_price)

                    traded_pair['stop_loss'] = stop_loss_price
                    traded_pair['stop_loss_order_id'] = new_stop_loss_order['id']

                    print(f"Updated stop-loss for {symbol}: Stop-loss order - {new_stop_loss_order}")
               # Check if the stop-loss order is closed and update the 'closed' key
                stop_loss_order_id = traded_pair['stop_loss_order_id']
                stop_loss_order = exchange.fetch_order(stop_loss_order_id, symbol)
                if stop_loss_order['status'] == 'closed':
                    traded_pair['closed'] = True
                    print(f"Trade closed for {symbol}: Stop-loss order - {stop_loss_order}")

                    # Save the updated traded_pairs_info to the JSON file
                    with open('traded_pairs_info.json', 'w') as f:
                        json.dump(traded_pairs_info, f)

            except Exception as e:
                print(f"Error updating stop-loss for {symbol}: {e}")

    # Save the updated traded_pairs_info to the JSON file
    with open('traded_pairs_info.json', 'w') as f:
        json.dump(traded_pairs_info, f)

    time.sleep(time_interval)
