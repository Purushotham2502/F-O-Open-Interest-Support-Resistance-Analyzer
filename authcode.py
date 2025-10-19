import subprocess
import json
from urllib.parse import urlparse, parse_qs
from fyers_apiv3 import fyersModel




tokens = load_tokens("fyers_tokens.json")
CLIENT_ID= tokens.get("client_id")  # load client_id here instead of hardcoded string
access_token = tokens.get("access_token")
# ---------- Fyers Auth Details ----------
tokens = load_tokens("fyers_tokens.json")
CLIENT_ID= tokens.get("client_id")  # load client_id here instead of hardcoded string
CLIENT_SECRET = "YourClient_secret"  # Replace with your secret key
REDIRECT_URI = "https://www.google.com/"  # Must match your app settings
STATE = "sample_state"
GRANT_TYPE = "authorization_code"

TOKEN_FILE = "fyers_tokens.json"

# ---------- Helper functions ----------
def save_tokens(filepath, tokens):
    with open(filepath, "w") as f:
        json.dump(tokens, f)
    print(f"Tokens saved to {filepath}")


def load_tokens(filepath):
    try:
        with open(filepath, "r") as f:
            tokens = json.load(f)
        return tokens
    except FileNotFoundError:
        print("Token file not found. Please authenticate first.")
        return None


# ---------- Prepare auth URL ----------
auth_url = (
    f"https://api-t1.fyers.in/api/v3/generate-authcode?"
    f"client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state={STATE}"
)

# ---------- Chrome paths ----------
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
profile_path = r"C:\Users\kodid\AppData\Local\Google\Chrome\User Data"

# ---------- Open Chrome to authorize ----------
subprocess.Popen([chrome_path, f"--user-data-dir={profile_path}", auth_url])
print(" Chrome opened with your profile. Log in manually and pass captcha.")

# ---------- Wait for manual login ----------
input("Once login is complete and you are redirected to the redirect URL, press Enter here...")

# ---------- Capture redirected URL ----------
redirected_url = input("Paste the full redirected URL here: ").strip()

# ---------- Extract auth code ----------
parsed = urlparse(redirected_url)
params = parse_qs(parsed.query)
auth_code = params.get("auth_code", [""])[0]

if not auth_code:
    print("Failed to capture auth code. Check the URL you pasted.")
    exit()

print("Auth code captured:", auth_code)

# ---------- Exchange auth code for tokens ----------
session = fyersModel.SessionModel(
    client_id=CLIENT_ID,
    secret_key=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    response_type="code",
    grant_type=GRANT_TYPE,
)
session.set_token(auth_code)
response = session.generate_token()

if "access_token" in response and "refresh_token" in response:
    print(" Access Token:", response["access_token"])
    print(" Refresh Token:", response["refresh_token"])

    # ---------- Save tokens ----------
    tokens = {
        "access_token": response["access_token"],
        "refresh_token": response["refresh_token"],
    }
    save_tokens(TOKEN_FILE, tokens)
else:
    print(" Failed to get tokens:", response)

