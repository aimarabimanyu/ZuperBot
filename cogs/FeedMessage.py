import discord
from discord.ext import commands
from datetime import datetime, timedelta


class FeedMessage(commands.Cog, name='Feed Message'):
    def __init__(self, client) -> None:
        self.client = client
        self.feed_message_update_channel_id = client.config['FeedMessage']['feed_message_update_channel_id']
        self.feed_message_new_channel_id = client.config['FeedMessage']['feed_message_new_channel_id']
        self.source_channel_id = client.config['FeedMessage']['source_channel_id']
        self.mention_all_role_id = client.config['FeedMessage']['mention_all_role_id']
        self.mention_feed_role_id = client.config['FeedMessage']['mention_feed_role_id']
        self.logger = client.logger

    """
    Send feed message on #ping-post-garapan when roles get mentioned in message 
    at #diskusi-garapan thread channel
    """
    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        if message.author == self.client.user:
            return

        try:
            if (
                    isinstance(message.channel.parent, discord.channel.ForumChannel) and
                    (message.raw_role_mentions == [self.mention_feed_role_id] or
                     all(role in message.raw_role_mentions for role in [self.mention_feed_role_id,
                                                                        self.mention_all_role_id]))
            ):
                ping_garapan_channel = self.client.get_channel(self.feed_message_update_channel_id)
                feed_message_update = f"{self.client.config['FeedMessage']['feed_message_update']}"
                embed = discord.Embed(title=f"{message.jump_url}",
                                      description=f"{message.content}",
                                      color=discord.Color.yellow())
                if message.attachments:
                    embed.set_image(url=message.attachments[0].url)
                embed.set_author(name=message.author.global_name, icon_url=message.author.avatar)
                embed.set_footer(text=f'{message.id}')

                await ping_garapan_channel.send(
                    feed_message_update.format(mention=self.mention_all_role_id, message=message.channel.name),
                    embed=embed
                )

                self.logger.info(
                    f"New message|[{message.id}] on [{message.channel}]|[{message.channel.id}] "
                    f"by [{message.author.global_name}]|[{message.author.id}]: {message.content}, "
                    f"Feed message is successfully sent"
                )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.info(
                f"New message|[{message.id}] on [{message.channel}]|[{message.channel.id}] "
                f"by [{message.author.global_name}]|[{message.author.id}]: {message.content}, "
                f"{exception}"
            )

    """
    Send feed message on #ping-post-garapan when message 
    at #diskusi-garapan thread channel get edited with roles mentioned
    """
    @commands.Cog.listener()
    async def on_message_edit(self, before, after) -> None:
        if before.author == self.client.user:
            return

        try:
            ping_garapan_channel = self.client.get_channel(self.feed_message_update_channel_id)
            feed_message_update = f"{self.client.config['FeedMessage']['feed_message_update']}"
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for message in ping_garapan_channel.history(limit=200):
                if message.embeds:
                    feed_message_footer_id_list.append(int(message.embeds[0].footer.text))
                    feed_message_id_list.append(message.id)

            # Send new message if the message is edited and feed message is sent more than 3 days ago
            if (
                    isinstance(after.channel.parent, discord.channel.ForumChannel) and
                    before.pinned == after.pinned and
                    before.id in feed_message_footer_id_list and
                    (datetime.now().timestamp() - before.created_at.timestamp()) > timedelta(days=3).total_seconds()
            ):
                if (
                        after.raw_role_mentions == [self.mention_feed_role_id] or
                        all(role in after.raw_role_mentions for role in [self.mention_feed_role_id,
                                                                         self.mention_all_role_id])
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
                    await ping_garapan_channel.send(
                        feed_message_update.format(mention=self.mention_all_role_id, message=after.channel.name),
                        embed=embed
                    )

                    self.logger.info(
                        f"Edited message|[{before.id}] on [{before.channel}]|[{before.channel.id}] "
                        f"by [{before.author.global_name}]|[{before.author.id}]: {before.content} to {after.content}, "
                        f"Feed message is successfully updated"
                    )

            # Edit embed feed message if the message is edited and feed message is sent less than 3 days ago
            elif (
                    isinstance(after.channel.parent, discord.channel.ForumChannel) and
                    before.pinned == after.pinned and
                    before.id in feed_message_footer_id_list and
                    (datetime.now().timestamp() - before.created_at.timestamp()) < timedelta(days=3).total_seconds()
            ):
                if (
                        after.raw_role_mentions == [self.mention_feed_role_id] or
                        all(role in after.raw_role_mentions for role in [self.mention_feed_role_id,
                                                                         self.mention_all_role_id])
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

                    self.logger.info(
                        f"Edited message|[{before.id}] on [{before.channel}]|[{before.channel.id}] "
                        f"by [{before.author.global_name}]|[{before.author.id}]: {before.content} to {after.content}, "
                        f"Feed message is successfully updated"
                    )

            # Send new message if the message is edited and feed message is not sent yet
            elif (
                    isinstance(after.channel.parent, discord.channel.ForumChannel) and
                    before.pinned == after.pinned and
                    before.id not in feed_message_footer_id_list
            ):
                if (
                        after.raw_role_mentions == [self.mention_feed_role_id] or
                        all(role in after.raw_role_mentions for role in [self.mention_feed_role_id,
                                                                         self.mention_all_role_id])
                ):
                    embed = discord.Embed(title=f"{after.jump_url}",
                                          description=f"{after.content}",
                                          color=discord.Color.yellow())
                    if after.attachments:
                        embed.set_image(url=after.attachments[0].url)
                    embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                    embed.set_footer(text=f'{after.id}')

                    await ping_garapan_channel.send(
                        feed_message_update.format(mention=self.mention_all_role_id, message=after.channel.name),
                        embed=embed
                    )

                    self.logger.info(
                        f"Edited message|[{before.id}] on [{before.channel}]|[{before.channel.id}] "
                        f"by [{before.author.global_name}]|[{before.author.id}]: {before.content} to {after.content}, "
                        f"Feed message is successfully sent"
                    )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.info(
                f"Edited message|[{before.id}] on [{before.channel}]|[{before.channel.id}] "
                f"by [{before.author.global_name}]|[{before.author.id}]: {before.content} to {after.content}, "
                f"{exception}"
            )

    """
    Delete feed message on #ping-post-garapan when message at #diskusi-garapan thread channel get deleted
    """
    @commands.Cog.listener()
    async def on_message_delete(self, message) -> None:
        if message.author == self.client.user:
            return

        try:
            ping_garapan_channel = self.client.get_channel(self.feed_message_update_channel_id)
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for feed_message in ping_garapan_channel.history(limit=200):
                if feed_message.embeds:
                    feed_message_footer_id_list.append(int(feed_message.embeds[0].footer.text))
                    feed_message_id_list.append(feed_message.id)

            if (
                    isinstance(message.channel.parent, discord.channel.ForumChannel) and
                    message.id in feed_message_footer_id_list
            ):
                feed_message = await ping_garapan_channel.fetch_message(
                    feed_message_id_list[feed_message_footer_id_list.index(message.id)]
                )
                await feed_message.delete()

                self.logger.info(
                    f"Deleted message|[{message.id}] on [{message.channel}]|[{message.channel.id}] "
                    f"by [{message.author.global_name}]|[{message.author.id}]: {message.content}, "
                    f"Feed message is successfully deleted"
                )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            f"Deleted message|[{message.id}] on [{message.channel}]|[{message.channel.id}] "
            f"by [{message.author.global_name}]|[{message.author.id}]: {message.content}, {exception}"

    """
    Send feed message on #warmindo-24-jam when there is new thread created on #diskusi-garapan
    """
    @commands.Cog.listener()
    async def on_thread_create(self, thread) -> None:
        if thread.owner == self.client.user:
            return

        try:
            if thread.parent_id == self.source_channel_id:
                warmindo_channel = self.client.get_channel(self.feed_message_new_channel_id)
                starter_message = await thread.fetch_message(thread.id)
                feed_message_new = f"{self.client.config['FeedMessage']['feed_message_new']}"

                embed = discord.Embed(title=f"{thread.jump_url}",
                                      description=f"{starter_message.content}",
                                      color=discord.Color.green())
                if starter_message.attachments:
                    embed.set_image(url=starter_message.attachments[0].url)
                embed.set_author(name=thread.owner.name, icon_url=thread.owner.avatar)
                embed.set_footer(text=f'{thread.id}')

                await warmindo_channel.send(
                    feed_message_new.format(mention=self.mention_all_role_id, thread=thread.name),
                    embed=embed
                )

                self.logger.info(
                    f"Thread feed message [{thread.name}]|[{thread.id}] on [{thread.parent}]|[{thread.parent.id}] "
                    f"is successfully sent"
                )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.error(f"Failed when send feed message when thread [{thread.name}] created, {exception}")

    """
    Delete feed message on #warmindo-24-jam when thread on #diskusi-garapan get deleted
    """
    @commands.Cog.listener()
    async def on_thread_delete(self, thread) -> None:
        if thread.owner == self.client.user:
            return

        try:
            warmindo_channel = self.client.get_channel(self.feed_message_new_channel_id)
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for feed_message in warmindo_channel.history(limit=200):
                if feed_message.embeds and feed_message.author.name == self.client.config['bot_name']:
                    if feed_message.embeds[0].footer.text is not None:
                        feed_message_footer_id_list.append(int(feed_message.embeds[0].footer.text))
                    feed_message_id_list.append(feed_message.id)

            if thread.parent_id == self.source_channel_id and thread.id in feed_message_footer_id_list:
                feed_message = await warmindo_channel.fetch_message(
                    feed_message_id_list[feed_message_footer_id_list.index(thread.id)]
                )
                await feed_message.delete()

                self.logger.info(
                    f"Thread feed message [{thread.name}]|[{thread.id}] on [{thread.parent}]|[{thread.parent.id}] "
                    f"is successfully deleted"
                )

        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.error(f"Failed when try to delete thread [{thread.name}] feed message, {exception}")


async def setup(client) -> None:
    await client.add_cog(FeedMessage(client))
