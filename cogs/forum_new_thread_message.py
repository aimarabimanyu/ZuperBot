import discord
from discord.ext import commands
import time

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
        time.sleep(3)
        try:
            if thread.parent_id == self.config['forum_new_thread_message']['source_forum_channel_id']:
                target_channel = self.client.get_channel(self.config['forum_new_thread_message']['target_channel_id'])
                feed_message_new = f"{self.client.config['forum_new_thread_message']['new_thread_message']}"
                starter_message = await thread.fetch_message(thread.id)

                embed = discord.Embed(title=f"{thread.jump_url}",
                                      description=f"{starter_message.content}",
                                      color=discord.Color.green())
                if starter_message.attachments:
                    embed.set_image(url=starter_message.attachments[0].url)
                embed.set_author(name=thread.owner.name, icon_url=thread.owner.avatar)
                embed.set_footer(text=f'{thread.id}')

                await target_channel.send(
                    feed_message_new.format(
                        mention=self.client.config['forum_new_thread_message']['mention_role_id'],
                        thread=thread.name
                    ),
                    embed=embed
                )

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
    Delete new thread message on target channel when thread at source forum channel get deleted
    """
    @commands.Cog.listener()
    async def on_thread_delete(self, thread) -> None:
        time.sleep(3)
        try:
            target_channel = self.client.get_channel(self.config['forum_new_thread_message']['target_channel_id'])
            new_thread_message_footer_id_list = []
            new_thread_message_id_list = []

            async for new_thread_message in target_channel.history(limit=300):
                if new_thread_message.embeds and new_thread_message.author.name == self.client.config['bot_name']:
                    if new_thread_message.embeds[0].footer.text is not None:
                        new_thread_message_footer_id_list.append(int(new_thread_message.embeds[0].footer.text))
                    new_thread_message_id_list.append(new_thread_message.id)

            if (thread.parent_id == self.config['forum_new_thread_message']['source_forum_channel_id']
                    and thread.id in new_thread_message_footer_id_list):
                new_thread_message = await target_channel.fetch_message(
                    new_thread_message_id_list[new_thread_message_footer_id_list.index(thread.id)]
                )
                await new_thread_message.delete()

                self.logger.info(
                    f"Deleted thread at source forum channel detected | Thread ID: [{thread.id}], "
                    f"Thread Name: [{thread.name}], Thread Location: [{thread.parent}], "
                    f"Author: [{thread.owner.name}], Author ID: [{thread.owner.id}] | "
                    f"New thread message is successfully deleted"
                )

        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.warning(
                f"Deleted thread detected | Thread ID: [{thread.id}], Thread Name: [{thread.name}], "
                f"Thread Location: [{thread.parent}], Author: [{thread.owner.name}], "
                f"Author ID: [{thread.owner.id}] | Failed when delete new thread message: {exception}"
            )


async def setup(client) -> None:
    await client.add_cog(ForumNewThreadMessage(client))
