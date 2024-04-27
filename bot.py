import os
import json
import sys
import random

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv


# Load config.json
if os.path.exists(f"{os.path.realpath(os.path.dirname(__file__))}/config.json"):
    with open('config.json', 'r') as file:
        config = json.load(file)
else:
    sys.exit("config.json not found! please add config.json file to the root directory.")

# Set the bot intents
intent = discord.Intents.all()
intent.members = True


class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.config = config

    async def load_cogs(self) -> None:
        for extension in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
            if extension.endswith('.py'):
                extension = extension[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    print(f"Failed to load extension {extension}\n{exception}")

    @tasks.loop(minutes=30)
    async def update_status(self) -> None:
        await self.change_presence(activity=discord.Game(random.choice(config["bot_activity"])))

    @update_status.before_loop
    async def before_status_task(self) -> None:
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        await self.load_cogs()
        self.update_status.start()


# Load the environment variable
load_dotenv()

bot = DiscordBot(command_prefix=config["prefix"], help_command=None, intents=intent, config=config)
bot.run(os.getenv('DISCORD_API_TOKEN'))
