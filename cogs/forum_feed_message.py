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
        await self.client.get_cog('Database').initialization_event.wait()

        try:
            cursor.execute(
                "SELECT 1 FROM forum_message WHERE message_id = ?",
                (message.id,)
            )

            # Check if the message is from source forum channel, trigger role is mentioned, and the message is not in the database
            if (
                    message.channel.parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id']
                    and self.config['forum_feed_message_settings']['trigger_role_id'] in message.raw_role_mentions
                    and cursor.fetchone() is None
            ):
                # Get the target channel and feed message content
                target_channel = self.client.get_channel(self.config['forum_feed_message_settings']['target_channel_id'])
                feed_message_content = f"{self.client.config['forum_feed_message_settings']['feed_message']}"

                # Setups the embed message for new forum feed message
                embed = discord.Embed(title=f"{message.jump_url}", description=f"{message.content}", color=discord.Color.yellow())
                if message.attachments:
                    embed.set_image(url=message.attachments[0].url)
                embed.set_author(name=message.author.name, icon_url=message.author.avatar)
                embed.set_footer(text=str(message.id))

                # Send forum feed message to target channel
                new_feed_message = await target_channel.send(
                    feed_message_content.format(mention=self.config['forum_feed_message_settings']['mention_role_id'], message=message.channel.name),
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
                self.logger.info(f"Trigger role detected | Message ID: {message.id} | Forum feed message sent")
        except Exception as e:
            self.logger.error(f"Message ID: {message.id} | Forum feed message not sent | {e}")

    """
    Update feed message on target channel when message at source forum channel get edited with added trigger role
    """
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload) -> None:
        await self.client.get_cog('Database').initialization_event.wait()

        try:
            # Check if the message is from source forum channel and trigger role is mentioned
            if (
                    str(self.config['forum_feed_message_settings']['trigger_role_id']) in payload.data['mention_roles']
                    and self.client.get_channel(payload.channel_id).parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id']
            ):
                # Get the target channel, forum message, and feed message content
                feed_message_content = f"{self.client.config['forum_feed_message_settings']['feed_message']}"
                target_channel = self.client.get_channel(self.config['forum_feed_message_settings']['target_channel_id'])
                forum_message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)

                # Check if the forum feed message and forum message is in the database based on message_id
                result = cursor.execute(
                    "SELECT forum_feed_message_id FROM forum_message WHERE message_id = ?",
                    (payload.message_id,)
                ).fetchone()
                forum_feed_message_id = result[0] if result else None

                # Check if the edited message is more than 3 days old and the forum feed message is in the database
                if (
                        (datetime.now().timestamp() - datetime.fromisoformat(payload.data['edited_timestamp']).timestamp()) > timedelta(days=3).total_seconds()
                        and forum_feed_message_id is not None
                ):
                    # Get the old forum feed message
                    old_feed_message = await target_channel.fetch_message(forum_feed_message_id)

                    # Setups the embed message for new forum feed message
                    embed = discord.Embed(title=f"{forum_message.jump_url}", description=f"{forum_message.content}", color=discord.Color.yellow())
                    if payload.data['attachments']:
                        embed.set_image(url=forum_message.attachments[0].url)
                    embed.set_author(name=forum_message.author.name, icon_url=forum_message.author.avatar)
                    embed.set_footer(text=str(forum_message.id))

                    # Delete the old forum feed message
                    await old_feed_message.delete()

                    # Send the new forum feed message to target channel
                    new_feed_message = await target_channel.send(
                        feed_message_content.format(mention=self.config['forum_feed_message_settings']['mention_role_id'], message=target_channel.channel.name),
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
                            old_feed_message.id
                        )
                    )
                    database.commit()

                    # Log the updated forum feed message
                    self.logger.info(f"Edited message > 3 days | Message ID: {forum_message.id} | Forum feed message updated")

                # Check if the edited message is less than 3 days old and the forum feed message is in the database
                elif (
                        (datetime.now().timestamp() - datetime.fromisoformat(payload.data['edited_timestamp']).timestamp()) < timedelta(days=3).total_seconds()
                        and forum_feed_message_id is not None
                ):
                    # Get the old forum feed message
                    old_feed_message = await target_channel.fetch_message(forum_feed_message_id)

                    # Setups the embed message for new forum feed message
                    embed = discord.Embed(title=f"{forum_message.jump_url}", description=f"{forum_message.content}", color=discord.Color.yellow())
                    if payload.data['attachments']:
                        embed.set_image(url=forum_message.attachments[0].url)
                    embed.set_author(name=forum_message.author.name, icon_url=forum_message.author.avatar)
                    embed.set_footer(text=str(forum_message.id))

                    # edit the old forum feed message
                    new_feed_message = await old_feed_message.edit(embed=embed)

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
                    self.logger.info(f"Edited message < 3 days | Message ID: {forum_message.id} | Forum feed message updated")

                # Check if the forum feed message is not in the database
                elif forum_feed_message_id is None:
                    # Setups the embed message for new forum feed message
                    embed = discord.Embed(title=f"{forum_message.jump_url}", description=f"{forum_message.content}", color=discord.Color.yellow())
                    if payload.data['attachments']:
                        embed.set_image(url=forum_message.attachments[0].url)
                    embed.set_author(name=forum_message.author.name, icon_url=forum_message.author.avatar)
                    embed.set_footer(text=f'{forum_message.id}')

                    # Send the new forum feed message to target channel
                    new_feed_message = await target_channel.send(
                        feed_message_content.format(mention=self.config['forum_feed_message_settings']['mention_role_id'], message=forum_message.channel.name),
                        embed=embed
                    )

                    # Check and save if the forum message is in the database
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
                    self.logger.info(f"Edited message with added trigger role | Message ID: {payload.message_id} | Forum feed message updated")
            elif (
                    str(self.config['forum_feed_message_settings']['trigger_role_id']) not in payload.data['mention_roles']
                    and self.client.get_channel(payload.channel_id).parent.id == self.config['forum_feed_message_settings']['source_forum_channel_id']
                    and cursor.execute("SELECT 1 FROM forum_message WHERE message_id = ?", (payload.message_id,)).fetchone() is not None
            ):
                # Get the target channel
                target_channel = self.client.get_channel(self.config['forum_feed_message_settings']['target_channel_id'])

                # Check if the forum feed message and forum message is in the database based on message_id
                result = cursor.execute(
                    "SELECT forum_feed_message_id FROM forum_message WHERE message_id = ?",
                    (payload.message_id,)
                ).fetchone()
                forum_feed_message_id = result[0] if result else None

                # Check if the forum feed message is in the database
                if forum_feed_message_id is not None:
                    # Get the old forum feed message
                    old_feed_message = await target_channel.fetch_message(forum_feed_message_id)

                    # Delete the old forum feed message
                    await old_feed_message.delete()

                    # Delete the forum message and forum feed message from database
                    cursor.execute(
                        "DELETE FROM forum_message WHERE message_id = ?",
                        (payload.message_id,)
                    )
                    cursor.execute(
                        "DELETE FROM forum_feed_message WHERE forum_feed_message_id = ?",
                        (old_feed_message.id,)
                    )
                    database.commit()

                    # Log the updated forum feed message
                    self.logger.info(f"Edited message removed trigger role | Message ID: {payload.message_id} | Forum feed message deleted")
                # Check if the forum feed message is not in the database
                elif forum_feed_message_id is None:
                    # Delete the forum message from database
                    cursor.execute(
                        "DELETE FROM forum_message WHERE message_id = ?",
                        (payload.message_id,)
                    )
                    database.commit()

                    # Log the updated forum feed message
                    self.logger.info(f"Edited message removed trigger role | Message ID: {payload.message_id} | Forum message data deleted")
        except Exception as e:
            self.logger.error(f"Edited message detected | Message ID: {payload.message_id} | Forum feed message not updated | {e}")

    """
    Delete feed message on target channel when message at source forum channel get deleted
    """
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload) -> None:
        await self.client.get_cog('Database').initialization_event.wait()

        try:
            # Check if the forum feed message is in the database based on message_id
            result = cursor.execute(
                "SELECT forum_feed_message_id FROM forum_message WHERE message_id = ?",
                (payload.message_id,)
            ).fetchone()
            forum_feed_message_id = result[0] if result else None

            # Check if the forum feed message is in the database
            if forum_feed_message_id is not None:
                # Get the target channel
                target_channel = self.client.get_channel(self.config['forum_feed_message_settings']['target_channel_id'])

                # Get the old forum feed message
                old_feed_message = await target_channel.fetch_message(forum_feed_message_id)

                # Delete the old forum feed message
                await old_feed_message.delete()

                # Delete the forum message and forum feed message from database
                cursor.execute(
                    "DELETE FROM forum_message WHERE message_id = ?",
                    (payload.message_id,)
                )
                cursor.execute(
                    "DELETE FROM forum_feed_message WHERE forum_feed_message_id = ?",
                    (old_feed_message.id,)
                )
                database.commit()

                # Log the deleted forum feed message
                self.logger.info(f"Deleted message | Message ID: {payload.message_id} | Forum feed message deleted")
            if forum_feed_message_id is None:
                # Delete the forum message from database
                cursor.execute(
                    "DELETE FROM forum_message WHERE message_id = ?",
                    (payload.message_id,)
                )
                database.commit()

                # Log the deleted forum feed message
                self.logger.info(f"Deleted message | Message ID: {payload.message_id} | Forum message data deleted")
        except Exception as e:
            self.logger.error(f"Deleted message | Message ID: {payload.message_id} | Forum feed message not deleted | {e}")


async def setup(client) -> None:
    await client.add_cog(ForumFeedMessage(client))
