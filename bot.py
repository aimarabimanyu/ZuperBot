import os
import json
import sys
import random
import logging
import platform

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


# Set the loggers
class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"

    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record) -> str:
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")

        return formatter.format(record)


# Create a logger
logger = logging.getLogger(config["bot_name"])
logger.setLevel(logging.INFO)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())

# Create a file handler
file_handler = logging.FileHandler("discord_bot.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config = config
        self.logger = logger

    async def load_cogs(self) -> None:
        for extension in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
            if extension.endswith('.py'):
                if self.config["bot_feature"][extension[:-3]]:
                    extension = extension[:-3]
                    try:
                        await self.load_extension(f"cogs.{extension}")
                        self.logger.info(f"Loaded extension '{extension}'")
                    except Exception as e:
                        exception = f"{type(e).__name__}: {e}"
                        self.logger.error(f"Failed to load extension {extension}, {exception}")

    @tasks.loop(minutes=30)
    async def update_status(self) -> None:
        await self.change_presence(activity=discord.Game(random.choice(config["bot_activity"])))

    @update_status.before_loop
    async def before_status_task(self) -> None:
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        self.logger.info("-------------------------------")
        await self.load_cogs()
        self.update_status.start()


# Load the environment variable
load_dotenv()

bot = DiscordBot(command_prefix=config["prefix"], help_command=None, intents=intent, config=config)
bot.run(os.getenv('DISCORD_API_TOKEN'))
