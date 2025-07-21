import asyncio
import json
import os
from datetime import timedelta
from telethon import TelegramClient, events
import discord
from discord.ext import commands
import sqlite3


database = sqlite3.connect('data/data.db', timeout=5)
cursor = database.cursor()


class TelegramToDiscord(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.telegram_client_session_directory = (
            f"{os.path.dirname(os.path.realpath(os.path.dirname(__file__)))}"
            f"/data/{self.bot.config['telegram_chat_mirror_settings']['session_name']}"
        )
        self.telegram_client = TelegramClient(
            self.telegram_client_session_directory,
            os.getenv('API_ID'),
            os.getenv('API_HASH')
        )
        self.telegram_group_ids = self.bot.config['telegram_chat_mirror_settings']['group_ids']
        self.target_channel_ids = self.bot.config['telegram_chat_mirror_settings']['target_channel_ids']

    """
    Static method to split the message into parts
    """
    @staticmethod
    def split_message(text):
        limit = 1900
        part = []
        while len(text) > limit:
            index = text.rfind(" ", 0, limit)
            if index == -1:
                index = limit
            part.append(text[:index])
            text = text[index:].strip()
        part.append(text)
        return part

    """
    Telegram client to interact with the telegram group and channel
    """
    async def start_telegram_client(self):
        # Register the handler for new messages with multiple group IDs
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
        message = event.message.text
        message = self.split_message(message)
        target_channel_id = self.target_channel_ids[self.telegram_group_ids.index(group_id)]
        target_channel = self.bot.get_channel(target_channel_id)
        post_author = event.message.post_author

        cursor.execute(
            """
            INSERT INTO telegram_messages (message_id, datetime) VALUES (?, ?)
            """,
            (event.message.id, (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'))
        )

        file_temp = await self.telegram_client.download_media(event.message.media)

        # Check if the file is None, which means no media was sent
        if file_temp is None:
            discord_message_id = []

            # Check if the message is not replying to another message
            if event.message.reply_to is None:
                for part in message:
                    if part == message[0]:
                        discord_message = await target_channel.send("```{} | {}``` \n {}".format(
                            post_author if post_author else "Unknown Author",
                            (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                            part
                        ))
                    else:
                        discord_message = await target_channel.send(part)
                    discord_message_id.append(discord_message.id)

            # Check if the message is replying to another message
            elif event.message.reply_to is not None:
                cursor.execute(
                    """
                    SELECT discord_message_id FROM telegram_messages WHERE message_id = ?
                    """,
                    (event.message.reply_to.reply_to_msg_id,)
                )

                replied_message_id = cursor.fetchone()
                replied_message = await target_channel.fetch_message(int(json.loads(replied_message_id[0].strip())[-1])) if replied_message_id else None

                for part in message:
                    if part == message[0]:
                        discord_message = await target_channel.send("```{} | {}``` \n {}".format(
                            post_author if post_author else "Unknown Author",
                            (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                            part
                        ), reference=replied_message)
                    else:
                        discord_message = await target_channel.send(part)
                    discord_message_id.append(discord_message.id)

            cursor.execute(
                """
                UPDATE telegram_messages SET discord_message_id = ? WHERE message_id = ?
                """,
                (json.dumps(discord_message_id), event.message.id)
            )

        # Check if the file is not None, which means media was sent
        elif file_temp:
            discord_message_id = []

            # If the message is not replying to another message
            if event.message.reply_to is None:
                if message:
                    for part in message:
                        if part == message[0] and len(message) > 1:
                            discord_message = await target_channel.send("```{} | {}``` \n {}".format(
                                post_author if post_author else "Unknown Author",
                                (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                                part
                            ))
                        elif part == message[-1] and len(message) > 1:
                            discord_message = await target_channel.send(part, file=discord.File(file_temp))
                            os.remove(file_temp)
                        elif len(message) == 1:
                            discord_message = await target_channel.send("```{} | {}``` \n {}".format(
                                post_author if post_author else "Unknown Author",
                                (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                                part
                            ), file=discord.File(file_temp))
                            os.remove(file_temp)
                        else:
                            discord_message = await target_channel.send(part)
                        discord_message_id.append(discord_message.id)
                else:
                    discord_message = await target_channel.send(file=discord.File(file_temp))
                    discord_message_id.append(discord_message.id)
                    os.remove(file_temp)

            # If the message is replying to another message
            elif event.message.reply_to is not None:
                cursor.execute(
                    """
                    SELECT discord_message_id FROM telegram_messages WHERE message_id = ?
                    """,
                    (event.message.reply_to.reply_to_msg_id,)
                )

                replied_message_id = cursor.fetchone()
                replied_message = await target_channel.fetch_message(int(json.loads(replied_message_id[0].strip())[-1])) if replied_message_id else None

                if message:
                    for part in message:
                        if part == message[0] and len(message) > 1:
                            discord_message = await target_channel.send("```{} | {}``` \n {}".format(
                                post_author if post_author else "Unknown Author",
                                (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                                part
                            ), reference=replied_message)
                        elif part == message[-1] and len(message) > 1:
                            discord_message = await target_channel.send(part, file=discord.File(file_temp), reference=replied_message)
                            os.remove(file_temp)
                        elif len(message) == 1:
                            discord_message = await target_channel.send("```{} | {}``` \n {}".format(
                                post_author if post_author else "Unknown Author",
                                (event.message.date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:S'),
                                part
                            ), file=discord.File(file_temp), reference=replied_message)
                            os.remove(file_temp)
                        else:
                            discord_message = await target_channel.send(part)
                        discord_message_id.append(discord_message.id)
                else:
                    discord_message = await target_channel.send(file=discord.File(file_temp))
                    discord_message_id.append(discord_message.id)
                    os.remove(file_temp)

            cursor.execute(
                """
                UPDATE telegram_messages SET discord_message_id = ? WHERE message_id = ?
                """,
                (json.dumps(discord_message_id), event.message.id)
            )

        database.commit()

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

        discord_message_id = cursor.fetchone()
        target_channel_id = self.target_channel_ids[self.telegram_group_ids.index(group_id)]
        target_channel = self.bot.get_channel(target_channel_id)

        if discord_message_id:
            discord_message_id = json.loads(discord_message_id[0].strip())

            edited_message_parts = self.split_message(event.message.text)

            for i, message_id in enumerate(discord_message_id):
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
                    if discord_message.attachments is None:
                        await discord_message.edit(content=".")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user}")

        await asyncio.create_task(self.start_telegram_client())


async def setup(bot):
    await bot.add_cog(TelegramToDiscord(bot))
