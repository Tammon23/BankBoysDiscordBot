import os
import time
import random
import logging
import psycopg2
from dotenv import load_dotenv
from psycopg2.errors import SerializationFailure


class Database:
    conn = None

    def __init__(self):
        pass

    def connect_to_db(self):
        if self.conn is not None:
            return self.conn

        load_dotenv()
        self.conn = psycopg2.connect(os.getenv('COCKROACHDB'))
        print("New db connection.")

        return self.conn

    def run_transaction(self, op, max_retries=3):
        """
        Execute the operation *op(conn)* retrying serialization failure.

        If the database returns an error asking to retry the transaction, retry it
        *max_retries* times before giving up (and propagate it).
        """

        if self.conn is None:
            raise TypeError("Connection should not be None. Did you run connect_to_db()?")

        # leaving this block the transaction will commit or rollback
        # (if leaving with an exception)
        with self.conn:
            for retry in range(1, max_retries + 1):
                try:
                    result = op(self.conn)

                    # If we reach this point, we were able to commit, so we break
                    # from the retry loop.
                    return result

                except SerializationFailure as e:
                    # This is a retry error, so we roll back the current
                    # transaction and sleep for a bit before retrying. The
                    # sleep time increases for each failed transaction.
                    logging.debug("got error: %s", e)
                    self.conn.rollback()
                    logging.debug("EXECUTE SERIALIZATION_FAILURE BRANCH")
                    sleep_ms = (2 ** retry) * 0.1 * (random.random() + 0.5)
                    logging.debug("Sleeping %s seconds", sleep_ms)
                    time.sleep(sleep_ms)

                except psycopg2.Error as e:
                    logging.debug("got error: %s", e)
                    logging.debug("EXECUTE NON-SERIALIZATION_FAILURE BRANCH")
                    raise e

            raise ValueError(f"Transaction did not succeed after {max_retries} retries")