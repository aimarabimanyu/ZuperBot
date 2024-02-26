import discord
from discord.ext import commands

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
        channel = client.get_channel(1211739560485064734)
        embed = discord.Embed()
        embed.set_image(url="https://i.imgur.com/Le2xPHN.png")

        await channel.send(f"Selamat datang {member.mention}, jangan lupa untuk nyalakan notifikasi pada <#{str(1211739632773894194)}> untuk dapat update garapan baru dengan melakukan \n\n"
                           f"> Klik kanan di <#{str(1211739632773894194)}> "
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
                if message.raw_role_mentions == [1211741113728110651]:
                    channel = client.get_channel(1211739766220132375)
                    print()
                    msg_url = message.jump_url

                    await channel.send(f"<@&{1211741113728110651}> ada update baru di {msg_url}")
        except:
            print('Pesan tidak terdeteksi parent channel')

    client.run('MTIwNDkyMDIwOTE2NTY1MjAwMA.GAqr2b.bsNJlUgxCdwG2P7i8vDO-Yx5kjYzhKKa3t2FGY')

if __name__ == '__main__':
    main()
