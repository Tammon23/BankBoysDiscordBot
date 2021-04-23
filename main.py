import requests
import discord

if __name__ == "__main__":
    data = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"}).json()
    print(data)
