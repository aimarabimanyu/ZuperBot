import discord
from discord.ext import commands
import os
from dotenv import load_dotenv


def main():
    # Load the environment variable
    load_dotenv()

    # Set the bot intents
    intent = discord.Intents.all()
    intent.members = True

    # Create a bot instance
    client = commands.Bot(command_prefix='!', intents=intent)

    # Display message on terminal when bot is ready
    @client.event
    async def on_ready():
        print('Bot is ready and online')

    # Display welcome message when a new member join the server
    @client.event
    async def on_member_join(member):
        channel = client.get_channel(int(os.getenv('WELCOME_CHANNEL_ID')))
        embed = discord.Embed()
        embed.set_image(url="https://i.imgur.com/Le2xPHN.png")

        await channel.send(f"Selamat datang {member.mention}, jangan lupa untuk nyalakan notifikasi pada "
                           f"<#{os.getenv('GARAPAN_CHANNEL_ID')}> untuk dapat update garapan baru dengan melakukan \n\n"
                           f"> Klik kanan di <#{os.getenv('GARAPAN_CHANNEL_ID')}> "
                           f"> Kik `Notification Setting` "
                           f"> Centang `New Posts Created` \n\n"
                           f"Contoh: ", embed=embed)

    # Display feed message on #ping-post-garapan when roles get mentioned in message at #diskusi-garapan thread channel
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        try:
            if isinstance(message.channel.parent, discord.channel.ForumChannel):
                if message.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or all(role in message.raw_role_mentions for role in [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))]):
                    channel = client.get_channel(int(os.getenv('PING_GARAPAN_CHANNEL_ID')))
                    msg_url = message.jump_url

                    embed = discord.Embed(title=f"{msg_url}",
                                          description=f"{message.content}",
                                          color=discord.Color.yellow())
                    embed.set_author(name=message.author.global_name, icon_url=message.author.avatar)
                    if message.attachments:
                        embed.set_image(url=message.attachments[0].url)
                    embed.set_footer(text=f'{message.id}')

                    await channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}> "
                                       f"ada update baru di {message.channel.name}", embed=embed)
        except:
            print('Pesan tidak terdeteksi parent forum channel')

    # Display feed message on #ping-post-garapan when message at #diskusi-garapan thread channel get edited with roles mentioned
    @client.event
    async def on_message_edit(before, after):
        if before.author == client.user:
            return

        try:
            if isinstance(after.channel.parent, discord.channel.ForumChannel):
                if (before.edited_at is None and after.edited_at is not None):
                    if (after.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or all(role in after.raw_role_mentions for role in [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))])):
                        channel = client.get_channel(int(os.getenv('PING_GARAPAN_CHANNEL_ID')))
                        msg_url = after.jump_url

                        embed = discord.Embed(title=f"{msg_url}",
                                              description=f"{after.content}",
                                              color=discord.Color.yellow())
                        embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                        if after.attachments:
                            embed.set_image(url=after.attachments[0].url)
                        embed.set_footer(text=f'{after.id}')
                        await channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}> "
                                           f"ada update baru di {after.channel.name}", embed=embed)
        except:
            print('Pesan tidak terdeteksi parent forum channel')

    client.run(os.getenv('DISCORD_API_TOKEN'))


if __name__ == '__main__':
    main()
