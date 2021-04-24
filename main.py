import requests
import discord
from discord.ext import commands
import os
# 🌟 remember pip3 install python-dotenv
from dotenv import load_dotenv

bot = commands.Bot(command_prefix='!')

client = discord.Client()

load_dotenv()
TOKEN = os.getenv('TOKEN')


@client.event
async def on_ready():
    print(f'This: {client.user} has connected')


# client.run(TOKEN)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Bot latency is: {round(bot.latency * 1000)}ms")


bot.run(TOKEN)

if __name__ == "__main__":
    data = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"}).json()
    print(data)
