from discord.ext import commands, tasks
import sqlite3


class Database(commands.Cog, name='Database'):
    def __init__(self, client) -> None:
        self.client = client
        self.config = self.client.config
        self.logger = self.client.logger

        try:
            self.database = sqlite3.connect('data/forum_thread.db')
            self.cursor = self.database.cursor()

            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS forum_thread (
                    thread_id INTEGER PRIMARY KEY,
                    thread_name TEXT,
                    thread_location_id INTEGER,
                    thread_location TEXT,
                    author_id INTEGER,
                    author_name TEXT,
                    created_at TEXT,
                    jump_url TEXT,
                    member_count INTEGER,
                    message_count INTEGER,
                    locked BOOLEAN DEFAULT 0,
                    archived BOOLEAN DEFAULT 0
                )
                """
            )

            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS forum_new_thread_message (
                    message_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    created_at TEXT,
                    edited_at TEXT
                )
                """
            )

            self.database.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
        except Exception as e:
            self.logger.error(f"Exception in __init__: {e}")

    """
    Initialize the existing threads and messages in to the database
    """
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        try:
            source_forum_channel = self.client.get_channel(
                self.config['forum_new_thread_message']['source_forum_channel_id']
            )
            target_channel = self.client.get_channel(self.config['forum_new_thread_message']['target_channel_id'])

            # Iterate over each ACTIVE thread in the source forum channel and insert it into the database
            for thread in source_forum_channel.threads:
                self.cursor.execute("SELECT 1 FROM forum_thread WHERE thread_id = ?", (thread.id,))
                if not self.cursor.fetchone():
                    self.cursor.execute(
                        """
                        INSERT INTO forum_thread (
                            thread_id, thread_name, thread_location_id, thread_location, author_id, author_name,
                            created_at, jump_url, member_count, message_count, locked, archived
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            thread.id, thread.name, thread.parent_id, thread.parent.name, thread.owner_id,
                            thread.owner.name, thread.created_at, thread.jump_url, thread.member_count,
                            thread.message_count, thread.locked, thread.archived
                        )
                    )

            # Iterate over each ARCHIVED thread in the source forum channel and insert it into the database
            async for thread in source_forum_channel.archived_threads(limit=None):
                self.cursor.execute("SELECT 1 FROM forum_thread WHERE thread_id = ?", (thread.id,))
                if not self.cursor.fetchone():
                    self.cursor.execute(
                        """
                        INSERT INTO forum_thread (
                            thread_id, thread_name, thread_location_id, thread_location, author_id, author_name,
                            created_at, jump_url, member_count, message_count, locked, archived
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            thread.id, thread.name, thread.parent_id, thread.parent.name, thread.owner_id,
                            thread.owner.name, thread.created_at, thread.jump_url, thread.member_count,
                            thread.message_count, thread.locked, thread.archived
                        )
                    )

            # Iterate over each message in the target channel and insert it into the database
            async for message in target_channel.history(limit=None):
                self.cursor.execute("SELECT 1 FROM forum_new_thread_message WHERE message_id = ?", (message.id,))
                if not self.cursor.fetchone():
                    self.cursor.execute(
                        """
                        INSERT INTO forum_new_thread_message (message_id, channel_id, created_at, edited_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (message.id, message.channel.id, message.created_at, message.edited_at)
                    )

            self.database.commit()
            self.logger.info("Database initialized with threads and messages from the source forum and target channel")
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
        except Exception as e:
            self.logger.error(f"Exception in Database method on_ready: {e}")

        await self.update_database.start()

    @tasks.loop(minutes=10)
    async def update_database(self) -> None:
        await self._update_forum_thread()
        await self._update_forum_new_thread_message()

    async def _update_forum_thread(self) -> None:
        try:
            source_forum_channel = self.client.get_channel(
                self.config['forum_new_thread_message']['source_forum_channel_id']
            )

            # Iterate over each message in the target channel and update it into the database
            for thread in source_forum_channel.threads:
                self.cursor.execute("SELECT 1 FROM forum_thread WHERE thread_id = ?", (thread.id,))
                if self.cursor.fetchone():
                    self.cursor.execute(
                        """
                        UPDATE forum_thread SET
                            thread_name = ?, thread_location_id = ?, thread_location = ?, author_id = ?, 
                            author_name = ?, created_at = ?, jump_url = ?, member_count = ?, message_count = ?, 
                            locked = ?, archived = ?
                        WHERE thread_id = ?
                        """,
                        (
                            thread.name, thread.parent_id, thread.parent.name, thread.owner_id, thread.owner.name,
                            thread.created_at, thread.jump_url, thread.member_count, thread.message_count,
                            thread.locked, thread.archived, thread.id
                        )
                    )

            self.database.commit()
            self.logger.info("Database updated with newest form existing threads from the source forum channel")
        except sqlite3.Error as e:
            self.logger.error(f"Database error in _update_forum_thread: {e}")
        except Exception as e:
            self.logger.error(f"Exception in Database _update_forum_thread: {e}")

    async def _update_forum_new_thread_message(self) -> None:
        try:
            target_channel = self.client.get_channel(self.config['forum_new_thread_message']['target_channel_id'])

            # Iterate over each ACTIVE thread in the source forum channel and update it into the database
            async for message in target_channel.history(limit=None):
                self.cursor.execute("SELECT 1 FROM forum_new_thread_message WHERE message_id = ?", (message.id,))
                if self.cursor.fetchone():
                    self.cursor.execute(
                        """
                        UPDATE forum_new_thread_message SET 
                            channel_id = ?, created_at = ?, edited_at = ?
                        WHERE message_id = ?
                        """,
                        (message.channel.id, message.created_at, message.edited_at, message.id)
                    )

            self.database.commit()
            self.logger.info("Database updated with newest form existing messages from the target channel")
        except sqlite3.Error as e:
            self.logger.error(f"Database error in _update_forum_new_thread_message: {e}")
        except Exception as e:
            self.logger.error(f"Exception in Database _update_forum_new_thread_message: {e}")

    @update_database.before_loop
    async def before_update_database_task(self) -> None:
        await self.client.wait_until_ready()


async def setup(client) -> None:
    await client.add_cog(Database(client))
