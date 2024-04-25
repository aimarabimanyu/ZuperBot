import discord
from discord.ext import commands
from datetime import datetime, timedelta
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
        welcome_channel = client.get_channel(int(os.getenv('WELCOME_CHANNEL_ID')))
        embed = discord.Embed()
        embed.set_image(url="https://i.imgur.com/Le2xPHN.png")

        await welcome_channel.send(f"Selamat datang {member.mention}, jangan lupa untuk nyalakan notifikasi pada "
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
                    ping_garapan_channel = client.get_channel(int(os.getenv('PING_GARAPAN_CHANNEL_ID')))
                    msg_url = message.jump_url

                    embed = discord.Embed(title=f"{msg_url}",
                                          description=f"{message.content}",
                                          color=discord.Color.yellow())
                    embed.set_author(name=message.author.global_name, icon_url=message.author.avatar)
                    if message.attachments:
                        embed.set_image(url=message.attachments[0].url)
                    embed.set_footer(text=f'{message.id}')

                    await ping_garapan_channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}> "
                                                    f"ada update baru di {message.channel.name}", embed=embed)
        except:
            print('Pesan tidak terdeteksi parent forum channel (New Message)')

    # Display feed message on #ping-post-garapan when message at #diskusi-garapan thread channel get edited with roles mentioned
    @client.event
    async def on_message_edit(before, after):
        if before.author == client.user:
            return

        ping_garapan_channel = client.get_channel(int(os.getenv('PING_GARAPAN_CHANNEL_ID')))
        msg_url = after.jump_url

        try:
            if isinstance(after.channel.parent, discord.channel.ForumChannel) and before.pinned == after.pinned:
                feed_message_footer_id_list = []
                feed_message_id_list = []

                # Take the message id from the footer of the message
                async for message in ping_garapan_channel.history(limit=200):
                    if message.embeds:
                        feed_message_footer_id_list.append(int(message.embeds[0].footer.text))
                        feed_message_id_list.append(message.id)

                # Send new message if the message is edited and feed message is sent more than 3 days ago
                if before.id in feed_message_footer_id_list and (datetime.now().timestamp() - before.created_at.timestamp()) > timedelta(days=3).total_seconds():
                    if after.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or all(role in after.raw_role_mentions for role in [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))]):
                        embed = discord.Embed(title=f"{msg_url}",
                                              description=f"{after.content}",
                                              color=discord.Color.yellow())

                        embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                        if after.attachments:
                            embed.set_image(url=after.attachments[0].url)
                        embed.set_footer(text=f'{after.id}')

                        feed_message = await ping_garapan_channel.fetch_message(feed_message_id_list[feed_message_footer_id_list.index(before.id)])
                        await feed_message.delete()
                        await ping_garapan_channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}> "
                                                        f"ada update baru di {after.channel.name}", embed=embed)

                # Edit embed feed message if the message is edited and feed message is sent less than 3 days ago
                elif before.id in feed_message_footer_id_list and (datetime.now().timestamp() - before.created_at.timestamp()) < timedelta(days=3).total_seconds():
                    if after.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or all(role in after.raw_role_mentions for role in [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))]):
                        embed = discord.Embed(title=f"{msg_url}",
                                              description=f"{after.content}",
                                              color=discord.Color.yellow())

                        embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                        if after.attachments:
                            embed.set_image(url=after.attachments[0].url)
                        embed.set_footer(text=f'{after.id}')

                        feed_message = await ping_garapan_channel.fetch_message(feed_message_id_list[feed_message_footer_id_list.index(before.id)])
                        await feed_message.edit(embed=embed)

                # Send new message if the message is edited and feed message is not sent yet
                elif before.id not in feed_message_footer_id_list:
                    if after.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or all(role in after.raw_role_mentions for role in [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))]):
                        embed = discord.Embed(title=f"{msg_url}",
                                              description=f"{after.content}",
                                              color=discord.Color.yellow())
                        embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                        if after.attachments:
                            embed.set_image(url=after.attachments[0].url)
                        embed.set_footer(text=f'{after.id}')

                        await ping_garapan_channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}> "
                                                        f"ada update baru di {after.channel.name}", embed=embed)

        except:
            print('Pesan tidak terdeteksi parent forum channel (Edited)')

    # Delete feed message on #ping-post-garapan when message at #diskusi-garapan thread channel get deleted
    @client.event
    async def on_message_delete(message):
        if message.author == client.user:
            return

        ping_garapan_channel = client.get_channel(int(os.getenv('PING_GARAPAN_CHANNEL_ID')))

        try:
            if isinstance(message.channel.parent, discord.channel.ForumChannel):
                feed_message_footer_id_list = []
                feed_message_id_list = []

                async for feed_message in ping_garapan_channel.history(limit=200):
                    if feed_message.embeds:
                        feed_message_footer_id_list.append(int(feed_message.embeds[0].footer.text))
                        feed_message_id_list.append(feed_message.id)

                if message.id in feed_message_footer_id_list:
                    feed_message = await ping_garapan_channel.fetch_message(feed_message_id_list[feed_message_footer_id_list.index(message.id)])
                    await feed_message.delete()

        except:
            print('Pesan tidak terdeteksi parent forum channel (Delete)')

    # Send feed message on #warmindo-24-jam when there is new thread created on #diskusi-garapan
    @client.event
    async def on_thread_create(thread):
        if thread.owner == client.user:
            return

        if thread.parent_id == int(os.getenv('GARAPAN_CHANNEL_ID')):
            warmindo_channel = client.get_channel(int(os.getenv('WARMINDO_CHANNEL_ID')))
            thread_url = thread.jump_url
            starter_message = await thread.fetch_message(thread.id)

            embed = discord.Embed(title=f"{thread_url}",
                                  description=f"{starter_message.content}",
                                  color=discord.Color.green())
            embed.set_author(name=thread.owner.name, icon_url=thread.owner.avatar)
            if thread.starter_message.attachments:
                embed.set_image(url=starter_message.attachments[0].url)
            embed.set_footer(text=f'{thread.id}')

            await warmindo_channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}>\n"
                                        f"garapan baru {thread.name} udah ada di channel diskusi garapan, buruan gih tinggalin jejak", embed=embed)

    # Delete feed message on #warmindo-24-jam when thread on #diskusi-garapan get deleted
    @client.event
    async def on_thread_delete(thread):
        if thread.owner == client.user:
            return

        if thread.parent_id == int(os.getenv('GARAPAN_CHANNEL_ID')):
            warmindo_channel = client.get_channel(int(os.getenv('WARMINDO_CHANNEL_ID')))
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for feed_message in warmindo_channel.history(limit=200):
                if feed_message.embeds and feed_message.author.name == 'ZuperBot Testing':
                    if feed_message.embeds[0].footer.text is not None:
                        feed_message_footer_id_list.append(int(feed_message.embeds[0].footer.text))
                    feed_message_id_list.append(feed_message.id)

            if thread.id in feed_message_footer_id_list:
                feed_message = await warmindo_channel.fetch_message(feed_message_id_list[feed_message_footer_id_list.index(thread.id)])
                await feed_message.delete()


    client.run(os.getenv('DISCORD_API_TOKEN'))


if __name__ == '__main__':
    main()
