import requests
from discord.ext import commands
import os
# 🌟 remember pip3 install python-dotenv
from dotenv import load_dotenv

bot = commands.Bot(command_prefix='!', help_command=None)


@bot.event
async def on_ready():
    print(f'This: {bot.user} has connected')


# ctx is short for context
# joshy commands 🚀
@bot.command()
async def ping(ctx):
    await ctx.send(f"Bot latency is: {round(bot.latency * 1000)}ms")


@bot.command()
async def help(ctx):
    await ctx.send("🚀 🚀 🚀 🚀 🚀 🚀 🚀 🚀 \n!ping:[no args], returns the bot latency\n!help:[no args], returns usable commands\n!coin:[any coin e.g btcusdt] returns value of the coin")

@bot.command()
async def coin(ctx, args):
    ref = args.upper()
    print(f'Symbol: {ref}')
    values = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": ref}).json()
    for key, value in values.items():
        print(f'{key} : {value}')
        print(value)
        await ctx.send(f'{key} : {value}')


if __name__ == "__main__":
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            bot.load_extension(f"cogs.{filename[:-3]}")

    load_dotenv()
    # token for joshy jr
    TOKEN = os.getenv('TOKEN')
    bot.run(TOKEN)