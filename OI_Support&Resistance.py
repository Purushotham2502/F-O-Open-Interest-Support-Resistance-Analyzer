import json
from fyers_apiv3 import fyersModel
import pandas as pd
import subprocess
import tkinter as tk
from tkinter import messagebox




def get_atm_strike(strikes, spot):
    return min(strikes, key=lambda x: abs(x - spot))

def atm_preferred_level(oi_by_strike, spot, kind='call', dominance_factor=1.2, atm_window=200):
    """ATM preferred support/resistance filtering."""
    if not oi_by_strike:
        return []
    strikes = sorted(oi_by_strike)
    atm = get_atm_strike(strikes, spot)
    atm_oi = oi_by_strike.get(atm, 0)
    # Neighbors within ±atm_window
    if kind == 'call':
        relevant_neighbors = [oi_by_strike.get(s, 0) for s in strikes if atm < s <= atm + atm_window]
    else:  # 'put'
        relevant_neighbors = [oi_by_strike.get(s, 0) for s in strikes if atm - atm_window <= s < atm]
    if all(atm_oi >= dominance_factor * n for n in relevant_neighbors if n > 0) and atm_oi > 0:
        return [(atm, atm_oi)]
    return []

# --- INTRADAY HIGHEST RESISTANCE ONLY WITH ADAPTIVE THRESHOLD ---
def intraday_resistance_only_highest(oi_by_strike, spot, max_pct_away=0.04, cluster_ratio=0.7, min_avg_multiplier=1.5):
    choices = [(k, v) for k, v in oi_by_strike.items()
               if k >= spot and (k - spot) / spot <= max_pct_away]
    if not choices:
        return []
    avg_oi = sum(v for _, v in choices) / len(choices)
    max_oi = max(v for _, v in choices)
    min_oi_threshold = min(avg_oi * min_avg_multiplier, max_oi)
    filtered = [(k, v) for k, v in choices if v >= min_oi_threshold and v >= max_oi * cluster_ratio]
    if filtered:
        return [max(filtered, key=lambda x: x[1])]
    return []

# --- INTRADAY STRONG SUPPORTS WITH ADAPTIVE THRESHOLD AND CLUSTER FILTER ---
def nearest_strong_supports_cluster(oi_by_strike, spot, n=2, max_pct_away=0.04, cluster_ratio=0.6, min_avg_multiplier=1.5):
    levels = [(k, v) for k, v in oi_by_strike.items()
              if k <= spot and (spot - k) / spot <= max_pct_away]
    if not levels:
        return []
    avg_oi = sum(v for _, v in levels) / len(levels)
    max_oi = max(v for _, v in levels)
    min_oi_threshold = min(avg_oi * min_avg_multiplier, max_oi)
    filtered = [(k, v) for k, v in levels if v >= min_oi_threshold]
    if not filtered:
        return []
    max_filtered_oi = max(v for _, v in filtered)
    cluster_levels = [(k, v) for k, v in filtered if v >= max_filtered_oi * cluster_ratio]
    cluster_levels.sort(key=lambda x: (-x[1], spot - x[0]))
    return cluster_levels[:n]

# --- POSITIONAL WATCHLIST RESISTANCES (TOP 2 CLUSTERS, WITH DOMINANCE LOGIC) ---
def positional_resistances_highest(oi_by_strike, spot, cluster_ratio=0.3, min_avg_multiplier=1.2, dominance_factor=1.5):
    choices = [(k, v) for k, v in oi_by_strike.items() if k >= spot]
    if not choices:
        return []
    avg_oi = sum(v for _, v in choices) / len(choices)
    max_oi = max(v for _, v in choices)
    min_oi_threshold = min(avg_oi * min_avg_multiplier, max_oi)
    filtered = [(k, v) for k, v in choices if v >= min_oi_threshold]
    if not filtered:
        return []
    max_filtered_oi = max(v for _, v in filtered)
    cluster_choices = [(k, v) for k, v in filtered if v >= max_filtered_oi * cluster_ratio]
    cluster_choices.sort(key=lambda x: (-x[1], x[0]))
    # Dominance filter: exclude closer strikes overshadowed by farther higher OI strikes
    if cluster_choices:
        dominant = []
        for i, (strike, oi) in enumerate(cluster_choices):
            overshadowed = False
            for j in range(i + 1, len(cluster_choices)):
                farther_strike, farther_oi = cluster_choices[j]
                if farther_oi >= dominance_factor * oi:
                    overshadowed = True
                    break
            if not overshadowed:
                dominant.append((strike, oi))
        if dominant:
            return dominant[:2]
        return cluster_choices[:2]
    return []

# --- POSITIONAL WATCHLIST SUPPORTS (TOP 2 CLUSTERS, WITH DOMINANCE LOGIC) ---
def positional_supports_highest(oi_by_strike, spot, cluster_ratio=0.3, min_avg_multiplier=1.2, dominance_factor=1.5):
    choices = [(k, v) for k, v in oi_by_strike.items() if k <= spot]
    if not choices:
        return []
    avg_oi = sum(v for _, v in choices) / len(choices)
    max_oi = max(v for _, v in choices)
    min_oi_threshold = min(avg_oi * min_avg_multiplier, max_oi)
    filtered = [(k, v) for k, v in choices if v >= min_oi_threshold]
    if not filtered:
        return []
    max_filtered_oi = max(v for _, v in filtered)
    cluster_choices = [(k, v) for k, v in filtered if v >= max_filtered_oi * cluster_ratio]
    cluster_choices.sort(key=lambda x: (-x[1], -x[0]))
    # Dominance filter: exclude farther supports overshadowed by closer stronger supports
    if cluster_choices:
        dominant = []
        for i, (strike, oi) in enumerate(cluster_choices):
            overshadowed = False
            for j in range(i):
                closer_strike, closer_oi = cluster_choices[j]
                if closer_oi >= dominance_factor * oi:
                    overshadowed = True
                    break
            if not overshadowed:
                dominant.append((strike, oi))
        if dominant:
            return dominant[:2]
        return cluster_choices[:2]
    return []

# --- HELPER FUNCTIONS FOR ADJACENT OI FILTERING NEAR PRICE ---
def neighboring_put_oi_near_price(put_oi_by_strike, strike, spot, max_pct_away=0.05):
    candidates = [k for k in put_oi_by_strike.keys() if k < strike and (spot - k) / spot <= max_pct_away]
    if not candidates:
        return 0
    nearest_lower = max(candidates)
    return put_oi_by_strike.get(nearest_lower, 0)

def neighboring_call_oi_near_price(call_oi_by_strike, strike, spot, max_pct_away=0.05):
    candidates = [k for k in call_oi_by_strike.keys() if k > strike and (k - spot) / spot <= max_pct_away]
    if not candidates:
        return 0
    nearest_higher = min(candidates)
    return call_oi_by_strike.get(nearest_higher, 0)

def filter_resistances_by_adjacent_puts_near_price(resistances, put_oi_by_strike, spot, max_pct_away=0.05):
    filtered = []
    for strike, oi in resistances:
        put_adj_oi = neighboring_put_oi_near_price(put_oi_by_strike, strike, spot, max_pct_away)
        if oi > put_adj_oi:
            filtered.append((strike, oi))
    return filtered

def filter_supports_by_adjacent_calls_near_price(supports, call_oi_by_strike, spot, max_pct_away=0.05):
    filtered = []
    for strike, oi in supports:
        call_adj_oi = neighboring_call_oi_near_price(call_oi_by_strike, strike, spot, max_pct_away)
        if oi > call_adj_oi:
            filtered.append((strike, oi))
    return filtered


# --- LOAD TOKENS ---
def load_tokens(filepath):
    with open(filepath, "r") as f:
        return json.load(f)
def is_token_valid(client_id, access_token):
    try:
        fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")
        # Perform a lightweight API call
        # Example: Get profile (endpoint that requires authentication)
        profile = fyers.get_profile()
        if profile.get('code') == 200:
            return True
        else:
            print(f"Received profile response: {profile}")
            return False
    except Exception as e:
        print(f"Token check failed due to exception: {e}")
        return False
def get_new_token():
    # Run your authcode.py file which fetches and writes a new access_token to fyers_tokens.json
    print("Attempting to refresh token by running authcode.py ...")
    subprocess.run(["python", "authcode.py"], check=True)

    
client_id = "1U5QOSSO5M-100"

# Step 1: Load the current tokens
tokens = load_tokens("fyers_tokens.json")
access_token = tokens.get("access_token")
# Step 2: Check if access token is valid
if not is_token_valid(client_id, access_token):
    print("Access token expired or invalid. Fetching a new access token...")
    # Step 3: Run authcode.py to refresh the token (this must create/update fyers_tokens.json)
    get_new_token()
    # Step 4: Reload the new tokens
    tokens = load_tokens("fyers_tokens.json")
    access_token = tokens.get("access_token")
    # Optional: Double check new token
    if not is_token_valid(client_id, access_token):
        raise Exception("Token refresh failed. Please check authcode.py.")
# Load tokens from JSON file
def load_tokens(filepath):
    with open(filepath, "r") as f:
        tokens = json.load(f)
    return tokens
results = []
# --- MAIN CODE ---
tokens = load_tokens("fyers_tokens.json")
access_token = tokens.get("access_token")

fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# Load stock symbol and fetch option chain
stock_list = pd.read_excel("stock_list.xlsx")
for symbol in stock_list["symbol"]:
    data = {
        "symbol": symbol,
        "strikecount": 20,
        "timestamp": ""
    }
    response = fyers.optionchain(data=data)
    options_chain = response.get("data", {}).get("optionsChain", [])
    print(f"\nProcessing {symbol} ...")
    # Extract stock price and OI data
    stock_price = None
    for item in options_chain:
        if item.get("option_type", "") == "" and item.get("strike_price", 0) == -1:
            stock_price = item.get("ltp")
            break
        print(f"Underlying stock price: {stock_price}")

    call_oi_by_strike = {}
    put_oi_by_strike = {}
    for option in options_chain:
        strike = option.get("strike_price")
        option_type = option.get("option_type")
        oi = option.get("oi")
        if strike is not None and strike != -1 and oi is not None:
            if option_type == "CE":
                call_oi_by_strike[float(strike)] = oi
            elif option_type == "PE":
                put_oi_by_strike[float(strike)] = oi

    # ATM-centric preferred intraday levels
    def atm_preferred_level(oi_by_strike, spot, kind='call', dominance_factor=1.2, atm_window=200):
        if not oi_by_strike:
            return []
        strikes = sorted(oi_by_strike)
        atm = min(strikes, key=lambda x: abs(x - spot))
        atm_oi = oi_by_strike.get(atm, 0)
        if kind == 'call':
            neighbors = [oi_by_strike.get(s, 0) for s in strikes if atm < s <= atm + atm_window]
        else:
            neighbors = [oi_by_strike.get(s, 0) for s in strikes if atm - atm_window <= s < atm]
        if all(atm_oi >= dominance_factor * n for n in neighbors if n > 0) and atm_oi > 0:
            return [(atm, atm_oi)]
        return []

    intraday_resistances = atm_preferred_level(call_oi_by_strike, stock_price, kind='call')
    intraday_supports = atm_preferred_level(put_oi_by_strike, stock_price, kind='put')

    # If ATM-based not found, fallback to original filters
    if not intraday_resistances:
        intraday_resistances_raw = intraday_resistance_only_highest(
            call_oi_by_strike, stock_price, max_pct_away=0.04, cluster_ratio=0.7, min_avg_multiplier=1.5)
        intraday_resistances = filter_resistances_by_adjacent_puts_near_price(
            intraday_resistances_raw, put_oi_by_strike, stock_price, max_pct_away=0.05)
    if not intraday_supports:
        intraday_supports_raw = nearest_strong_supports_cluster(
            put_oi_by_strike, stock_price, n=2, max_pct_away=0.06, cluster_ratio=0.6, min_avg_multiplier=1.5)
        intraday_supports = filter_supports_by_adjacent_calls_near_price(
            intraday_supports_raw, call_oi_by_strike, stock_price, max_pct_away=0.05)

    positional_resistances = positional_resistances_highest(
        call_oi_by_strike, stock_price, cluster_ratio=0.3, min_avg_multiplier=1.2, dominance_factor=1.5)
    positional_supports = positional_supports_highest(
        put_oi_by_strike, stock_price, cluster_ratio=0.3, min_avg_multiplier=1.2, dominance_factor=1.5)
    
    res_strike, res_oi = intraday_resistances[0] if intraday_resistances else (None, None)
    sup_strike, sup_oi = intraday_supports[0] if intraday_supports else (None, None)
    res_diff = abs(stock_price - res_strike) if res_strike is not None else float('inf')
    sup_diff = abs(stock_price - sup_strike) if sup_strike is not None else float('inf')

    results.append({
        "symbol": symbol,
        "stock_price": stock_price,
        "support_strike": sup_strike,
        "support_oi": sup_oi,
        "support_diff": sup_diff,
        "resistance_strike": res_strike,
        "resistance_oi": res_oi,
        "resistance_diff": res_diff,
        "nearest_level": min(sup_diff, res_diff)
   })


# Sort results by nearest level and save to Excel

results_sorted = sorted(results, key=lambda x: x["nearest_level"])
df_results = pd.DataFrame(results_sorted)
output_filename = "stocks_near_intraday_support_resistance.xlsx"
df_results.to_excel(output_filename, index=False)
print(f"Saved stocks near intraday support/resistance to {output_filename}")
