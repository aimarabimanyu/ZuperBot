import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class FeedMessage(commands.Cog, name='Feed Message'):
    def __init__(self, client):
        self.client = client

    """
    Display feed message on #ping-post-garapan when roles get mentioned in message 
    at #diskusi-garapan thread channel
    """
    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        if message.author == self.client.user:
            return

        if isinstance(message.channel.parent, discord.channel.ForumChannel):
            if (
                    message.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or
                    all(role in message.raw_role_mentions for role in
                        [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))])
            ):
                ping_garapan_channel = self.client.get_channel(int(os.getenv('PING_GARAPAN_CHANNEL_ID')))

                embed = discord.Embed(title=f"{message.jump_url}",
                                      description=f"{message.content}",
                                      color=discord.Color.yellow())
                if message.attachments:
                    embed.set_image(url=message.attachments[0].url)
                embed.set_author(name=message.author.global_name, icon_url=message.author.avatar)
                embed.set_footer(text=f'{message.id}')

                await ping_garapan_channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}> "
                                                f"ada update baru di {message.channel.name}", embed=embed)

    """
    Display feed message on #ping-post-garapan when message 
    at #diskusi-garapan thread channel get edited with roles mentioned
    """
    @commands.Cog.listener()
    async def on_message_edit(self, before, after) -> None:
        if before.author == self.client.user:
            return

        if isinstance(after.channel.parent, discord.channel.ForumChannel) and before.pinned == after.pinned:
            ping_garapan_channel = self.client.get_channel(int(os.getenv('PING_GARAPAN_CHANNEL_ID')))
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for message in ping_garapan_channel.history(limit=200):
                if message.embeds:
                    feed_message_footer_id_list.append(int(message.embeds[0].footer.text))
                    feed_message_id_list.append(message.id)

            # Send new message if the message is edited and feed message is sent more than 3 days ago
            if (
                    before.id in feed_message_footer_id_list and
                    (datetime.now().timestamp() - before.created_at.timestamp()) > timedelta(days=3).total_seconds()
            ):
                if (
                        after.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or
                        all(role in after.raw_role_mentions for role in
                            [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))])
                ):
                    embed = discord.Embed(title=f"{after.jump_url}",
                                          description=f"{after.content}",
                                          color=discord.Color.yellow())
                    if after.attachments:
                        embed.set_image(url=after.attachments[0].url)
                    embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                    embed.set_footer(text=f'{after.id}')

                    feed_message = await ping_garapan_channel.fetch_message(
                        feed_message_id_list[feed_message_footer_id_list.index(before.id)]
                    )

                    await feed_message.delete()
                    await ping_garapan_channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}> "
                                                    f"ada update baru di {after.channel.name}", embed=embed)

            # Edit embed feed message if the message is edited and feed message is sent less than 3 days ago
            elif (
                    before.id in feed_message_footer_id_list and
                    (datetime.now().timestamp() - before.created_at.timestamp()) < timedelta(days=3).total_seconds()
            ):
                if (
                        after.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or
                        all(role in after.raw_role_mentions for role in
                            [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))])
                ):
                    embed = discord.Embed(title=f"{after.jump_url}",
                                          description=f"{after.content}",
                                          color=discord.Color.yellow())
                    if after.attachments:
                        embed.set_image(url=after.attachments[0].url)
                    embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                    embed.set_footer(text=f'{after.id}')

                    feed_message = await ping_garapan_channel.fetch_message(
                        feed_message_id_list[feed_message_footer_id_list.index(before.id)]
                    )
                    await feed_message.edit(embed=embed)

            # Send new message if the message is edited and feed message is not sent yet
            elif before.id not in feed_message_footer_id_list:
                if (
                        after.raw_role_mentions == [int(os.getenv('UPDATE_GARAPAN_ROLE_ID'))] or
                        all(role in after.raw_role_mentions for role in
                            [int(os.getenv('UPDATE_GARAPAN_ROLE_ID')), int(os.getenv('NAKAMA_ROLE_ID'))])
                ):
                    embed = discord.Embed(title=f"{after.jump_url}",
                                          description=f"{after.content}",
                                          color=discord.Color.yellow())
                    if after.attachments:
                        embed.set_image(url=after.attachments[0].url)
                    embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                    embed.set_footer(text=f'{after.id}')

                    await ping_garapan_channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}> "
                                                    f"ada update baru di {after.channel.name}", embed=embed)

    """
    Delete feed message on #ping-post-garapan when message at #diskusi-garapan thread channel get deleted
    """
    @commands.Cog.listener()
    async def on_message_delete(self, message) -> None:
        if message.author == self.client.user:
            return

        if isinstance(message.channel.parent, discord.channel.ForumChannel):
            ping_garapan_channel = self.client.get_channel(int(os.getenv('PING_GARAPAN_CHANNEL_ID')))
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for feed_message in ping_garapan_channel.history(limit=200):
                if feed_message.embeds:
                    feed_message_footer_id_list.append(int(feed_message.embeds[0].footer.text))
                    feed_message_id_list.append(feed_message.id)

            if message.id in feed_message_footer_id_list:
                feed_message = await ping_garapan_channel.fetch_message(
                    feed_message_id_list[feed_message_footer_id_list.index(message.id)]
                )
                await feed_message.delete()

    """
    Send feed message on #warmindo-24-jam when there is new thread created on #diskusi-garapan
    """
    @commands.Cog.listener()
    async def on_thread_create(self, thread) -> None:
        if thread.owner == self.client.user:
            return

        if thread.parent_id == int(os.getenv('GARAPAN_CHANNEL_ID')):
            warmindo_channel = self.client.get_channel(int(os.getenv('WARMINDO_CHANNEL_ID')))
            starter_message = await thread.fetch_message(thread.id)

            embed = discord.Embed(title=f"{thread.jump_url}",
                                  description=f"{starter_message.content}",
                                  color=discord.Color.green())
            if thread.starter_message.attachments:
                embed.set_image(url=starter_message.attachments[0].url)
            embed.set_author(name=thread.owner.name, icon_url=thread.owner.avatar)
            embed.set_footer(text=f'{thread.id}')

            await warmindo_channel.send(f"<@&{int(os.getenv('NAKAMA_ROLE_ID'))}>\n"
                                        f"garapan baru {thread.name} udah ada di channel diskusi garapan, "
                                        f"buruan gih tinggalin jejak", embed=embed)

    """
    Delete feed message on #warmindo-24-jam when thread on #diskusi-garapan get deleted
    """
    @commands.Cog.listener()
    async def on_thread_delete(self, thread) -> None:
        if thread.owner == self.client.user:
            return

        if thread.parent_id == int(os.getenv('GARAPAN_CHANNEL_ID')):
            warmindo_channel = self.client.get_channel(int(os.getenv('WARMINDO_CHANNEL_ID')))
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for feed_message in warmindo_channel.history(limit=100):
                if feed_message.embeds and feed_message.author.name == os.getenv('ZUPERBOT_USERNAME'):
                    if feed_message.embeds[0].footer.text is not None:
                        feed_message_footer_id_list.append(int(feed_message.embeds[0].footer.text))
                    feed_message_id_list.append(feed_message.id)

            if thread.id in feed_message_footer_id_list:
                feed_message = await warmindo_channel.fetch_message(
                    feed_message_id_list[feed_message_footer_id_list.index(thread.id)]
                )
                await feed_message.delete()


async def setup(client) -> None:
    await client.add_cog(FeedMessage(client))
