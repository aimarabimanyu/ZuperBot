import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load the environment variable
load_dotenv()

# Set the bot intents
intent = discord.Intents.all()
intent.members = True

# Create a bot instance
client = commands.Bot(command_prefix='!', help_command=None, intents=intent)

initial_extensions = []
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        initial_extensions.append(f'cogs.{filename[:-3]}')

@client.event
async def on_ready():
    print('Bot is ready and online')
    await client.change_presence(status=discord.Status.online, activity=discord.Game("Ngocok Pake Sabun"))
    for cog in initial_extensions:
        try:
            print(f"Loading cog {cog}")
            await client.load_extension(cog)
            print(f"Loaded cog {cog}")
        except Exception as e:
            exc = "{}: {}".format(type(e).__name__, e)
            print("Failed to load cog {}\n{}".format(cog, exc))

client.run('MTIzMjk1NTIzOTc1NDIzNTk4Ng.G-dy22.4DZzYf7LTneFhtdBPue5zniZ5vczuYi9dpuzBA')



