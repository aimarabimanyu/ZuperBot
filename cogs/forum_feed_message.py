import discord
from discord.ext import commands
from datetime import datetime, timedelta
import sqlite3


database = sqlite3.connect('data/data.db', timeout=5)
cursor = database.cursor()


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
        try:
            cursor.execute("SELECT 1 FROM forum_message WHERE message_id = ?", (message.id,))

            # Check if the message is from source forum channel, trigger role is mentioned, and the message is not in the database
            if (
                    message.channel.parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id']
                    and self.config['forum_feed_message_settings']['trigger_role_id'] in message.raw_role_mentions and
                    cursor.fetchone() is None
            ):
                # Get the target channel and feed message content
                on_message_target_forum_channel = self.client.get_channel(self.config['forum_feed_message_settings']['target_channel_id'])
                feed_message_content = f"{self.client.config['forum_feed_message_settings']['feed_message']}"

                # Setups the embed message for new forum feed message
                embed = discord.Embed(title=f"{message.jump_url}",
                                      description=f"{message.content}",
                                      color=discord.Color.yellow())
                if message.attachments:
                    embed.set_image(url=message.attachments[0].url)
                embed.set_author(name=message.author.name, icon_url=message.author.avatar)
                embed.set_footer(text=f'{message.id}')

                # Send forum feed message to target channel
                new_feed_message = await on_message_target_forum_channel.send(
                    feed_message_content.format(
                        mention=self.config['forum_feed_message_settings']['mention_role_id'],
                        message=message.channel.name
                    ),
                    embed=embed
                )

                # Save the forum message and forum feed message to database
                cursor.execute(
                    """
                    INSERT INTO forum_message (
                        message_id, thread_location_id, author_id, author_name, created_at, edited_at, 
                        forum_feed_message_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.id, message.channel.id, message.author.id, message.author.name,
                        message.created_at, message.edited_at, new_feed_message.id
                    )
                )
                cursor.execute(
                    """
                    INSERT INTO forum_feed_message (
                        forum_feed_message_id, channel_id, created_at, edited_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        new_feed_message.id, new_feed_message.channel.id, new_feed_message.created_at,
                        new_feed_message.edited_at
                    )
                )

                database.commit()

                # Log the forum feed message sent
                self.logger.info(
                    f"Trigger role on source forum channel detected | Message ID: [{message.id}], "
                    f"Location: [{message.channel}], Location ID: [{message.channel.id}], "
                    f"Author: [{message.author.name}], Author ID: [{message.author.id}] | "
                    f"Forum feed message is successfully sent"
                )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.error(
                f"Message detected | Message ID: [{message.id}], Location: [{message.channel}], "
                f"Location ID: [{message.channel.id}], Author: [{message.author.name}], "
                f"Author ID: [{message.author.id}] | Forum feed message not sent: {exception}"
            )

    """
    Update feed message on target channel when message at source forum channel get edited with added trigger role
    """
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload) -> None:
        try:
            # Check if the message is from source forum channel and trigger role is mentioned
            if (
                    str(self.config['forum_feed_message_settings']['trigger_role_id']) in payload.data['mention_roles'] and
                    self.client.get_channel(payload.channel_id).parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id']
            ):
                # Get the target channel, forum message, and feed message content
                feed_message_content = f"{self.client.config['forum_feed_message_settings']['feed_message']}"
                on_edit_target_forum_channel = self.client.get_channel(self.config['forum_feed_message_settings']['target_channel_id'])
                on_edit_forum_message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)

                # Check if the forum feed message and forum message is in the database based on message_id
                result = cursor.execute("SELECT forum_feed_message_id FROM forum_message WHERE message_id = ?", (payload.message_id,)).fetchone()
                if result is not None:
                    forum_feed_message_id = result[0]
                else:
                    forum_feed_message_id = None

                # Check if the edited message is more than 3 days old and the forum feed message is in the database
                if (
                        (datetime.now().timestamp() - datetime.fromisoformat(payload.data['edited_timestamp']).timestamp()) > timedelta(days=3).total_seconds()
                        and forum_feed_message_id is not None
                ):
                    # Get the old forum feed message
                    under_three_feed_message = await on_edit_target_forum_channel.fetch_message(forum_feed_message_id)

                    # Setups the embed message for new forum feed message
                    embed = discord.Embed(title=f"{on_edit_forum_message.jump_url}",
                                          description=f"{on_edit_forum_message.content}",
                                          color=discord.Color.yellow())
                    if payload.data['attachments']:
                        embed.set_image(url=on_edit_forum_message.attachments[0].url)
                    embed.set_author(name=on_edit_forum_message.author.name,
                                     icon_url=on_edit_forum_message.author.avatar)
                    embed.set_footer(text=f'{on_edit_forum_message.id}')

                    # Delete the old forum feed message
                    await under_three_feed_message.delete()

                    # Send the new forum feed message to target channel
                    new_feed_message = await on_edit_target_forum_channel.send(
                        feed_message_content.format(
                            mention=self.config['forum_feed_message_settings']['mention_role_id'],
                            message=on_edit_forum_message.channel.name
                        ),
                        embed=embed
                    )

                    # Update the forum message and forum feed message in the database
                    cursor.execute(
                        """
                        UPDATE forum_message SET edited_at = ?, forum_feed_message_id = ? WHERE message_id = ?
                        """,
                        (
                            payload.data['edited_timestamp'], new_feed_message.id, payload.message_id
                        )
                    )
                    cursor.execute(
                        """
                        UPDATE forum_feed_message SET forum_feed_message_id = ?, created_at = ?, edited_at = ? WHERE forum_feed_message_id = ?
                        """,
                        (
                            new_feed_message.id, new_feed_message.created_at, new_feed_message.edited_at,
                            under_three_feed_message.id
                        )
                    )

                    database.commit()

                    # Log the updated forum feed message
                    self.logger.info(
                        f"Edited message more 3 days with added trigger role detected | Message ID: [{on_edit_forum_message.id}], "
                        f"Location: [{on_edit_forum_message.channel}], Location ID: [{on_edit_forum_message.channel.id}], "
                        f"Author: [{on_edit_forum_message.author.name}], Author ID: [{on_edit_forum_message.author.id}] | "
                        f"Forum feed message is successfully updated"
                    )

                # Check if the edited message is less than 3 days old and the forum feed message is in the database
                if (
                        (datetime.now().timestamp() - datetime.fromisoformat(payload.data['edited_timestamp']).timestamp()) < timedelta(days=3).total_seconds()
                        and forum_feed_message_id is not None
                ):
                    # Get the old forum feed message
                    upper_three_feed_message = await on_edit_target_forum_channel.fetch_message(forum_feed_message_id)

                    # Setups the embed message for new forum feed message
                    embed = discord.Embed(title=f"{on_edit_forum_message.jump_url}",
                                          description=f"{on_edit_forum_message.content}",
                                          color=discord.Color.yellow())
                    if payload.data['attachments']:
                        embed.set_image(url=on_edit_forum_message.attachments[0].url)
                    embed.set_author(name=on_edit_forum_message.author.name,
                                     icon_url=on_edit_forum_message.author.avatar)
                    embed.set_footer(text=f'{on_edit_forum_message.id}')

                    # edit the old forum feed message
                    new_feed_message = await upper_three_feed_message.edit(embed=embed)

                    # Update the forum message and forum feed message in the database
                    cursor.execute(
                        """
                        UPDATE forum_message SET edited_at = ? WHERE message_id = ?
                        """,
                        (
                            payload.data['edited_timestamp'], payload.message_id
                        )
                    )
                    cursor.execute(
                        """
                        UPDATE forum_feed_message SET edited_at = ? WHERE forum_feed_message_id = ?
                        """,
                        (
                            new_feed_message.edited_at, new_feed_message.id
                        )
                    )

                    database.commit()

                    # Log the updated forum feed message
                    self.logger.info(
                        f"Edited message under 3 days with added trigger role detected | Message ID: [{on_edit_forum_message.id}], "
                        f"Location: [{on_edit_forum_message.channel}], Location ID: [{on_edit_forum_message.channel.id}], "
                        f"Author: [{on_edit_forum_message.author.name}], Author ID: [{on_edit_forum_message.author.id}] | "
                        f"Forum feed message is successfully updated"
                    )

                # Check if the forum feed message is not in the database
                if forum_feed_message_id is None:
                    # Setups the embed message for new forum feed message
                    embed = discord.Embed(title=f"{on_edit_forum_message.jump_url}",
                                          description=f"{on_edit_forum_message.content}",
                                          color=discord.Color.yellow())
                    if payload.data['attachments']:
                        embed.set_image(url=on_edit_forum_message.attachments[0].url)
                    embed.set_author(name=on_edit_forum_message.author.name,
                                     icon_url=on_edit_forum_message.author.avatar)
                    embed.set_footer(text=f'{on_edit_forum_message.id}')

                    # Send the new forum feed message to target channel
                    new_feed_message = await on_edit_target_forum_channel.send(
                        feed_message_content.format(
                            mention=self.config['forum_feed_message_settings']['mention_role_id'],
                            message=on_edit_forum_message.channel.name
                        ),
                        embed=embed
                    )

                    # Check if the forum message is in the database
                    if cursor.execute("SELECT 1 FROM forum_message WHERE message_id = ?", (payload.message_id,)).fetchone() is not None:
                        cursor.execute(
                            """
                            UPDATE forum_message SET edited_at = ?, forum_feed_message_id = ? WHERE message_id = ?
                            """,
                            (
                                payload.data['edited_timestamp'], new_feed_message.id, payload.message_id
                            )
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO forum_message (
                                message_id, thread_location_id, author_id, author_name, created_at, edited_at,
                                forum_feed_message_id
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                payload.message_id, payload.channel_id, payload.data['author']['id'],
                                payload.data['author']['username'], payload.data['timestamp'],
                                payload.data['edited_timestamp'],
                                new_feed_message.id
                            )
                        )

                    # Save the forum feed message to database
                    cursor.execute(
                        """
                        INSERT INTO forum_feed_message (
                            forum_feed_message_id, channel_id, created_at, edited_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            new_feed_message.id, new_feed_message.channel.id,
                            new_feed_message.created_at, new_feed_message.edited_at
                        )
                    )

                    database.commit()

                    # Log the updated forum feed message
                    self.logger.info(
                        f"Edited message with added trigger role detected | Message ID: [{payload.message_id}], "
                        f"Location: [{self.client.get_channel(payload.channel_id)}], Location ID: [{payload.channel_id}], "
                        f"Author: [{payload.data['author']['username']}], Author ID: [{payload.data['author']['id']}] | "
                        f"Forum feed message is successfully updated"
                    )
            elif (
                    str(self.config['forum_feed_message_settings']['trigger_role_id']) not in payload.data['mention_roles'] and
                    self.client.get_channel(payload.channel_id).parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id'] and
                    cursor.execute("SELECT 1 FROM forum_message WHERE message_id = ?", (payload.message_id,)).fetchone() is not None
            ):
                # Get the target channel
                on_edit_target_forum_channel = self.client.get_channel(self.config['forum_feed_message_settings']['target_channel_id'])

                # Check if the forum feed message and forum message is in the database based on message_id
                result = cursor.execute("SELECT forum_feed_message_id FROM forum_message WHERE message_id = ?",
                                        (payload.message_id,)).fetchone()
                if result is not None:
                    forum_feed_message_id = result[0]
                else:
                    forum_feed_message_id = None

                # Check if the forum feed message is in the database
                if forum_feed_message_id is not None:
                    # Get the old forum feed message
                    feed_message = await on_edit_target_forum_channel.fetch_message(forum_feed_message_id)

                    # Delete the old forum feed message
                    await feed_message.delete()

                    # Delete the forum message and forum feed message from database
                    cursor.execute("DELETE FROM forum_message WHERE message_id = ?", (payload.message_id,))
                    cursor.execute("DELETE FROM forum_feed_message WHERE forum_feed_message_id = ?", (feed_message.id,))

                    database.commit()

                    # Log the updated forum feed message
                    self.logger.info(
                        f"Edited message with removed trigger role detected | Message ID: [{payload.message_id}], "
                        f"Location: [{self.client.get_channel(payload.channel_id)}], Location ID: [{payload.channel_id}], "
                        f"Author: [{payload.data['author']['username']}], Author ID: [{payload.data['author']['id']}] | "
                        f"Forum feed message is successfully deleted"
                    )
                # Check if the forum feed message is not in the database
                elif forum_feed_message_id is None:
                    # Delete the forum message from database
                    cursor.execute("DELETE FROM forum_message WHERE message_id = ?", (payload.message_id,))

                    database.commit()

                    # Log the updated forum feed message
                    self.logger.info(
                        f"Edited message with removed trigger role detected | Message ID: [{payload.message_id}], "
                        f"Location: [{self.client.get_channel(payload.channel_id)}], Location ID: [{payload.channel_id}], "
                        f"Author: [{payload.data['author']['username']}], Author ID: [{payload.data['author']['id']}] | "
                        f"Forum message data is successfully deleted"
                    )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.error(
                f"Edited message detected | Message ID: [{payload.message_id}], "
                f"Location: [{self.client.get_channel(payload.channel_id)}], Location ID: [{payload.channel_id}], "
                f"Author: [{payload.data['author']['username']}], Author ID: [{payload.data['author']['id']}] | "
                f"Forum feed message not updated: {exception}"
            )

    """
    Delete feed message on target channel when message at source forum channel get deleted
    """
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload) -> None:
        try:
            # Check if the forum feed message is in the database based on message_id
            result = cursor.execute("SELECT forum_feed_message_id FROM forum_message WHERE message_id = ?", (payload.message_id,)).fetchone()
            if result is not None:
                forum_feed_message_id = result[0]
            else:
                forum_feed_message_id = None

            # Check if the forum feed message is in the database
            if forum_feed_message_id is not None:
                # Get the target channel
                on_delete_target_forum_channel = self.client.get_channel(self.config['forum_feed_message_settings']['target_channel_id'])

                # Get the old forum feed message
                feed_message = await on_delete_target_forum_channel.fetch_message(forum_feed_message_id)

                # Delete the old forum feed message
                await feed_message.delete()

                # Delete the forum message and forum feed message from database
                cursor.execute("DELETE FROM forum_message WHERE message_id = ?", (payload.message_id,))
                cursor.execute("DELETE FROM forum_feed_message WHERE forum_feed_message_id = ?", (feed_message.id,))

                database.commit()

                # Log the deleted forum feed message
                self.logger.info(
                    f"Deleted message detected | Message ID: [{payload.message_id}], "
                    f"Location: [{self.client.get_channel(payload.channel_id)}], Location ID: [{payload.channel_id}] | "
                    f"Forum feed message is successfully deleted"
                )
            if forum_feed_message_id is None:
                # Delete the forum message from database
                cursor.execute("DELETE FROM forum_message WHERE message_id = ?", (payload.message_id,))

                database.commit()

                # Log the deleted forum feed message
                self.logger.info(
                    f"Deleted message detected | Message ID: [{payload.message_id}], "
                    f"Location: [{self.client.get_channel(payload.channel_id)}], Location ID: [{payload.channel_id}] | "
                    f"Forum message data is successfully deleted"
                )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.error(
                f"Deleted message detected | Message ID: [{payload.message_id}], "
                f"Location: [{self.client.get_channel(payload.channel_id)}], Location ID: [{payload.channel_id}] | "
                f"Forum feed message not deleted: {exception}"
            )


async def setup(client) -> None:
    await client.add_cog(ForumFeedMessage(client))
