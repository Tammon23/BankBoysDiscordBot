import time
import logging
from discord.ext import commands
from database import Database as db


class Wallet(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.db = db()
        self.db.connect_to_db()

    @staticmethod
    def db_deposit(conn, guild, user, coinsymbol, price, savedate, quantity):
        with conn.cursor() as cur:
            # inserting into the db the new data
            cur.execute("INSERT INTO wallet (guildid, userid, coinsymbol, price, savedate, quantity) VALUES (%2, %s, %s, %s, %s, %s);"
                        , (guild, user, coinsymbol, price, savedate, quantity))

        conn.commit()
        logging.debug("deposit(): status message: %s", cur.statusmessage)

    @commands.command(help="!deposit coin, price")
    async def deposit(self, ctx, *args):
        if len(args) != 3:
            await ctx.send("Incorrect usage.")

        else:
            coin, price, quantity = args
            price = str(price)
            price.replace("$", "")

            guild = str(ctx.guild.id)
            author = str(ctx.author.id)

            try:
                self.db.run_transaction(lambda conn: self.db_deposit(conn, guild, author, coin, price, time.time_ns(), quantity))
                await ctx.send(f"Updating wallet successful!")

            except ValueError as ve:
                logging.debug(f"deposit(ctx, *args) failed {ve}")
                await ctx.send(f"Updating wallet failed!")


def setup(client):
    client.add_cog(Wallet(client))
