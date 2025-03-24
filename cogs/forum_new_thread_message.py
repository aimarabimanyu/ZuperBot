import discord
from discord.ext import commands
import asyncio
import sqlite3


database = sqlite3.connect('data/data.db')
cursor = database.cursor()


class ForumNewThreadMessage(commands.Cog, name='Forum New Thread Message'):
    def __init__(self, client) -> None:
        self.client = client
        self.config = self.client.config
        self.logger = self.client.logger

    """
    Send new thread message on target channel when there is new thread created at source forum channel
    """
    @commands.Cog.listener()
    async def on_thread_create(self, thread) -> None:
        cursor.execute(
            "SELECT forum_new_thread_message_id FROM forum_thread WHERE thread_id = ?",
            (thread.id,)
        )
        forum_new_thread_message_id = cursor.fetchone()
        try:
            # Check if the new thread is created at the source forum channel
            if thread.parent_id == self.config['forum_new_thread_message_settings']['source_forum_channel_id'] and forum_new_thread_message_id is None:
                # Get the target channel and new thread message format
                target_channel = self.client.get_channel(self.config['forum_new_thread_message_settings']['target_channel_id'])
                feed_message_new = f"{self.client.config['forum_new_thread_message_settings']['new_thread_message']}"
                starter_message = None

                # Wait until the thread starter message is fetched
                while starter_message is None:
                    try:
                        starter_message = await thread.fetch_message(thread.id)
                    except discord.NotFound:
                        await asyncio.sleep(1)

                # Setups the embed message for new thread message
                embed = discord.Embed(title=f"{thread.jump_url}", description=f"{starter_message.content}", color=discord.Color.green())
                if starter_message.attachments:
                    embed.set_image(url=starter_message.attachments[0].url)
                embed.set_author(name=thread.owner.name, icon_url=thread.owner.avatar)
                embed.set_footer(text=str(thread.id))

                # Send the new thread message to the target channel
                new_thread_message = await target_channel.send(
                    feed_message_new.format(mention=self.client.config['forum_new_thread_message_settings']['mention_role_id'], thread=thread.name),
                    embed=embed
                )

                # Insert the new thread and new thread message into the database
                cursor.execute(
                    "SELECT 1 FROM forum_thread WHERE thread_id = ?",
                    (thread.id,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO forum_thread (
                            thread_id, thread_name, thread_location_id, thread_location, author_id, author_name,
                            created_at, jump_url, member_count, message_count, locked, archived, 
                            forum_new_thread_message_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            thread.id, thread.name, thread.parent_id, thread.parent.name, thread.owner_id,
                            thread.owner.name, thread.created_at, thread.jump_url, thread.member_count,
                            thread.message_count, thread.locked, thread.archived, new_thread_message.id
                        )
                    )
                cursor.execute(
                    "SELECT 1 FROM forum_new_thread_message WHERE forum_new_thread_message_id = ?",
                    (new_thread_message.id,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO forum_new_thread_message (
                            forum_new_thread_message_id, channel_id, created_at, edited_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            new_thread_message.id, new_thread_message.channel.id, new_thread_message.created_at,
                            new_thread_message.edited_at
                        )
                    )
                database.commit()

                # Log the new thread message
                self.logger.info(f"New thread detected | Thread ID: {thread.id} | New thread message sent")
        except Exception as e:
            self.logger.error(f"Failed to send new thread message | {e}")

    """
    Update new thread message on target channel when thread at source forum channel get edited
    """
    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload) -> None:
        cursor.execute(
            "SELECT forum_new_thread_message_id FROM forum_thread WHERE thread_id = ?",
            (payload.thread_id,)
        )
        forum_new_thread_message_id = cursor.fetchone()

        # Check if the thread id is existed in forum_thread table
        if forum_new_thread_message_id:
            try:
                # Get the target channel, updated thread, new thread message, and new thread message content
                target_channel = self.client.get_channel(self.config['forum_new_thread_message_settings']['target_channel_id'])
                thread_post_updated = self.client.get_channel(payload.thread_id)
                new_thread_message = await target_channel.fetch_message(forum_new_thread_message_id[0])
                new_thread_message_content = f"{self.client.config['forum_new_thread_message_settings']['new_thread_message']}"
                starter_message = await thread_post_updated.fetch_message(payload.thread_id)

                # Setups the embed message for edit new thread message with the newest thread content
                embed = discord.Embed(title=f"{payload.thread.jump_url}", description=f"{starter_message.content}", color=discord.Color.green())
                if starter_message.attachments:
                    embed.set_image(url=starter_message.attachments[0].url)
                embed.set_author(name=payload.thread.owner.name, icon_url=payload.thread.owner.avatar)
                embed.set_footer(text=str(payload.thread_id))

                # Edit the new thread message on the target channel
                await new_thread_message.edit(
                    content=new_thread_message_content.format(mention=self.client.config['forum_new_thread_message_settings']['mention_role_id'], thread=payload.thread.name),
                    embed=embed
                )

                # Update the updated thread content and new thread message into the database
                cursor.execute(
                    """
                    UPDATE forum_thread SET thread_name = ? WHERE thread_id = ?
                    """,
                    (
                        payload.thread.name, payload.thread_id
                    )
                )
                cursor.execute(
                    """
                    UPDATE forum_new_thread_message SET edited_at = ? WHERE forum_new_thread_message_id = ?
                    """,
                    (
                        new_thread_message.edited_at, forum_new_thread_message_id[0]
                    )
                )
                database.commit()

                # Log the edited thread message
                self.logger.info(f"Thread updated | Thread ID: {payload.thread_id} | New thread message updated")
            except Exception as e:
                self.logger.error(f"Failed to update new thread message | {e}")

    """
    Update new thread message on target channel when thread starter message at source forum channel get edited
    """
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload) -> None:
        cursor.execute(
            "SELECT forum_new_thread_message_id FROM forum_thread WHERE thread_id = ?",
            (payload.message_id,)
        )
        new_thread_message_id = cursor.fetchone()

        # Check if the new thread message id is existed in forum_thread table
        if new_thread_message_id:
            try:
                # Get the target channel, thread starter channel, new thread message, and new thread message content
                target_channel = self.client.get_channel(self.config['forum_new_thread_message_settings']['target_channel_id'])
                thread_post_starter = self.client.get_channel(payload.message_id)
                new_thread_message = await target_channel.fetch_message(new_thread_message_id[0])
                new_thread_message_content = f"{self.client.config['forum_new_thread_message_settings']['new_thread_message']}"
                starter_message = await thread_post_starter.fetch_message(payload.message_id)

                # Setups the embed message for edit new thread message with the newest thread starter message content
                embed = discord.Embed(title=f"{thread_post_starter.jump_url}", description=f"{starter_message.content}", color=discord.Color.green())
                if starter_message.attachments:
                    embed.set_image(url=starter_message.attachments[0].url)
                embed.set_author(name=thread_post_starter.owner.name, icon_url=thread_post_starter.owner.avatar)
                embed.set_footer(text=f'{payload.message_id}')

                # Edit the new thread message on the target channel
                await new_thread_message.edit(
                    content=new_thread_message_content.format(mention=self.client.config['forum_new_thread_message_settings']['mention_role_id'], thread=thread_post_starter.name),
                    embed=embed
                )

                # Update the updated thread starter message content into the database
                cursor.execute(
                    """
                    UPDATE forum_new_thread_message SET edited_at = ? WHERE forum_new_thread_message_id = ?
                    """,
                    (
                        new_thread_message.edited_at, new_thread_message_id[0]
                    )
                )
                database.commit()

                # Log the edited thread starter message
                self.logger.info(f"Thread starter message updated | Thread ID: {payload.message_id} | New thread message updated")
            except Exception as e:
                self.logger.error(f"Failed to update new thread message | {e}")

    """
    Delete new thread message on target channel when thread at source forum channel get deleted
    """
    @commands.Cog.listener()
    async def on_raw_thread_delete(self, payload) -> None:
        cursor.execute(
            "SELECT 1 FROM forum_thread WHERE thread_id = ?",
            (payload.thread_id,)
        )

        # Check if the thread id is existed in forum_thread table
        if cursor.fetchone():
            try:
                # Get the target channel, new thread message id, and new thread message
                target_channel = self.client.get_channel(self.config['forum_new_thread_message_settings']['target_channel_id'])
                cursor.execute(
                    "SELECT forum_new_thread_message_id FROM forum_thread WHERE thread_id = ?",
                    (payload.thread_id,)
                )
                forum_new_thread_message_id = cursor.fetchone()
                new_thread_message = await target_channel.fetch_message(forum_new_thread_message_id[0])

                # Delete the new thread message on the target channel
                await new_thread_message.delete()

                # Delete the thread and new thread message from the database
                cursor.execute(
                    "DELETE FROM forum_thread WHERE thread_id = ?",
                    (payload.thread_id,)
                )
                cursor.execute(
                    "DELETE FROM forum_new_thread_message WHERE forum_new_thread_message_id = ?",
                    (forum_new_thread_message_id[0],)
                )
                database.commit()

                # Log the deleted thread message
                self.logger.info(f"Thread deleted | Thread ID: {payload.thread_id} | New thread message deleted")
            except Exception as e:
                self.logger.error(f"Failed to delete new thread message | {e}")


async def setup(client) -> None:
    await client.add_cog(ForumNewThreadMessage(client))
