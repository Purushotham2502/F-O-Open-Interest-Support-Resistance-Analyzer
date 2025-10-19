from flask import Flask, render_template_string
import pandas as pd
import subprocess
import json
import os
import threading
import time
import webbrowser
from fyers_apiv3 import fyersModel

CLIENT_ID = "1U5QOSSO5M-100"
OUTPUT_XLSX = "stocks_near_intraday_support_resistance.xlsx"
MAIN_SCRIPT = "OI_Support&Resistance.py"
TOKENS_FILE = "fyers_tokens.json"

app = Flask(__name__)

# ---------------- Token helpers ----------------
def load_tokens(filepath=TOKENS_FILE):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def is_token_valid(client_id, access_token):
    try:
        fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")
        resp = fyers.get_profile()
        return resp.get("code") == 200
    except Exception:
        return False

def refresh_token():
    # Runs your local authcode.py which must update fyers_tokens.json
    subprocess.run(["python", "authcode.py"], check=True)

def ensure_token():
    tokens = load_tokens()
    access_token = tokens.get("access_token", "")
    if not access_token or not is_token_valid(CLIENT_ID, access_token):
        refresh_token()

# ---------------- Data fetch ----------------
def fetch_fresh_data():
    """
    Ensures token is valid, runs your main script to rebuild the Excel,
    then reads the Excel into a DataFrame and returns it.
    """
    ensure_token()

    # Run your existing script which computes OI S/R and writes Excel
    subprocess.run(["python", MAIN_SCRIPT], check=True)

    # Read the latest Excel
    if not os.path.exists(OUTPUT_XLSX):
        raise FileNotFoundError(f"{OUTPUT_XLSX} not found after script run")

    df = pd.read_excel(OUTPUT_XLSX)
    cols = [c for c in ["symbol", "stock_price", "support_strike", "support_oi",
                        "resistance_strike", "resistance_oi", "nearest_level"] if c in df.columns]
    if cols:
        df = df[cols]

    return df

TABLE_CSS = """
<style>
body { font-family: Arial, sans-serif; margin: 24px; }
h1 { margin-bottom: 8px; }
.small { color: #666; margin-top: 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
th { background: #f2f2f2; position: sticky; top: 0; }
tr:nth-child(even) { background: #fafafa; }
.btn {
  display:inline-block; padding:8px 12px; border:1px solid #444; border-radius:6px;
  text-decoration:none; color:#111; font-weight:bold; margin-right:8px;
}
</style>
"""

PAGE_TMPL = """
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>OI Support &amp; Resistance</title>
{{ css }}
</head>
<body>
  <h1>OI Support &amp; Resistance</h1>
  <p class="small">Refreshed at: {{ ts }} &nbsp;|&nbsp; Press your browser’s refresh (F5) any time to fetch fresh data.</p>
  <p>
    <a class="btn" href="/">Refresh Now</a>
  </p>
  {{ table | safe }}
</body>
</html>
"""

@app.route("/")
def index():
    try:
        df = fetch_fresh_data()
        html_table = df.to_html(index=False)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        return render_template_string(PAGE_TMPL, table=html_table, ts=ts, css=TABLE_CSS)
    except Exception as e:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        return render_template_string(PAGE_TMPL, table=f"<p><b>Error:</b> {str(e)}</p>", ts=ts, css=TABLE_CSS)

def open_browser():
    time.sleep(1.5)
    try:
        webbrowser.open_new("http://127.0.0.1:5000/")
    except Exception:
        pass

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
