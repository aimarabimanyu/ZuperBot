import os

import discord
from discord.ext import commands, tasks
from web3 import Web3
from dotenv import load_dotenv


class TreasuryMonitoring(commands.Cog, name='Treasury Monitoring'):
    def __init__(self, client) -> None:
        self.client = client
        self.config = self.client.config
        self.logger = self.client.logger
        self.treasury_monitoring.start()

    @tasks.loop(minutes=1)
    async def treasury_monitoring(self) -> None:
        treasury_rpc_url = os.getenv('RPC_URL')
        treasury_address = self.config['treasury_monitoring_settings']['treasury_address']
        treasury_message = f"{self.config['treasury_monitoring_settings']['treasury_message']}"

        w3 = Web3(Web3.HTTPProvider(treasury_rpc_url))
        checksum_treasury_address = w3.to_checksum_address(treasury_address)
        treasury_value = w3.eth.get_balance(checksum_treasury_address)
        treasury_value_in_ether = round(w3.from_wei(treasury_value, 'ether'), 4)

        await self.client.change_presence(activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=treasury_message.format(treasury_value=treasury_value_in_ether)
            )
        )

        self.logger.info(f"Bot presence updated | Treasury value: {treasury_value_in_ether} ETH")

    @treasury_monitoring.before_loop
    async def before_treasury_monitoring(self) -> None:
        await self.client.wait_until_ready()
        self.logger.info('Treasury monitoring is ready')


async def setup(client) -> None:
    load_dotenv()

    await client.add_cog(TreasuryMonitoring(client))
