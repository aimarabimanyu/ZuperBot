from discord.ext import commands, tasks
import sqlite3
from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio
import asyncio


# Connect to the database
database = sqlite3.connect('data/data.db')
cursor = database.cursor()


# Create a new class called Database
class Database(commands.Cog, name='Database'):
    def __init__(self, client) -> None:
        self.client = client
        self.config = self.client.config
        self.logger = self.client.logger
        self.db_initialization_event = None
        self.db_lock = None

    """
    Initialize database lock and initialization event
    """
    async def initialize(self) -> None:
        self.db_initialization_event = asyncio.Event()
        self.db_lock = asyncio.Lock()

    """
    Initialize the existing threads and messages into the database
    """
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Wait until the client is ready
        await self.client.wait_until_ready()

        # Initialize the database lock and initialization event
        await self.initialize()

        # Create the database if it does not exist
        await self._create_database_tables()

        # Initialize the existing threads and messages into the database
        await self._initialize_database()

        # Log the successful initialization of the database
        self.logger.info("Database initialized successfully")

        # Set the database initialization event
        self.db_initialization_event.set()

        # Start the update_database task
        await self.update_database.start()

    """
    Do a database update every 15 minutes
    """
    @tasks.loop(minutes=15)
    async def update_database(self) -> None:
        # Wait until the database initialization event is set
        await self.db_initialization_event.wait()

        # Check if the bot feature for forum new thread message is enabled
        if self.config["bot_feature"]["forum_new_thread_message"]:
            # Add a helper method for forum new thread message periodic update functionality
            await self._update_forum_thread()
            await self._update_forum_new_thread_message()

        # Check if the bot feature for forum feed message is enabled
        if self.config["bot_feature"]["forum_feed_message"]:
            # Add a helper method for forum feed message periodic update functionality
            await self._update_forum_message()
            await self._update_forum_feed_message()

        # Log the database update
        self.logger.info("Database updated with newest form existing threads and messages")

    """
    Create the database tables if they do not exist
    """
    async def _create_database_tables(self) -> None:
        try:
            # Check if forum new thread message are enabled
            if self.config["bot_feature"]["forum_new_thread_message"]:
                # Create the forum_new_thread_message table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS forum_new_thread_message (
                        forum_new_thread_message_id INTEGER PRIMARY KEY,
                        channel_id INTEGER,
                        created_at TEXT,
                        edited_at TEXT
                    )
                    """
                )

                # Create the forum_thread table
                cursor.execute(
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
                        archived BOOLEAN DEFAULT 0,
                        forum_new_thread_message_id INTEGER,
                        FOREIGN KEY (forum_new_thread_message_id) REFERENCES forum_new_thread_message (forum_new_thread_message_id)
                    )
                    """
                )

            # Check if forum feed message are enabled
            if self.config["bot_feature"]["forum_feed_message"]:
                # Create the forum_feed_message table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS forum_feed_message (
                        forum_feed_message_id INTEGER PRIMARY KEY,
                        channel_id INTEGER,
                        created_at TEXT,
                        edited_at TEXT
                    )
                    """
                )

                # Create the forum_message table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS forum_message (
                        message_id INTEGER PRIMARY KEY,
                        thread_location_id INTEGER,
                        author_id INTEGER,
                        author_name TEXT,
                        created_at TEXT,
                        edited_at TEXT,
                        forum_feed_message_id INTEGER,
                        FOREIGN KEY (forum_feed_message_id) REFERENCES forum_feed_message (forum_feed_message_id)
                    )
                    """
                )

            # Check if treasury monitoring is enabled
            if self.config["bot_feature"]["treasury_monitoring"]:
                # Create treasury_monitoring table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS treasury_monitoring (
                        tx_hash TEXT PRIMARY KEY,
                        value TEXT,
                        asset TEXT,
                        from_address TEXT,
                        to_address TEXT,
                        timestamp TEXT
                    )
                    """
                )

            # Check if telegram chat mirror is enabled
            if self.config["bot_feature"]["telegram_chat_mirror"]:
                # Create the telegram mirror chat table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS telegram_messages (
                        message_id INTEGER PRIMARY KEY,
                        datetime TEXT,
                        discord_message_id TEXT
                    )
                    """
                )

            # Commit the changes to the database
            async with self.db_lock:
                database.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Database error in _create_database_tables: {e}")

        except Exception as e:
            self.logger.error(f"Exception in Database _create_database_tables | {e}")

    """
    Initialize the existing threads and messages into the database
    """
    async def _initialize_database(self) -> None:
        try:
            # Get the source and target channels for forum new thread message and forum feed message
            forumnewthreadmessage_source_forum_channel = self.client.get_channel(
                self.config['forum_new_thread_message_settings']['source_forum_channel_id'])
            forumfeedmessage_source_forum_channel = self.client.get_channel(
                self.config['forum_feed_message_settings']['source_forum_channel_id'])
            forumnewthreadmessage_target_channel = self.client.get_channel(
                self.config['forum_new_thread_message_settings']['target_channel_id'])
            forumfeedmessage_target_channel = self.client.get_channel(
                self.config['forum_feed_message_settings']['target_channel_id'])

            # Check if forum new thread message settings are enabled
            if self.config["bot_feature"]["forum_new_thread_message"]:
                # Iterate over each ACTIVE thread in the source forum channel and insert it into database
                active_threads = forumnewthreadmessage_source_forum_channel.threads
                for thread in tqdm(active_threads, desc="Processing active threads"):
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
                                thread.id, thread.name, thread.parent_id,
                                thread.parent.name if thread.parent else "Unknown", thread.owner_id,
                                thread.owner.name if thread.owner else "Unknown", thread.created_at, thread.jump_url,
                                thread.member_count, thread.message_count, thread.locked, thread.archived, None
                            )
                        )

                # Iterate over each ARCHIVED thread in the source forum channel and insert it into database
                archived_threads = forumnewthreadmessage_source_forum_channel.archived_threads(limit=None)
                async for thread in tqdm_asyncio(archived_threads, desc="Processing archived threads"):
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
                                thread.id, thread.name, thread.parent_id,
                                thread.parent.name if thread.parent else "Unknown", thread.owner_id,
                                thread.owner.name if thread.owner else "Unknown", thread.created_at, thread.jump_url,
                                thread.member_count, thread.message_count, thread.locked, thread.archived, None
                            )
                        )

                # Iterate over each message in the target channel and insert it into database for ForumNewThreadMessage
                # and update the forum_thread table with the new forum_new_thread_message_id
                async for message in tqdm_asyncio(
                        forumnewthreadmessage_target_channel.history(limit=None),
                        desc="Processing target channel messages for ForumNewThreadMessage"
                ):
                    cursor.execute(
                        "SELECT 1 FROM forum_new_thread_message WHERE forum_new_thread_message_id = ?",
                        (message.id,)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            """
                            INSERT INTO forum_new_thread_message (
                                forum_new_thread_message_id, channel_id, created_at, edited_at
                            ) VALUES (?, ?, ?, ?)
                            """,
                            (message.id, message.channel.id, message.created_at, message.edited_at)
                        )
                        cursor.execute(
                            """
                            UPDATE forum_thread SET forum_new_thread_message_id = ? WHERE thread_id = ?
                            """,
                            (message.id, message.embeds[0].footer.text.split(' ')[-1])
                        )

                # Commit the all changes to the database
                async with self.db_lock:
                    database.commit()

            # Check if forum feed message settings are enabled
            if self.config["bot_feature"]["forum_feed_message"]:
                # Iterate over each message in ACTIVE SOURCE FORUM CHANNEL THREAD
                # and IF CONTAINS TRIGGER ROLE ID then insert it into database
                for thread in tqdm(
                        forumfeedmessage_source_forum_channel.threads,
                        desc="Processing message containing trigger role in active threads"
                ):
                    async for message in thread.history(limit=None):
                        if self.config['forum_feed_message_settings']['trigger_role_id'] in message.raw_role_mentions:
                            cursor.execute(
                                "SELECT 1 FROM forum_message WHERE message_id = ?",
                                (message.id,)
                            )
                            if not cursor.fetchone():
                                cursor.execute(
                                    """
                                    INSERT INTO forum_message (
                                        message_id, thread_location_id, author_id, author_name, created_at, edited_at,
                                        forum_feed_message_id
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        message.id, thread.id, message.author.id,
                                        message.author.name if message.author else "Unknown",
                                        message.created_at, message.edited_at, None
                                    )
                                )

                # Iterate over each message in ARCHIVED SOURCE FORUM CHANNEL THREAD
                # and IF CONTAINS TRIGGER ROLE ID then insert it into database
                async for thread in tqdm_asyncio(
                        forumfeedmessage_source_forum_channel.archived_threads(limit=None),
                        desc="Processing message containing trigger role in archived threads"
                ):
                    async for message in thread.history(limit=None):
                        if self.config['forum_feed_message_settings']['trigger_role_id'] in message.raw_role_mentions:
                            cursor.execute(
                                "SELECT 1 FROM forum_message WHERE message_id = ?",
                                (message.id,)
                            )
                            if not cursor.fetchone():
                                cursor.execute(
                                    """
                                    INSERT INTO forum_message (
                                        message_id, thread_location_id, author_id, author_name, created_at, edited_at,
                                        forum_feed_message_id
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        message.id, thread.id, message.author.id,
                                        message.author.name if message.author else "Unknown",
                                        message.created_at, message.edited_at, None
                                    )
                                )

                # Iterate over each message in the target channel and insert it into database for ForumFeedMessage
                async for message in tqdm_asyncio(
                        forumfeedmessage_target_channel.history(limit=None),
                        desc="Processing target channel messages for ForumFeedMessage"
                ):
                    cursor.execute(
                        "SELECT 1 FROM forum_feed_message WHERE forum_feed_message_id = ?",
                        (message.id,)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            """
                            INSERT INTO forum_feed_message (forum_feed_message_id, channel_id, created_at, edited_at
                            ) VALUES (?, ?, ?, ?)
                            """,
                            (message.id, message.channel.id, message.created_at, message.edited_at)
                        )
                        cursor.execute(
                            """
                            UPDATE forum_message SET forum_feed_message_id = ? WHERE message_id = ?
                            """,
                            (message.id, message.embeds[0].footer.text.split(' ')[-1])
                        )

                # Commit the all changes to the database
                async with self.db_lock:
                    database.commit()

            # Log the database initialization
            self.logger.info("Database initialized with threads and messages from the source forum and target channel")

        except sqlite3.Error as e:
            self.logger.error(f"Database error in _initialize_database: {e}")

        except Exception as e:
            self.logger.error(f"Exception in Database _initialize_database | {e}")

    """
    Update the forum_thread table with the newest threads from the source forum channel
    """
    async def _update_forum_thread(self) -> None:
        try:
            # Get the source forum channel
            update_forum_thread_source_forum_channel = self.client.get_channel(
                self.config['forum_new_thread_message_settings']['source_forum_channel_id']
            )

            # Iterate over each ACTIVE thread in the source forum channel and update it into the database
            for thread in update_forum_thread_source_forum_channel.threads:
                cursor.execute(
                    "SELECT 1 FROM forum_thread WHERE thread_id = ?",
                    (thread.id,)
                )
                if cursor.fetchone():
                    cursor.execute(
                        """
                        UPDATE forum_thread SET
                            thread_name = ?, thread_location_id = ?, thread_location = ?, author_id = ?, 
                            author_name = ?, created_at = ?, jump_url = ?, member_count = ?, message_count = ?, 
                            locked = ?, archived = ?
                        WHERE thread_id = ?
                        """,
                        (
                            thread.name, thread.parent_id, thread.parent.name if thread.parent else "Unknown",
                            thread.owner_id, thread.owner.name if thread.owner else "Unknown",
                            thread.created_at, thread.jump_url, thread.member_count, thread.message_count,
                            thread.locked, thread.archived, thread.id
                        )
                    )

                    # Commit the all changes to the database
                    async with self.db_lock:
                        database.commit()

            # Iterate over thread_id in the forum_thread table and check if the thread still exists as
            # ACTIVE THREAD and ARCHIVED THREAD in the source forum channel, if not then delete it from the database
            cursor.execute(
                "SELECT thread_id FROM forum_thread"
            )
            for thread_id in cursor.fetchall():
                if (
                        thread_id[0] not in [thread.id for thread in update_forum_thread_source_forum_channel.threads]
                        and thread_id[0] not in [thread.id async for thread in update_forum_thread_source_forum_channel.archived_threads()]
                ):
                    cursor.execute(
                        "DELETE FROM forum_thread WHERE thread_id = ?",
                        (thread_id[0],)
                    )

                    # Commit the all changes to the database
                    async with self.db_lock:
                        database.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Database error in _update_forum_thread: {e}")

        except Exception as e:
            self.logger.error(f"Exception in Database _update_forum_thread: {e}")

    """
    Update the forum_new_thread_message table with the newest messages from the target channel
    """
    async def _update_forum_new_thread_message(self) -> None:
        try:
            # Get the target channel
            update_forum_new_thread_message_target_channel = self.client.get_channel(
                self.config['forum_new_thread_message_settings']['target_channel_id']
            )

            # Iterate over each message in the target channel and update it into the database
            async for message in update_forum_new_thread_message_target_channel.history(limit=None):
                cursor.execute(
                    "SELECT 1 FROM forum_new_thread_message WHERE forum_new_thread_message_id = ?",
                    (message.id,)
                )
                if cursor.fetchone():
                    cursor.execute(
                        """
                        UPDATE forum_new_thread_message SET 
                            channel_id = ?, created_at = ?, edited_at = ?
                        WHERE forum_new_thread_message_id = ?
                        """,
                        (message.channel.id, message.created_at, message.edited_at, message.id)
                    )

                    # Commit the all changes to the database
                    async with self.db_lock:
                        database.commit()

            # Iterate over forum_new_thread_message_id in the forum_new_thread_message table and check if the message
            # still exists in the target channel, if not then delete it from the database
            cursor.execute(
                "SELECT forum_new_thread_message_id FROM forum_new_thread_message"
            )
            for forum_new_thread_message_id in cursor.fetchall():
                if forum_new_thread_message_id[0] not in [
                    message.id async for message in update_forum_new_thread_message_target_channel.history()
                ]:
                    cursor.execute(
                        "DELETE FROM forum_new_thread_message WHERE forum_new_thread_message_id = ?",
                        (forum_new_thread_message_id[0],)
                    )

                    # Commit the all changes to the database
                    async with self.db_lock:
                        database.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Database error in _update_forum_new_thread_message: {e}")

        except Exception as e:
            self.logger.error(f"Exception in Database _update_forum_new_thread_message: {e}")

    """
    Update the forum_message table with the newest messages from the target channel
    """
    async def _update_forum_message(self) -> None:
        try:
            # Get the source forum channel
            update_forum_message_source_forum_channel = self.client.get_channel(
                self.config['forum_feed_message_settings']['source_forum_channel_id']
            )

            # Iterate over each ACTIVE SOURCE FORUM CHANNEL THREAD and IF CONTAINS TRIGGER ROLE ID
            # then update it into database
            for thread in update_forum_message_source_forum_channel.threads:
                async for message in thread.history(limit=None):
                    if self.config['forum_feed_message_settings']['trigger_role_id'] in message.raw_role_mentions:
                        cursor.execute(
                            "SELECT 1 FROM forum_message WHERE message_id = ?",
                            (message.id,)
                        )
                        if cursor.fetchone():
                            cursor.execute(
                                """
                                UPDATE forum_message SET
                                    thread_location_id = ?, author_id = ?, author_name = ?, created_at = ?, edited_at = ?
                                WHERE message_id = ?
                                """,
                                (
                                    thread.id, message.author.id, message.author.name if message.author else "Unknown",
                                    message.created_at, message.edited_at, message.id
                                )
                            )

                            # Commit the all changes to the database
                            async with self.db_lock:
                                database.commit()

            # Iterate over message_id in the forum_message table and check if the message still exists
            # in the target channel, if not then delete it from the database
            forum_message_id = []
            for thread in update_forum_message_source_forum_channel.threads:
                async for message in thread.history(limit=None):
                    forum_message_id.append(message.id)
            async for thread in update_forum_message_source_forum_channel.archived_threads():
                async for message in thread.history(limit=None):
                    forum_message_id.append(message.id)
            cursor.execute(
                "SELECT message_id FROM forum_message"
            )
            for message_id in cursor.fetchall():
                if message_id[0] not in forum_message_id:
                    cursor.execute(
                        "DELETE FROM forum_message WHERE message_id = ?",
                        (message_id[0],)
                    )

                    # Commit the all changes to the database
                    async with self.db_lock:
                        database.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Database error in _update_forum_message: {e}")

        except Exception as e:
            self.logger.error(f"Exception in Database _update_forum_message: {e}")

    """
    Update the forum_feed_message table with the newest messages from the target channel
    """
    async def _update_forum_feed_message(self) -> None:
        try:
            # Get the target channel
            update_forum_feed_message_target_channel = self.client.get_channel(
                self.config['forum_feed_message_settings']['target_channel_id']
            )

            # Iterate over each message in the target channel and update it into the database
            async for message in update_forum_feed_message_target_channel.history(limit=None):
                cursor.execute(
                    "SELECT 1 FROM forum_feed_message WHERE forum_feed_message_id = ?",
                    (message.id,)
                )
                if cursor.fetchone():
                    cursor.execute(
                        """
                        UPDATE forum_feed_message SET 
                            channel_id = ?, created_at = ?, edited_at = ?
                        WHERE forum_feed_message_id = ?
                        """,
                        (message.channel.id, message.created_at, message.edited_at, message.id)
                    )

                    # Commit the all changes to the database
                    async with self.db_lock:
                        database.commit()

            # Iterate over forum_feed_message_id in the forum_feed_message table and check if the message still exists
            # in the target channel, if not then delete it from the database
            cursor.execute(
                "SELECT forum_feed_message_id FROM forum_feed_message"
            )
            for forum_feed_message_id in cursor.fetchall():
                if forum_feed_message_id[0] not in [message.id async for message in update_forum_feed_message_target_channel.history()]:
                    cursor.execute(
                        "DELETE FROM forum_feed_message WHERE forum_feed_message_id = ?",
                        (forum_feed_message_id[0],)
                    )

                    # Commit the all changes to the database
                    async with self.db_lock:
                        database.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Database error in _update_forum_feed_message: {e}")

        except Exception as e:
            self.logger.error(f"Exception in Database _update_forum_feed_message: {e}")

    """
    Make sure the update_database task waits until the client is ready before starting
    """
    @update_database.before_loop
    async def before_update_database_task(self) -> None:
        await self.client.wait_until_ready()


async def setup(client) -> None:
    await client.add_cog(Database(client))
