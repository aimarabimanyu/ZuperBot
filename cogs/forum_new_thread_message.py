import discord
from discord.ext import commands
import asyncio
import sqlite3


database = sqlite3.connect('data/forum_thread.db')
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
        try:
            if thread.parent_id == self.config['forum_new_thread_message']['source_forum_channel_id']:
                target_channel = self.client.get_channel(self.config['forum_new_thread_message']['target_channel_id'])
                feed_message_new = f"{self.client.config['forum_new_thread_message']['new_thread_message']}"
                starter_message = None
                while starter_message is None:
                    try:
                        starter_message = await thread.fetch_message(thread.id)
                    except discord.NotFound:
                        await asyncio.sleep(1)

                embed = discord.Embed(title=f"{thread.jump_url}",
                                      description=f"{starter_message.content}",
                                      color=discord.Color.green())
                if starter_message.attachments:
                    embed.set_image(url=starter_message.attachments[0].url)
                embed.set_author(name=thread.owner.name, icon_url=thread.owner.avatar)
                embed.set_footer(text=f'{thread.id}')

                new_thread_message = await target_channel.send(
                    feed_message_new.format(
                        mention=self.client.config['forum_new_thread_message']['mention_role_id'],
                        thread=thread.name
                    ),
                    embed=embed
                )

                cursor.execute("SELECT 1 FROM forum_thread WHERE thread_id = ?", (thread.id,))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO forum_thread (
                            thread_id, thread_name, thread_location_id, thread_location, author_id, author_name,
                            created_at, jump_url, member_count, message_count, locked, archived, message_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            thread.id, thread.name, thread.parent_id, thread.parent.name, thread.owner_id,
                            thread.owner.name, thread.created_at, thread.jump_url, thread.member_count,
                            thread.message_count, thread.locked, thread.archived, new_thread_message.id
                        )
                    )

                cursor.execute("SELECT 1 FROM forum_new_thread_message WHERE message_id = ?", (new_thread_message.id,))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO forum_new_thread_message (
                            message_id, channel_id, created_at, edited_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            new_thread_message.id, new_thread_message.channel.id, new_thread_message.created_at,
                            new_thread_message.edited_at
                        )
                    )
                database.commit()

                self.logger.info(
                    f"New thread at source forum channel detected | Thread ID: [{thread.id}], "
                    f"Thread Name: [{thread.name}], Thread Location: [{thread.parent}], "
                    f"Author: [{thread.owner.name}], Author ID: [{thread.owner.id}] | "
                    f"New thread message is successfully sent"
                )
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.warning(
                f"New thread detected | Thread ID: [{thread.id}], Thread Name: [{thread.name}], "
                f"Thread Location: [{thread.parent}], Author: [{thread.owner.name}], "
                f"Author ID: [{thread.owner.id}] | Failed when send new thread message: {exception}"
            )

    """
    Update new thread message on target channel when thread at source forum channel get edited
    """
    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload) -> None:
        thread_id = payload.thread_id
        cursor.execute("SELECT message_id FROM forum_thread WHERE thread_id = ?", (thread_id,))
        message_id = cursor.fetchone()
        if message_id:
            try:
                target_channel = self.client.get_channel(self.config['forum_new_thread_message']['target_channel_id'])
                thread_post = self.client.get_channel(thread_id)
                new_thread_message = await target_channel.fetch_message(message_id[0])
                starter_message = await thread_post.fetch_message(thread_id)
                feed_message_content = f"{self.client.config['forum_new_thread_message']['new_thread_message']}"

                embed = discord.Embed(title=f"{payload.thread.jump_url}",
                                      description=f"{starter_message.content}",
                                      color=discord.Color.green())
                if starter_message.attachments:
                    embed.set_image(url=starter_message.attachments[0].url)
                embed.set_author(name=payload.thread.owner.name, icon_url=payload.thread.owner.avatar)
                embed.set_footer(text=f'{thread_id}')

                await new_thread_message.edit(
                    content=feed_message_content.format(
                        mention=self.client.config['forum_new_thread_message']['mention_role_id'],
                        thread=payload.thread.name
                    ),
                    embed=embed
                )

                cursor.execute(
                    """
                    UPDATE forum_thread SET thread_name = ? WHERE thread_id = ?
                    """,
                    (
                        payload.thread.name, thread_id
                    )
                )
                cursor.execute(
                    """
                    UPDATE forum_new_thread_message SET edited_at = ? WHERE message_id = ?
                    """,
                    (
                        new_thread_message.edited_at, message_id[0]
                    )
                )
                database.commit()

                self.logger.info(
                    f"Edited thread at source forum channel detected | Thread ID: [{thread_id}], "
                    f"Thread Name: [{payload.thread.name}], Thread Location: [{payload.thread.parent}], "
                    f"Author: [{payload.thread.owner.name}], Author ID: [{payload.thread.owner.id}] | "
                    f"New thread message is successfully updated"
                )
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                self.logger.warning(
                    f"Edited thread detected | Thread ID: [{thread_id}], Thread Name: [{payload.thread.name}], "
                    f"Thread Location: [{payload.thread.parent}], Author: [{payload.thread.owner.name}], "
                    f"Author ID: [{payload.thread.owner.id}] | Failed when update new thread message: {exception}"
                )

    """
    Update new thread message on target channel when thread starter message at source forum channel get edited
    """
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload) -> None:
        cursor.execute("SELECT message_id FROM forum_thread WHERE thread_id = ?", (payload.message_id,))
        new_thread_message_id = cursor.fetchone()
        if new_thread_message_id:
            try:
                target_channel = self.client.get_channel(self.config['forum_new_thread_message']['target_channel_id'])
                thread_post = self.client.get_channel(payload.message_id)
                new_thread_message = await target_channel.fetch_message(new_thread_message_id[0])
                starter_message = await thread_post.fetch_message(payload.message_id)
                feed_message_content = f"{self.client.config['forum_new_thread_message']['new_thread_message']}"

                embed = discord.Embed(title=f"{thread_post.jump_url}",
                                      description=f"{starter_message.content}",
                                      color=discord.Color.green())
                if starter_message.attachments:
                    embed.set_image(url=starter_message.attachments[0].url)
                embed.set_author(name=thread_post.owner.name, icon_url=thread_post.owner.avatar)
                embed.set_footer(text=f'{payload.message_id}')

                await new_thread_message.edit(
                    content=feed_message_content.format(
                        mention=self.client.config['forum_new_thread_message']['mention_role_id'],
                        thread=thread_post.name
                    ),
                    embed=embed
                )

                cursor.execute(
                    """
                    UPDATE forum_new_thread_message SET edited_at = ? WHERE message_id = ?
                    """,
                    (
                        new_thread_message.edited_at, new_thread_message_id[0]
                    )
                )
                database.commit()

                self.logger.info(
                    f"Edited thread starter message at source forum channel detected | "
                    f"Thread ID: [{payload.message_id}], "
                    f"Thread Name: [{thread_post.name}], Thread Location: [{thread_post.parent}], "
                    f"Author: [{thread_post.owner.name}], Author ID: [{thread_post.owner.id}] | "
                    f"New thread message is successfully updated"
                )
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                self.logger.warning(
                    f"Edited thread detected | Thread ID: [{payload.message_id}], "
                    f"Thread Name: [{thread_post.name}], "
                    f"Thread Location: [{thread_post.parent}], Author: [{thread_post.owner.name}], "
                    f"Author ID: [{thread_post.owner.id}] | Failed when update new thread message: {exception}"
                )

    """
    Delete new thread message on target channel when thread at source forum channel get deleted
    """
    @commands.Cog.listener()
    async def on_raw_thread_delete(self, payload) -> None:
        thread_id = payload.thread_id
        cursor.execute("SELECT 1 FROM forum_thread WHERE thread_id = ?", (thread_id,))
        if cursor.fetchone():
            try:
                target_channel = self.client.get_channel(self.config['forum_new_thread_message']['target_channel_id'])
                cursor.execute("SELECT message_id FROM forum_thread WHERE thread_id = ?", (thread_id,))
                message_id = cursor.fetchone()
                new_thread_message = await target_channel.fetch_message(message_id[0])

                await new_thread_message.delete()

                cursor.execute("DELETE FROM forum_thread WHERE thread_id = ?", (thread_id,))
                database.commit()
                cursor.execute("DELETE FROM forum_new_thread_message WHERE message_id = ?", (message_id[0],))
                database.commit()

                self.logger.info(
                    f"Deleted thread at source forum channel detected | Thread ID: [{thread_id}] | "
                    f"New thread message is successfully deleted"
                )

            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                self.logger.warning(
                    f"Deleted thread detected | Thread ID: [{thread_id}] | "
                    f"Failed when delete new thread message: {exception}"
                )


async def setup(client) -> None:
    await client.add_cog(ForumNewThreadMessage(client))
