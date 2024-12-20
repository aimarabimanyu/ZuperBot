import discord
from discord.ext import commands
from datetime import datetime, timedelta


class ForumFeedMessage(commands.Cog, name='Forum Feed Message'):
    def __init__(self, client) -> None:
        self.client = client
        self.config = self.client.config
        self.logger = self.client.logger

    """
    Send feed message to target channel when trigger role get mentioned in message at source forum channel
    """
    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        if message.author == self.client.user:
            return

        try:
            if (
                    message.channel.parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id']
                    and (message.raw_role_mentions == [self.config['forum_feed_message_settings']['trigger_role_id']] or
                         {self.config['forum_feed_message_settings']['trigger_role_id'],
                          self.config['forum_feed_message_settings']['mention_role_id']}.issubset(
                             message.raw_role_mentions))
            ):
                target_forum_channel = self.client.get_channel(
                    self.config['forum_feed_message_settings']['target_channel_id']
                )
                feed_message = f"{self.client.config['forum_feed_message_settings']['feed_message']}"
                embed = discord.Embed(title=f"{message.jump_url}",
                                      description=f"{message.content}",
                                      color=discord.Color.yellow())
                if message.attachments:
                    embed.set_image(url=message.attachments[0].url)
                embed.set_author(name=message.author.global_name, icon_url=message.author.avatar)
                embed.set_footer(text=f'{message.id}')

                await target_forum_channel.send(
                    feed_message.format(mention=self.config['forum_feed_message_settings']['mention_role_id'],
                                        message=message.channel.name),
                    embed=embed
                )

                self.logger.info(
                    f"Trigger role on source forum channel detected | Message ID: [{message.id}], "
                    f"Location: [{message.channel}], Location ID: [{message.channel.id}], "
                    f"Author: [{message.author.global_name}], Author ID: [{message.author.id}] | "
                    f"Forum feed message is successfully sent"
                )

        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.warning(
                f"Message detected | Message ID: [{message.id}], Location: [{message.channel}], "
                f"Location ID: [{message.channel.id}], Author: [{message.author.global_name}], "
                f"Author ID: [{message.author.id}] | Forum feed message not sent: {exception}"
            )

    """
    Update feed message on target channel when message at source forum channel get edited with added trigger role
    """
    @commands.Cog.listener()
    async def on_message_edit(self, before, after) -> None:
        if before.author == self.client.user:
            return

        try:
            target_forum_channel = self.client.get_channel(
                self.config['forum_feed_message_settings']['target_channel_id']
            )
            feed_message = f"{self.client.config['forum_feed_message_settings']['feed_message']}"
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for message in target_forum_channel.history(limit=300):
                if message.embeds:
                    feed_message_footer_id_list.append(int(message.embeds[0].footer.text))
                    feed_message_id_list.append(message.id)

            # Send new feed message if feed message is sent more than 3 days ago
            if (
                    after.channel.parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id'] and
                    before.pinned == after.pinned and before.id in feed_message_footer_id_list and
                    (datetime.now().timestamp() - before.created_at.timestamp()) > timedelta(days=3).total_seconds()
            ):
                if (
                        after.raw_role_mentions == [self.config['forum_feed_message_settings']['trigger_role_id']] or
                        {self.config['forum_feed_message_settings']['trigger_role_id'],
                         self.config['forum_feed_message_settings']['mention_role_id']}.issubset(
                            after.raw_role_mentions
                        )
                ):
                    embed = discord.Embed(title=f"{after.jump_url}",
                                          description=f"{after.content}",
                                          color=discord.Color.yellow())
                    if after.attachments:
                        embed.set_image(url=after.attachments[0].url)
                    embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                    embed.set_footer(text=f'{after.id}')

                    feed_message = await target_forum_channel.fetch_message(
                        feed_message_id_list[feed_message_footer_id_list.index(before.id)]
                    )

                    await feed_message.delete()
                    await target_forum_channel.send(
                        feed_message.format(
                            mention=self.config['forum_feed_message_settings']['mention_role_id'],
                            message=after.channel.name
                        ),
                        embed=embed
                    )

                    self.logger.info(
                        f"Edited message more 3 days with added trigger role detected | Message ID: [{before.id}], "
                        f"Location: [{before.channel}], Location ID: [{before.channel.id}], "
                        f"Author: [{before.author.global_name}], Author ID: [{before.author.id}] | "
                        f"Forum feed message is successfully updated"
                    )

            # Edit embed feed message if feed message is sent less than 3 days ago
            elif (
                    after.channel.parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id'] and
                    before.pinned == after.pinned and before.id in feed_message_footer_id_list and
                    (datetime.now().timestamp() - before.created_at.timestamp()) < timedelta(days=3).total_seconds()
            ):
                if (
                        after.raw_role_mentions == [self.config['forum_feed_message_settings']['trigger_role_id']] or
                        {self.config['forum_feed_message_settings']['trigger_role_id'],
                         self.config['forum_feed_message_settings']['mention_role_id']}.issubset(
                            after.raw_role_mentions
                        )
                ):
                    embed = discord.Embed(title=f"{after.jump_url}",
                                          description=f"{after.content}",
                                          color=discord.Color.yellow())
                    if after.attachments:
                        embed.set_image(url=after.attachments[0].url)
                    embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                    embed.set_footer(text=f'{after.id}')

                    feed_message = await target_forum_channel.fetch_message(
                        feed_message_id_list[feed_message_footer_id_list.index(before.id)]
                    )

                    await feed_message.edit(embed=embed)

                    self.logger.info(
                        f"Edited message under 3 days with added trigger role detected | Message ID: [{before.id}], "
                        f"Location: [{before.channel}], Location ID: [{before.channel.id}], "
                        f"Author: [{before.author.global_name}], Author ID: [{before.author.id}] | "
                        f"Forum feed message is successfully updated"
                    )

            # Send new message if the message is edited and feed message is not sent yet
            elif (
                    after.channel.parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id'] and
                    before.pinned == after.pinned and before.id not in feed_message_footer_id_list
            ):
                if (
                        after.raw_role_mentions == [self.config['forum_feed_message_settings']['trigger_role_id']] or
                        {self.config['forum_feed_message_settings']['trigger_role_id'],
                         self.config['forum_feed_message_settings']['mention_role_id']}.issubset(
                            after.raw_role_mentions
                        )
                ):
                    embed = discord.Embed(title=f"{after.jump_url}",
                                          description=f"{after.content}",
                                          color=discord.Color.yellow())
                    if after.attachments:
                        embed.set_image(url=after.attachments[0].url)
                    embed.set_author(name=after.author.global_name, icon_url=after.author.avatar)
                    embed.set_footer(text=f'{after.id}')

                    await target_forum_channel.send(
                        feed_message.format(
                            mention=self.config['forum_feed_message_settings']['mention_role_id'],
                            message=after.channel.name
                        ),
                        embed=embed
                    )

                    self.logger.info(
                        f"Edited message with added trigger role detected | Message ID: [{before.id}], "
                        f"Location: [{before.channel}], Location ID: [{before.channel.id}], "
                        f"Author: [{before.author.global_name}], Author ID: [{before.author.id}] | "
                        f"Forum feed message is successfully updated"
                    )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.warning(
                f"Edited message detected | Message ID: [{before.id}], "
                f"Location: [{before.channel}], Location ID: [{before.channel.id}], "
                f"Author: [{before.author.global_name}], Author ID: [{before.author.id}] | "
                f"Forum feed message not updated: {exception}"
            )

    """
    Delete feed message on target channel when message at source forum channel get deleted
    """
    @commands.Cog.listener()
    async def on_message_delete(self, message) -> None:
        if message.author == self.client.user:
            return

        try:
            target_forum_channel = self.client.get_channel(
                self.config['forum_feed_message_settings']['target_channel_id']
            )
            feed_message_footer_id_list = []
            feed_message_id_list = []

            async for feed_message in target_forum_channel.history(limit=300):
                if feed_message.embeds:
                    feed_message_footer_id_list.append(int(feed_message.embeds[0].footer.text))
                    feed_message_id_list.append(feed_message.id)

            if (
                    message.channel.parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id']
                    and message.id in feed_message_footer_id_list
            ):
                feed_message = await target_forum_channel.fetch_message(
                    feed_message_id_list[feed_message_footer_id_list.index(message.id)]
                )
                await feed_message.delete()

                self.logger.info(
                    f"Deleted message in source forum channel detected | Message ID: [{message.id}], "
                    f"Location: [{message.channel}], Location ID: [{message.channel.id}], "
                    f"Author: [{message.author.global_name}], Author ID: [{message.author.id}] | "
                    f"Feed message is successfully deleted"
                )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.warning(
                f"Deleted message detected | Message ID: [{message.id}], "
                f"Location: [{message.channel}], Location ID: [{message.id}], "
                f"Author: [{message.global_name}], Author ID: [{message.author.id}] | "
                f"Forum feed message not deleted: {exception}"
            )


async def setup(client) -> None:
    await client.add_cog(ForumFeedMessage(client))
