import requests


# checks the current price of the pair according to binance data
def get_currency(symbol, return_code=False):
    ans = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol}).json()

    # if there is an invalid symbol nothing is returned
    if "code" in ans and ans["code"] != 200:
        if return_code:
            return None, ans['code']
        return None, None

    if 'symbol' not in ans:
        return None, None

    return float(ans['price']), None


# checks to see if the pair is listed on binance
def is_valid_pair(symbol):
    sym = symbol.upper().strip()
    return sym in requests.get("https://api.binance.com/api/v3/ticker/price").json(), sym
