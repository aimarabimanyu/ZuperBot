import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()


class Greetings(commands.Cog, name='Greetings'):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self,member):
        welcome_channel = self.client.get_channel(int(os.getenv('WELCOME_CHANNEL_ID')))
        embed = discord.Embed()
        embed.set_image(url="https://i.imgur.com/Le2xPHN.png")

        await welcome_channel.send(f"Selamat datang {member.mention}, jangan lupa untuk nyalakan notifikasi pada "
                                   f"<#{os.getenv('GARAPAN_CHANNEL_ID')}> untuk dapat update garapan baru dengan melakukan \n\n"
                                   f"> Klik kanan di <#{os.getenv('GARAPAN_CHANNEL_ID')}> "
                                   f"> Kik `Notification Setting` "
                                   f"> Centang `New Posts Created` \n\n"
                                   f"Contoh: ", embed=embed)


async def setup(client) -> None:
    await client.add_cog(Greetings(client))
