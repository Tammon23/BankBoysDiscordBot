import sys
import time
import asyncio
import logging
import psycopg2
from datetime import datetime
from discord.ext import commands
from discord import Embed, Colour
from embed_helper import Constants
from database import Database as db
from crypto import get_currency, is_valid_pair


class Wallet(commands.Cog, description="A wallet feature that allows you to track coin statistics"):
    def __init__(self, client):
        self.client = client
        self.db = db()
        self.db.connect_to_db()

    @commands.group()
    async def wallet(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid wallet command passed...')

    @staticmethod
    def db_deposit(conn, guild, user, coinsymbol, price, savedate, quantity):
        with conn.cursor() as cur:
            # inserting into the db the new data
            cur.execute(
                "INSERT INTO wallet (guildid, userid, coinsymbol, price, savedate, quantity) VALUES (%s, %s, %s, %s, %s, %s);"
                , (guild, user, coinsymbol, price, savedate, quantity))

        conn.commit()
        logging.debug("db_deposit(): status message: %s", cur.statusmessage)

    @wallet.command(help="!wallet deposit [COIN] [PRICE] [QUANTITY]")
    async def deposit(self, ctx, *args):
        # checking for incorrect command usage
        if len(args) != 3 and len(args) != 2:
            await ctx.send("Incorrect usage.")

        # if the usage was correct
        else:

            if len(args) == 2:
                coin, quantity = args
                r, coin = is_valid_pair(coin)
                price, _ = get_currency(coin)

                if price is None:
                    await ctx.send(f"Could not find price on Binance for {coin}, please input price. [{ctx.author.mention}]")
                    return

            else:
                # dividing the arguments into subparts
                coin, price, quantity = args
                r, coin = is_valid_pair(coin)
                price = price.replace("$", "")

            quantity = float(quantity)

            channel = ctx.channel.id
            guild = str(ctx.guild.id)
            author = str(ctx.author.id)

            # if it's a valid pair, deposit it into the database
            if r:
                try:
                    self.db.run_transaction(
                        lambda conn: self.db_deposit(conn, guild, author, coin, price,
                                                     str(datetime.utcfromtimestamp(time.time())), quantity))
                    await ctx.send("Updating wallet successful!")

                except ValueError as ve:
                    logging.debug(f"deposit(ctx, *args) failed {ve}")
                    print(ve, file=sys.stderr)
                    await ctx.send("Updating wallet failed!")

            # if the pair is invalid ask for confirmation to add it
            # to the database via reactions
            else:
                message = await ctx.send(f"{coin} is not listed on binance. List anyways? react with ✅ or ❎ [{ctx.author.mention}]")
                await message.add_reaction("✅")
                await message.add_reaction("❎")

                # check function to verify that the user who sent the command responds
                # with one of the valid emojis
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["✅","❎"] and reaction.message.channel.id == channel

                try:
                    # waiting up to 60s for the reaction to be added
                    # if the time ran out then the asyncio.TimeoutError is called
                    reaction, user = await self.client.wait_for('reaction_add', timeout=10.0, check=check)

                    # if the reaction is a checkmark, deposit the data into the database
                    if str(reaction) == "✅":
                        try:
                            self.db.run_transaction(
                                lambda conn: self.db_deposit(conn, guild, author, coin, price,
                                                             str(datetime.utcfromtimestamp(time.time())), quantity))
                            await ctx.send("Updating wallet successful!")

                        except ValueError as ve:
                            logging.debug(f"deposit(ctx, *args) failed {ve}")
                            print(ve, file=sys.stderr)
                            await ctx.send("Updating wallet failed!")

                    # if the reaction is an x, then don't deposit it
                    else:
                        await ctx.send(f"{coin} was not added to the wallet!")

                # ran out of time waiting for a reaction
                except asyncio.TimeoutError:
                    pass
                    # called when the timeout runs out
                    # do nothing

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

    @staticmethod
    def data_to_strings(result):
        """ Used to calculate the networth of the wallet & used to prepare the
            inputs for use in the embed. Prepartion is done converting each value
            into a string and adding special symbols when needed (i.e., $) """

        net_worth = 0
        buy_prices = []
        quantities = []
        saved_dates = []
        coins = {}
        current_prices = {}

        for c in result:

            cprice, code = get_currency(c)
            current_prices[c] = [cprice, 0]

            for investment in result[c]:
                price, date, quantity = investment
                current_prices[c][1] += price * quantity

                # making sure that in the case the api service removes a coin from
                # their api, then nothing will break

                if cprice is not None:
                    net_worth += (quantity * cprice)

                buy_prices.append(f"> ${price:.9f}".rstrip('0').rstrip('.'))
                saved_dates.append(date)
                quantities.append(('%f' % quantity).rstrip('0').rstrip('.'))

            coins[c] = (buy_prices.copy(), quantities.copy(), saved_dates.copy())

            buy_prices.clear()
            quantities.clear()
            saved_dates.clear()

        return net_worth, current_prices, coins

    @staticmethod
    def reduce_strings(coins):
        """ The largest size string must be the embed max value limit. This function merges strings
            in a way that it adheres to the rule listed above, while maintaining the structure of each
            conjoined string (not cutoff midway) """

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
                reduced_strings.append(('\n'.join(coins[c][0][reduce_start_index:]),
                                        '\n'.join(coins[c][1][reduce_start_index:]),
                                        '\n'.join(coins[c][2][reduce_start_index:])))

            # similar to the above condition, this condition is saying "if the coin only has 1 entry then save
            # the entry as the shortest form"
            if len(coins[c][0]) == 1:
                reduced_strings.append((coins[c][0][0], coins[c][1][0], coins[c][2][0]))

            coins[c] = reduced_strings.copy()
            reduced_strings.clear()

        return coins

    @staticmethod
    def make_embeds(coins, current_prices, author, net_worth):
        """ This function is used to combine a series of coins into a
            embed (or more than one if wallet is big) """

        embeds = []
        num_fields = 0
        page = 1

        embed = Embed(
            title=f"{author}'s current Wallet" + "" if page == 1 else f" Page {page}",
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
                    title=f"{author}'s current Wallet" + "" if page == 1 else f" Page {page}",
                    colour=Colour(0xFF00FF),
                    type="rich",
                    description='**--------------------------------------------------------------------------------------------------**'
                )
                embed.set_footer(text="Pairs calculated via Binance")

            num_fields += 4
            embed.add_field(name=f'Coin/Pair: {c}',
                            value=f"**Current Price**: {'$' + f'{current_prices[c][0]:,}' if current_prices[c][0] is not None else 'Unknown'} **Wallet Value**: ${current_prices[c][1]:,} USDT",
                            inline=False)

            for row in coins[c]:
                price, quantity, date = row
                embed.add_field(name="Buy Price" if first_field else Constants.EMPTY.value, value=price,
                                inline=True)
                embed.add_field(name="Quantity" if first_field else Constants.EMPTY.value, value=quantity,
                                inline=True)
                embed.add_field(name="Saved at (UTC Time)" if first_field else Constants.EMPTY.value, value=date,
                                inline=True)
                embed.add_field(name=Constants.EMPTY.value, value=Constants.EMPTY.value, inline=False)

                first_field = False

        # if this statement is true, then we did not save the last embed
        if num_fields != 0:
            embeds.append(embed)

        # Adding the worth up for each price in the footer of the last embed
        embeds[-1].set_footer(text=f"Net worth of known coins is ${net_worth:,} USDT")
        return embeds

    @wallet.command(help="!wallet show")
    async def show(self, ctx):
        guild = ctx.guild
        author = ctx.author

        try:
            # getting the data
            result = self.db.run_transaction(lambda conn: self.db_get_wallet(conn, str(guild.id), str(author.id)))

            if len(result) == 0:
                embed = Embed(
                    title=f"{ctx.author}'s current Wallet",
                    colour=Colour(0xFF00FF),
                    type="rich",
                    description='**--------------------------------------------------------------------------------------------------**\n'
                                'Wallet is empty.'
                )
                await ctx.send(embed=embed)

            else:
                # formulating the strings of how the data should be displayed
                # by iterating through each saved coin

                net_worth, current_prices, coins = self.data_to_strings(result)

                # combining some of the strings to be put into a single string
                # this is based on the max character limit of FIELD_VALUE_LIMIT from constants
                coins = self.reduce_strings(coins)

                # create the embeds from here on out, each tuple is 3 fields
                embeds = self.make_embeds(coins, current_prices, str(author), net_worth)
                for e in embeds:
                    await ctx.send(embed=e)

        except ValueError as e:
            print(str(e))

    @staticmethod
    def db_Remove(conn, guild, user, buyprice, quantity, savedate, symbol):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM wallet WHERE guildid = %s AND userid = %s AND price = %s AND quantity = %s AND "
                        "savedate = %s AND coinsymbol = %s;",
                        (guild, user, buyprice, quantity, savedate, symbol))

            conn.commit()
            logging.debug("db_walletremove(): status message: %s", cur.statusmessage)

            return cur.rowcount

    @wallet.command(help="!wallet remove [COIN] [PRICE] [QUANTITY] [DATE] [TIME]")
    async def remove(self, ctx, *args):
        if len(args) != 5:
            await ctx.send("Incorrect usage!")
        else:

            symbol, price, quantity, date, timee = args
            price = price.replace("$", "")
            saved_at = date + " " + timee
            guild = str(ctx.guild.id)
            author = str(ctx.author.id)
            symbol = symbol.upper()

            try:
                amount_deleted = self.db.run_transaction(
                    lambda conn: self.db_Remove(conn, guild, author, price, quantity, saved_at, symbol))

                if amount_deleted == 0:
                    await ctx.send("Nothing matching does arguments was found in the wallet!")

                else:
                    await ctx.send("Deleting from wallet successful!")

            except ValueError as ve:
                logging.debug(f"remove(ctx, *args) failed {ve}")
                print(ve)
                await ctx.send("Deleting from wallet failed!")

    @staticmethod
    def db_transfer_wallet(conn, old_guild, user, new_guild):
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO wallet (guildid, userid, savedate, price, quantity, coinsymbol)
                        SELECT %s, userid, savedate, price, quantity, coinsymbol
                        FROM wallet w1
                        WHERE guildid = %s AND userid = %s AND NOT EXISTS(
                            SELECT guildid, userid, savedate
                            FROM wallet w2
                            WHERE w2.guildid = %s AND w2.userid = w1.userid AND w2.savedate = w1.savedate)""",
                        (new_guild, old_guild, user, new_guild))

            conn.commit()
            logging.debug("transfer_wallet(): status message: %s", cur.statusmessage)

            return cur.rowcount

    @wallet.command(help="!wallet send [SERVER_ID]")
    async def send(self, ctx, *args):
        if len(args) != 1:
            await ctx.send("Incorrect usage!")
        else:
            guild = str(ctx.guild.id)
            author = str(ctx.author.id)
            alternative_guild_id = int(args[0])

            try:
                amount_sent = self.db.run_transaction(
                    lambda conn: self.db_transfer_wallet(conn, guild, author, alternative_guild_id))

                if amount_sent == 0:
                    await ctx.send("No items were sent, is your wallet empty?")

                else:
                    await ctx.send(f"Sent {amount_sent} items to GuildID: {alternative_guild_id}")

            except ValueError as ve:
                logging.debug(f"send(ctx, *args) failed {ve}")
                print(ve)
                await ctx.send(f"Sending wallet to GuildID: {alternative_guild_id} failed!")

            except psycopg2.errors.UniqueViolation:
                await ctx.send(f"No new items to merge from GuildID: {alternative_guild_id}")

    @wallet.command(help="!wallet get [SERVER_ID]")
    async def get(self, ctx, *args):
        if len(args) != 1:
            await ctx.send("Incorrect usage!")
        else:
            guild = str(ctx.guild.id)
            author = str(ctx.author.id)
            alternative_guild_id = int(args[0])

            try:
                amount_recieved = self.db.run_transaction(
                    lambda conn: self.db_transfer_wallet(conn, alternative_guild_id, author, guild))

                if amount_recieved == 0:
                    await ctx.send("No items were received, is your wallet empty?")

                else:
                    await ctx.send(f"Received {amount_recieved} items from GuildID: {alternative_guild_id}")

            except ValueError as ve:
                logging.debug(f"get(ctx, *args) failed {ve}")
                print(ve)
                await ctx.send(f"Getting wallet from GuildID: {alternative_guild_id} failed!")

            except psycopg2.errors.UniqueViolation:
                await ctx.send(f"No new items to merge from GuildID: {alternative_guild_id}")

    @staticmethod
    def db_purge(conn, guild, user):
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM wallet WHERE guildid = %s AND userid = %s",
                (guild, user))

            conn.commit()
            logging.debug("db_purge(): status message: %s", cur.statusmessage)

            return cur.rowcount

    @wallet.command(help="!wallet purge")
    async def purge(self, ctx, *args):
        channel = ctx.channel.id
        guild = str(ctx.guild.id)
        author = str(ctx.author.id)

        message = await ctx.send(f"Purging is not reversible. Are you sure you want to? [{ctx.author.mention}]")
        await message.add_reaction("✅")
        await message.add_reaction("❎")

        # check function to verify that the user who sent the command responds
        # with one of the valid emojis
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❎"] and reaction.message.channel.id == channel

        try:
            # waiting up to 60s for the reaction to be added
            # if the time ran out then the asyncio.TimeoutError is called
            reaction, user = await self.client.wait_for('reaction_add', timeout=10.0, check=check)

            # if the reaction is a checkmark, deposit the data into the database
            if str(reaction) == "✅":
                try:
                    purge_amount = self.db.run_transaction(lambda conn: self.db_purge(conn, guild, author))

                    if purge_amount == 0:
                        await ctx.send(f"No items were purged from the wallet. If this is a bug tell an admin! [{ctx.author.mention}]")
                    else:
                        await ctx.send(f"{purge_amount} item(s) purged from the wallet. [{ctx.author.mention}]")

                except ValueError as ve:
                    logging.debug(f"purge(ctx, *args) failed {ve}")
                    print(ve, file=sys.stderr)
                    await ctx.send(f"Purging wallet failed! [{ctx.author.mention}]")

            # if the reaction is an x, then don't deposit it
            else:
                await ctx.send(f"Wallet will not be purged! [{ctx.author.mention}]")

        # ran out of time waiting for a reaction
        except asyncio.TimeoutError:
            pass
            # called when the timeout runs out
            # do nothing


def setup(client):
    client.add_cog(Wallet(client))
