import discord
from discord.ext import commands
from appkey import *

def main():
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
        channel = client.get_channel(WELCOME_CHANNEL_ID)
        embed = discord.Embed()
        embed.set_image(url="https://i.imgur.com/Le2xPHN.png")

        await channel.send(f"Selamat datang {member.mention}, jangan lupa untuk nyalakan notifikasi pada <#{str(FORUM_CHANNEL_ID)}> untuk dapat update garapan baru dengan melakukan \n\n"
                           f"> Klik kanan di <#{str(FORUM_CHANNEL_ID)}> "
                           f"> Kik `Notification Setting` "
                           f"> Centang `New Posts Created` \n\n"
                           f"Contoh: ", embed=embed)

    # Display message when roles get mentioned
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        try:
            if isinstance(message.channel.parent, discord.channel.ForumChannel):
                mentioned_roles = message.role_mentions

                if mentioned_roles :
                    channel = client.get_channel(PING_FORUM_CHANNEL_ID)
                    msg_url = message.jump_url

                    await channel.send(f"<@&{NAKAMA_ROLE_ID}> ada update baru di {msg_url}")
        except:
            print('Pesan tidak terdeteksi parent channel')

    client.run(BOT_TOKEN)

if __name__ == '__main__':
    main()
