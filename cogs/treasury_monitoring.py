import os
import asyncio
import discord
from discord.ext import commands, tasks
from web3 import Web3
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import threading


app = Flask(__name__)


class TreasuryMonitoring(commands.Cog, name='Treasury Monitoring'):
    def __init__(self, client) -> None:
        self.client = client
        self.config = self.client.config
        self.logger = self.client.logger
        self.w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))
        self.treasury_address = self.config['treasury_monitoring_settings']['treasury_address']
        self.usdc_contract_address = self.config['treasury_monitoring_settings']['usdc_contract_address']
        self.usdc_abi = self.config['treasury_monitoring_settings']['usdc_abi']
        self.usdc_contract = self.w3.eth.contract(address=self.usdc_contract_address, abi=self.usdc_abi)
        self.usdt_contract_address = self.config['treasury_monitoring_settings']['usdt_contract_address']
        self.usdt_abi = self.config['treasury_monitoring_settings']['usdt_abi']
        self.usdt_contract = self.w3.eth.contract(address=self.usdt_contract_address, abi=self.usdt_abi)
        self.last_block = self.w3.eth.block_number
        self.alchemy_webhook_payload_data = {}
        self.treasury_balance_presence.start()

    @staticmethod
    def censor_wallet_address(address):
        if len(address) < 20:
            return address
        return f"{address[:7]}...{address[-5:]}"

    @tasks.loop(seconds=30)
    async def treasury_balance_presence(self) -> None:
        checksum_treasury_address = self.w3.to_checksum_address(self.treasury_address)
        eth_treasury_value = self.w3.eth.get_balance(checksum_treasury_address)
        eth_treasury_value = round(self.w3.from_wei(eth_treasury_value, 'ether'), 5)
        usdc_treasury_value = self.usdc_contract.functions.balanceOf(checksum_treasury_address).call()
        usdc_treasury_value = round(usdc_treasury_value / 10**6, 2)
        usdt_treasury_value = self.usdt_contract.functions.balanceOf(checksum_treasury_address).call()
        usdt_treasury_value = round(usdt_treasury_value / 10**6, 2)
        await self.client.change_presence(activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="ETH: {0} | USDC: {1} | USDT: {2}".format(eth_treasury_value, usdc_treasury_value, usdt_treasury_value)
            )
        )
        self.logger.info(f"Bot presence updated | ETH: {eth_treasury_value}, USDC: {usdc_treasury_value}, USDT: {usdt_treasury_value}")

    async def alchemy_webhook(self):
        self.alchemy_webhook_payload_data = request.json
        await self.transaction_monitoring()
        return jsonify({'status': 'success'})

    async def transaction_monitoring(self) -> None:
        transaction_monitoring_target_channel = self.client.get_channel(int(self.config['treasury_monitoring_settings']['target_channel_id']))

        embed = discord.Embed(
            title="Transaction Detected",
            description="Outgoing transaction from the treasury address",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Transaction Hash",
            value=f"{(self.alchemy_webhook_payload_data['event']['activity'][0]['hash'])}",
            inline=False
        )
        embed.add_field(
            name="Value",
            value=f"{self.alchemy_webhook_payload_data['event']['activity'][0]['value']} {self.alchemy_webhook_payload_data['event']['activity'][0]['asset']}",
            inline=True
        )
        embed.add_field(
            name="Sender",
            value=self.censor_wallet_address(self.alchemy_webhook_payload_data['event']['activity'][0]['fromAddress']),
            inline=True
        )
        embed.add_field(
            name="Recipient",
            value=self.censor_wallet_address(self.alchemy_webhook_payload_data['event']['activity'][0]['toAddress']),
            inline=True
        )

        if self.alchemy_webhook_payload_data['event']['activity'][0]['value'] > 0:
            if self.alchemy_webhook_payload_data['event']['activity'][0]['fromAddress'].lower() == self.treasury_address.lower():
                await transaction_monitoring_target_channel.send(embed=embed)

                self.logger.info(
                    f"Outgoing transaction detected | Tx: {self.alchemy_webhook_payload_data['event']['activity'][0]['hash']}")
            if self.alchemy_webhook_payload_data['event']['activity'][0]['toAddress'].lower() == self.treasury_address.lower():
                embed.description = "Incoming transaction to the treasury address"

                await transaction_monitoring_target_channel.send(embed=embed)

                self.logger.info(
                    f"Incoming transaction detected | Tx: {self.alchemy_webhook_payload_data['event']['activity'][0]['hash']}")

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


async def setup(client) -> None:
    load_dotenv()
    treasury_monitoring = TreasuryMonitoring(client)
    loop = asyncio.get_event_loop()
    threading.Thread(target=run_flask, args=(treasury_monitoring, loop)).start()
    await client.add_cog(treasury_monitoring)
