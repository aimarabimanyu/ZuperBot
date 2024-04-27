import os
import json
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load config.json
if os.path.exists(f"{os.path.realpath(os.path.dirname(__file__))}\config.json"):
    with open('config.json', 'r') as file:
        config = json.load(file)
else:
    sys.exit("config.json not found! please add config.json file to the root directory.")

# Load the environment variable
load_dotenv()

# Set the bot intents
intent = discord.Intents.all()
intent.members = True

# Create a bot instance
client = commands.Bot(command_prefix=config["prefix"], help_command=None, intents=intent)
client.config = config

initial_extensions = []
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        initial_extensions.append(f'cogs.{filename[:-3]}')

@client.event
async def on_ready():
    print('Bot is ready and online')
    await client.change_presence(status=discord.Status.online, activity=discord.Game(name=config["bot_activity"]))
    for cog in initial_extensions:
        try:
            print(f"Loading cog {cog}")
            await client.load_extension(cog)
            print(f"Loaded cog {cog}")
        except Exception as e:
            exc = "{}: {}".format(type(e).__name__, e)
            print("Failed to load cog {}\n{}".format(cog, exc))

client.run(os.getenv('DISCORD_API_TOKEN'))



