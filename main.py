import requests
import discord
import os
#🌟 remember pip3 install python-dotenv
from dotenv import load_dotenv


client = discord.Client()

load_dotenv()
TOKEN = os.getenv('TOKEN')

@client.event
async def on_ready():
    print(f'This: {client.user} has connected')

client.run(TOKEN)

if __name__ == "__main__":
    data = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"}).json()
    print(data)
