import os
import asyncio
import discord
from discord.ext import commands, tasks
from web3 import Web3
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import threading
from waitress import serve
import sqlite3


app = Flask(__name__)
database = sqlite3.connect('data/data.db', timeout=5)
cursor = database.cursor()


class TreasuryMonitoring(commands.Cog, name='Treasury Monitoring'):
    def __init__(self, client) -> None:
        self.client = client
        self.config = self.client.config
        self.logger = self.client.logger
        self.w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))
        self.treasury_address = self.config['treasury_monitoring_settings']['treasury_address']
        self.usdc_contract = self.w3.eth.contract(
            address=self.config['treasury_monitoring_settings']['usdc_contract_address'],
            abi=self.config['treasury_monitoring_settings']['usdc_abi']
        )
        self.usdt_contract = self.w3.eth.contract(
            address=self.config['treasury_monitoring_settings']['usdt_contract_address'],
            abi=self.config['treasury_monitoring_settings']['usdt_abi']
        )
        self.last_block = self.w3.eth.block_number
        self.alchemy_webhook_payload_data = {}
        self.treasury_balance_presence.start()

    """
    Static method to censor the wallet address
    """
    @staticmethod
    def censor_wallet_address(address):
        return f"{address[:7]}...{address[-5:]}" if len(address) >= 20 else address

    """
    Update the bot presence with the treasury balance every 30 seconds
    """
    @tasks.loop(seconds=30)
    async def treasury_balance_presence(self) -> None:
        await self.client.get_cog('Database').db_initialization_event.wait()

        try:
            # Get the treasury balance
            checksum_treasury_address = self.w3.to_checksum_address(self.treasury_address)
            eth_balance = round(self.w3.from_wei(self.w3.eth.get_balance(checksum_treasury_address), 'ether'), 5)
            usdc_balance = round(self.usdc_contract.functions.balanceOf(checksum_treasury_address).call() / 10 ** 6, 2)
            usdt_balance = round(self.usdt_contract.functions.balanceOf(checksum_treasury_address).call() / 10 ** 6, 2)

            # Change the bot presence
            await self.client.change_presence(activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="Treasury Balance",
                    state="ETH: {0} | USDC: {1} | USDT: {2}".format(eth_balance, usdc_balance, usdt_balance),
                )
            )

            # Log the treasury balance
            self.logger.info(f"Bot presence updated | ETH: {eth_balance}, USDC: {usdc_balance}, USDT: {usdt_balance}")
        except Exception as e:
            self.logger.error(f"Failed to update bot presence | {e}")

    """
    Webhook endpoint to receive the transaction data from Alchemy API
    """
    async def alchemy_webhook(self):
        # Get the payload data from the webhook
        self.alchemy_webhook_payload_data = request.json

        # Call the transaction monitoring method to send the notification
        await self.transaction_monitoring()

        # Return the response
        return jsonify({'status': 'success'})

    """
    Send the notification to the target channel if the transaction is detected
    """
    async def transaction_monitoring(self) -> None:
        await self.client.get_cog('Database').db_initialization_event.wait()

        try:
            cursor.execute(
                "SELECT 1 FROM treasury_monitoring WHERE tx_hash = ?",
                (self.alchemy_webhook_payload_data['event']['activity'][0]['hash'],)
            )

            # Get the target channel to send the notification
            target_channel = self.client.get_channel(int(self.config['treasury_monitoring_settings']['target_channel_id']))

            # Create the embed message
            embed = discord.Embed(title="Transaction Detected", description="Outgoing transaction from the treasury address", color=discord.Color.orange())
            embed.add_field(name="Transaction Hash", value=f"{(self.alchemy_webhook_payload_data['event']['activity'][0]['hash'])}", inline=False)
            embed.add_field(name="Value", value=f"{self.alchemy_webhook_payload_data['event']['activity'][0]['value']} {self.alchemy_webhook_payload_data['event']['activity'][0]['asset']}",  inline=True)
            embed.add_field(name="Sender", value=self.censor_wallet_address(self.alchemy_webhook_payload_data['event']['activity'][0]['fromAddress']), inline=True)
            embed.add_field(name="Recipient", value=self.censor_wallet_address(self.alchemy_webhook_payload_data['event']['activity'][0]['toAddress']), inline=True)

            # Check if the transaction is outgoing or incoming and tx_hash is not already in the database
            if self.alchemy_webhook_payload_data['event']['activity'][0]['value'] > 0 and cursor.fetchone() is None:
                if self.alchemy_webhook_payload_data['event']['activity'][0]['fromAddress'].lower() == self.treasury_address.lower():
                    await target_channel.send(embed=embed)

                    # Insert the transaction hash into the database
                    cursor.execute(
                        """
                        INSERT INTO treasury_monitoring (
                            tx_hash, value, asset, from_address, to_address, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            self.alchemy_webhook_payload_data['event']['activity'][0]['hash'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['value'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['asset'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['fromAddress'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['toAddress'],
                            self.alchemy_webhook_payload_data['createdAt']
                        )
                    )

                    # Commit the all changes to the database
                    async with self.client.get_cog('Database').db_lock:
                        database.commit()

                    self.logger.info(
                        f"Outgoing transaction detected | Tx: {self.alchemy_webhook_payload_data['event']['activity'][0]['hash']}")
                if self.alchemy_webhook_payload_data['event']['activity'][0]['toAddress'].lower() == self.treasury_address.lower():
                    embed.description = "Incoming transaction to the treasury address"

                    await target_channel.send(embed=embed)

                    # Insert the transaction hash into the database
                    cursor.execute(
                        """
                        INSERT INTO treasury_monitoring (
                            tx_hash, value, asset, from_address, to_address, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            self.alchemy_webhook_payload_data['event']['activity'][0]['hash'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['value'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['asset'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['fromAddress'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['toAddress'],
                            self.alchemy_webhook_payload_data['event']['activity'][0]['blockTimestamp']
                        )
                    )

                    self.logger.info(
                        f"Incoming transaction detected | Tx: {self.alchemy_webhook_payload_data['event']['activity'][0]['hash']}")
        except Exception as e:
            self.logger.error(f"Failed to send the notification | {e}")

    """
    Run the treasury balance monitoring before the loop starts
    """
    @treasury_balance_presence.before_loop
    async def treasury_balance_monitoring_before_loop(self) -> None:
        await self.client.wait_until_ready()
        self.logger.info('Treasury balance monitoring is ready')


def run_flask(treasury_monitoring_instance, loop) -> None:
    def alchemy_webhook_handler():
        future = asyncio.run_coroutine_threadsafe(treasury_monitoring_instance.alchemy_webhook(), loop)
        result = future.result()
        return result

    app.add_url_rule('/alchemy_webhook', 'alchemy_webhook', alchemy_webhook_handler, methods=['GET', 'POST'])
    serve(app, host='0.0.0.0', port=5000, _quiet=True)


async def setup(client) -> None:
    load_dotenv()
    treasury_monitoring = TreasuryMonitoring(client)
    loop = asyncio.get_event_loop()
    threading.Thread(target=run_flask, args=(treasury_monitoring, loop)).start()
    await client.add_cog(treasury_monitoring)
