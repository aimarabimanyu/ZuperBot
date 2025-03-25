import os
import json
import sys
import logging
import platform

import discord
from discord.ext import commands
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


# Set the loggers format and colors for discord bot
class LoggingFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\x1b[38m\x1b[1m",
        logging.INFO: "\x1b[34m\x1b[1m",
        logging.WARNING: "\x1b[33m\x1b[1m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[31m\x1b[1m",
    }
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    BLACK = "\x1b[30m"
    GREEN = "\x1b[32m"

    def format(self, record) -> str:
        log_color = self.COLORS[record.levelno]
        format = f"{self.BLACK}{self.BOLD}{{asctime}}{self.RESET} {log_color}{{levelname:<8}}{self.RESET} {self.GREEN}{self.BOLD}{{name}}{self.RESET} {{message}}"
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


# Initialize the logger and set the level
logger = logging.getLogger(config["bot_name"])
logger.setLevel(logging.INFO)

# Check if handlers are already added to avoid duplicate logs
if not logger.handlers:
    # Set log console handler and formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LoggingFormatter())

    # Create a log file handler and set the formatter
    file_handler = logging.FileHandler("data/discord_bot.log", encoding="utf-8", mode="w")
    file_handler.setFormatter(logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"))

    # Add the handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


# Initialize the bot
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

    async def setup_hook(self) -> None:
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        self.logger.info("-------------------------------")
        await self.load_cogs()


# Load the environment variable
load_dotenv()

bot = DiscordBot(command_prefix=config["prefix"], help_command=None, intents=intent, config=config)
bot.run(os.getenv('DISCORD_API_TOKEN'))
