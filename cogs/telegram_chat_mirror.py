import asyncio
import json
import os
from datetime import timedelta
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel
import discord
from discord.ext import commands
import sqlite3


database = sqlite3.connect('data/data.db', timeout=5)
cursor = database.cursor()


class TelegramToDiscord(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.logger = self.bot.logger
        self.session_dir = f"{os.path.dirname(os.path.realpath(os.path.dirname(__file__)))}"\
                           f"/data/{self.bot.config['telegram_chat_mirror_settings']['session_name']}"
        self.telegram_client = TelegramClient(
            self.session_dir,
            os.getenv('API_ID'),
            os.getenv('API_HASH')
        )
        self.telegram_group_ids = self.bot.config['telegram_chat_mirror_settings']['group_ids']
        self.telegram_group_topics = []
        self.target_channel_ids = self.bot.config['telegram_chat_mirror_settings']['target_channel_ids']

    """
    Resolve group IDs to InputPeerChannel objects
    """
    def resolve_group_ids(self):
        for i, group in enumerate(self.telegram_group_ids):
            if "_" in str(group):
                group_id, access_hash = group.split("_")

                self.telegram_group_ids[i] = InputPeerChannel(
                    channel_id=int(group_id),
                    access_hash=int(access_hash)
                )

                self.telegram_group_topics.append(access_hash)
            else:
                self.telegram_group_topics.append(None)

    """
    Static method to split the message into parts
    """
    @staticmethod
    def split_message(text, limit=1900):
        parts = []
        while len(text) > limit:
            index = text.rfind(" ", 0, limit)
            if index == -1:
                index = limit
            parts.append(text[:index])
            text = text[index:].strip()
        parts.append(text)
        return parts

    """
    Telegram client to interact with the telegram group and channel
    """
    async def start_telegram_client(self):
        self.resolve_group_ids()

        for group_id in self.telegram_group_ids:
            self.telegram_client.add_event_handler(
                lambda event, group_id=group_id: self.handle_new_message(event, group_id),
                events.NewMessage(chats=group_id)
            )
            self.telegram_client.add_event_handler(
                lambda event, group_id=group_id: self.handle_edited_message(event, group_id),
                events.MessageEdited(chats=group_id)
            )

        await self.telegram_client.start()
        print("Telegram client started")
        await self.telegram_client.run_until_disconnected()

    """
    Handle new messages from the Telegram group
    """
    async def handle_new_message(self, event, group_id):
        if isinstance(group_id, InputPeerChannel):
            if event.message.reply_to is None:
                return
            elif not (
                event.message.reply_to.reply_to_msg_id == int(self.telegram_group_topics[self.telegram_group_ids.index(group_id)])
                or event.message.reply_to.reply_to_top_id == int(self.telegram_group_topics[self.telegram_group_ids.index(group_id)])
            ):
                return

        message = self.split_message(event.message.text)
        target_channel = self.bot.get_channel(self.target_channel_ids[self.telegram_group_ids.index(group_id)])
        post_author = event.message.post_author or "Unknown Author"

        cursor.execute(
            """
            INSERT INTO telegram_messages (message_id, datetime) VALUES (?, ?)
            """,
            (event.message.id, (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'))
        )

        database.commit()

        file_temp = await self.telegram_client.download_media(event.message.media)

        if file_temp:
            discord_message_ids = await self._send_media_message(
                target_channel, message, post_author, event.message.date, file_temp, event.message.reply_to
            )
        else:
            discord_message_ids = await self._send_text_message(
                target_channel, message, post_author, event.message.date, event.message.reply_to
            )

        cursor.execute(
            """
            UPDATE telegram_messages SET discord_message_id = ? WHERE message_id = ?
            """,
            (json.dumps(discord_message_ids), event.message.id)
        )

        database.commit()

    """
    Helper method for sending telegram messages to discord
    """
    async def _send_text_message(self, channel, message, author, date, reply_to):
        discord_message_ids = []
        replied_message = await self._fetch_replied_message(channel, reply_to)

        for part in message:
            if part == message[0]:
                discord_message = await channel.send("```{} | {}``` \n {}".format(
                    author if author else "Unknown Author",
                    date.strftime('%Y-%m-%d %H:%M:%S'),
                    part
                ), reference=replied_message)
            else:
                discord_message = await channel.send(part)
            discord_message_ids.append(discord_message.id)

        return discord_message_ids

    """
    Helper method for sending telegram messages with media to discord
    """
    async def _send_media_message(self, channel, message, author, date, file_temp, reply_to):
        discord_message_ids = []
        replied_message = await self._fetch_replied_message(channel, reply_to)

        for part in message:
            if part == message[0] and len(message) > 1:
                discord_message = await channel.send("```{} | {}``` \n {}".format(
                    author if author else "Unknown Author",
                    date.strftime('%Y-%m-%d %H:%M:%S'),
                    part
                ), file=discord.File(file_temp), reference=replied_message)
            elif part == message[-1] and len(message) > 1:
                discord_message = await channel.send(part, file=discord.File(file_temp), reference=replied_message)
                os.remove(file_temp)
            elif len(message) == 1:
                discord_message = await channel.send("```{} | {}``` \n {}".format(
                    author if author else "Unknown Author",
                    date.strftime('%Y-%m-%d %H:%M:%S'),
                    part
                ), file=discord.File(file_temp), reference=replied_message)
                os.remove(file_temp)
            else:
                discord_message = await channel.send(part)
            discord_message_ids.append(discord_message.id)

        return discord_message_ids

    """
    Helper method for fetch replied message from discord
    """
    @staticmethod
    async def _fetch_replied_message(channel, reply_to):
        if reply_to:
            cursor.execute(
                """
                SELECT discord_message_id FROM telegram_messages WHERE message_id = ?
                """,
                (reply_to.reply_to_msg_id,)
            )

            replied_message_id = cursor.fetchone()
            if replied_message_id:
                return await channel.fetch_message(int(json.loads(replied_message_id[0].strip())[-1]))

        return None

    """
    Handle edited messages from the Telegram group
    """
    async def handle_edited_message(self, event, group_id):
        cursor.execute(
            """
            SELECT discord_message_id FROM telegram_messages WHERE message_id = ?
            """,
            (event.message.id,)
        )

        discord_message_ids = cursor.fetchone()

        if discord_message_ids:
            discord_message_ids = json.loads(discord_message_ids[0].strip())
            target_channel = self.bot.get_channel(self.target_channel_ids[self.telegram_group_ids.index(group_id)])
            edited_message_parts = self.split_message(event.message.text)

            for i, message_id in enumerate(discord_message_ids):
                discord_message = await target_channel.fetch_message(int(message_id))

                if i < len(edited_message_parts):
                    if i == 0:
                        await discord_message.edit(content="```{} | {}``` \n {}".format(
                            event.message.post_author if event.message.post_author else "Unknown Author",
                            (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                            edited_message_parts[i]
                        ))
                    else:
                        await discord_message.edit(content=edited_message_parts[i])
                else:
                    await discord_message.edit(content=".")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user}")

        await asyncio.create_task(self.start_telegram_client())


async def setup(bot):
    await bot.add_cog(TelegramToDiscord(bot))
