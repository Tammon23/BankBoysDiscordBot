import sys
import time
import logging
from discord import Embed, Colour
from discord.ext import commands
from database import Database as db
from datetime import datetime
from embed_helper import Constants
from crypto import get_currency, is_valid_pair


class Wallet(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.db = db()
        self.db.connect_to_db()

    @staticmethod
    def db_deposit(conn, guild, user, coinsymbol, price, savedate, quantity):
        with conn.cursor() as cur:
            # inserting into the db the new data
            cur.execute(
                "INSERT INTO wallet (guildid, userid, coinsymbol, price, savedate, quantity) VALUES (%s, %s, %s, %s, %s, %s);"
                , (guild, user, coinsymbol, price, savedate, quantity))

        conn.commit()
        logging.debug("deposit(): status message: %s", cur.statusmessage)

    @commands.command(help="!deposit [COIN] [PRICE] [QUANTITY]")
    async def deposit(self, ctx, *args):
        if len(args) != 3:
            await ctx.send("Incorrect usage.")

        else:
            coin, price, quantity = args
            r, coin = is_valid_pair()
            if r:
                try:
                    quantity = float(quantity)
                    price = str(price)
                    price.replace("$", "")

                    guild = str(ctx.guild.id)
                    author = str(ctx.author.id)

                    try:
                        self.db.run_transaction(
                            lambda conn: self.db_deposit(conn, guild, author, coin, price, time.time_ns(), quantity))
                        await ctx.send(f"Updating wallet successful!")

                    except ValueError as ve:
                        logging.debug(f"deposit(ctx, *args) failed {ve}")
                        print(ve, file=sys.stderr)
                        await ctx.send(f"Updating wallet failed!")

                except ValueError:
                    await ctx.send("Incorrect usage.")
            else:
                await ctx.send(f"{coin} is not listed on binance. Is it a valid pair?")

    @staticmethod
    def db_get_wallet(conn, guild, user):
        with conn.cursor() as cur:
            # inserting into the db the new data
            cur.execute("select price, coinsymbol, savedate, quantity from wallet where guildid = %s and userid = %s",
                        (guild, user))

            result = cur.fetchall()

        # grouping the coins by symbol
        data = {}
        for r in result:
            price, sym, date, quantity = r
            if sym in data:
                data[sym].append((price, date, quantity))
            else:
                data[sym] = [(price, date, quantity)]

        logging.debug("db_get_wallet(): status message: %s", cur.statusmessage)
        return data

    @commands.command(help="!wallet")
    async def wallet(self, ctx, *args):
        net_worth = 0
        guild = str(ctx.guild.id)
        author = str(ctx.author.id)
        current_prices = {}
        coins = {}
        buy_prices = []
        quantities = []
        saved_dates = []
        embeds = []
        page = 1
        num_fields = 0

        try:
            # getting the data
            result = self.db.run_transaction(lambda conn: self.db_get_wallet(conn, guild, author))

            if len(result) == 0:
                embed = Embed(
                    title=f"{ctx.author}'s current Wallet" + "" if page == 1 else f" Page {[page]}",
                    colour=Colour(0xFF00FF),
                    type="rich",
                    description='**--------------------------------------------------------------------------------------------------**\n'
                                'Wallet is empty.'
                )
                await ctx.send(embed=embed)

            else:
                # formulating the strings of how the data should be displayed
                # by iterating through each saved coin
                for c in result:

                    cprice, code = get_currency(c)
                    current_prices[c] = cprice

                    for investment in result[c]:
                        price, date, quantity = investment

                        # making sure that in the case the api service removes a coin from
                        # their api, then nothing will break

                        if cprice is not None:
                            net_worth += (quantity * cprice)

                        buy_prices.append(f"> ${price}")
                        saved_dates.append(str(datetime.fromtimestamp(date / 1e+9))[:19])
                        quantities.append(('%f' % quantity).rstrip('0').rstrip('.'))

                    coins[c] = (buy_prices.copy(), quantities.copy(), saved_dates.copy())

                    buy_prices.clear()
                    quantities.clear()
                    saved_dates.clear()

                # combining some of the strings to be put into a single string
                # this is based on the max character limit of FIELD_VALUE_LIMIT from constants
                reduced_strings = []
                for c in coins:
                    reduce_start_index = buy_length = quantity_length = date_length = 0
                    for index in range(len(coins[c][0])):
                        if buy_length + len(coins[c][0][index]) > Constants.FIELD_VALUE_LIMIT.value \
                                or quantity_length + len(coins[c][1][index]) > Constants.FIELD_VALUE_LIMIT.value \
                                or date_length + len(coins[c][2][index]) > Constants.FIELD_VALUE_LIMIT.value:

                            reduced_strings.append(('\n'.join(coins[c][0][reduce_start_index:index]),
                                                    '\n'.join(coins[c][1][reduce_start_index:index]),
                                                    '\n'.join(coins[c][2][reduce_start_index:index])))

                            reduce_start_index = index
                            buy_length = len(coins[c][0][index])
                            quantity_length = len(coins[c][1][index])
                            date_length = len(coins[c][2][index])

                        else:
                            buy_length += len(coins[c][0][index])
                            quantity_length += len(coins[c][1][index])
                            date_length += len(coins[c][2][index])

                    # if the following if statement is true, then we didn't merge
                    # the last few strings into a new string
                    if reduce_start_index != index:
                        reduced_strings.append(('\n'.join(coins[c][0][reduce_start_index:index]),
                                                '\n'.join(coins[c][1][reduce_start_index:index]),
                                                '\n'.join(coins[c][2][reduce_start_index:index])))

                    # similar to the above condition, this condition is saying "if the coin only has 1 entry then save
                    # the entry as the shortest form"
                    if len(coins[c][0]) == 1:
                        reduced_strings.append((coins[c][0][0], coins[c][1][0], coins[c][2][0]))

                    coins[c] = reduced_strings.copy()
                    reduced_strings.clear()

                # create the embeds from here on out, each tuple is 3 fields
                embed = Embed(
                    title=f"{ctx.author}'s current Wallet" + "" if page == 1 else f" Page {page}",
                    colour=Colour(0xFF00FF),
                    type="rich",
                    description='**--------------------------------------------------------------------------------------------------**'
                )
                embed.set_footer(text="Pairs calculated via Binance")

                for c in coins:
                    # if adding these 3 fields would exceed the allowed amount
                    # make a new embed and save the old one someone where else
                    first_field = True
                    if num_fields + 5 > Constants.FIELD_LIMIT.value:
                        embeds.append(embed.copy())
                        page += 1
                        num_fields = 0

                        embed = Embed(
                            title=f"{ctx.author}'s current Wallet" + "" if page == 1 else f" Page {page}",
                            colour=Colour(0xFF00FF),
                            type="rich",
                            description='**--------------------------------------------------------------------------------------------------**'
                        )
                        embed.set_footer(text="Pairs calculated via Binance")

                    num_fields += 4
                    embed.add_field(name=f'Coin/Pair: {c}', value=f"Current Price: {'$' + str(current_prices[c]) if current_prices[c] is not None else 'Unknown'}", inline=False)

                    for row in coins[c]:
                        price, quantity, date = row
                        embed.add_field(name="Buy Price" if first_field else Constants.EMPTY.value, value=price,
                                        inline=True)
                        embed.add_field(name="Quantity" if first_field else Constants.EMPTY.value, value=quantity,
                                        inline=True)
                        embed.add_field(name="Saved at" if first_field else Constants.EMPTY.value, value=date,
                                        inline=True)
                        embed.add_field(name=Constants.EMPTY.value, value=Constants.EMPTY.value, inline=False)

                        first_field = False

                # if this statement is true, then we did not save the last embed
                if num_fields != 0:
                    embeds.append(embed)

                # Adding the worth up for each price in the footer of the last embed
                embeds[-1].set_footer(text=f"Networth of known coins is ${net_worth} USDT")
                for e in embeds:
                    await ctx.send(embed=e)

        except Exception as e:
            print(str(e))

        # embed.set_author(name="Author Plus ultra")
        # embed.set_footer(text=f"wallet balance calculated via biance api {'-'*int(spacesize)}")


def setup(client):
    client.add_cog(Wallet(client))
