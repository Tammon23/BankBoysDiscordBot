import os
import discord
import requests
from discord.ext import commands

from dotenv import load_dotenv

bot = commands.Bot(command_prefix='!', help_command=None)

@bot.event
async def on_ready():
    print(f'This: {bot.user} has connected')
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("!help"))

# ctx is short for context
# Joshy commands 🚀
@bot.command()
async def ping(ctx):
    await ctx.send(f"Bot latency is: {round(bot.latency * 1000)}ms")


@bot.command()
async def help(ctx):
    await ctx.send(
        "🚀 🚀 🚀 🚀 🚀 🚀 🚀 🚀 \n"
        "!ping:[no args], returns the bot latency\n"
        "!help:[no args], returns usable commands\n"
        "!coin:[any coin e.g btcusdt] returns value of the coin")


@bot.command(help="!coin <symbol>")
async def coin(ctx, args):
    ref = args.upper()
    print(f'Symbol: {ref}')
    values = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": ref}).json()
    for key, value in values.items():
        print(f'{key} : {value}')
        print(value)
        await ctx.send(f'{key} : {value}')

# loading the cogs
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        print(f"{filename[:-3]} Cog loaded")
        bot.load_extension(f"cogs.{filename[:-3]}")

if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv('TOKEN')
    bot.run(TOKEN)
