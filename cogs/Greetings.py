import discord
from discord.ext import commands


class Greetings(commands.Cog, name='Greetings'):
    def __init__(self, client) -> None:
        self.client = client
        self.logger = self.client.logger

    '''
    Send a welcome message to the welcome channel when a new member joins the server
    '''
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        welcome_channel = self.client.get_channel(int(self.client.config['Greetings']['welcome_channel_id']))
        welcome_message = f"{self.client.config['Greetings']['welcome_message']}"
        embed = discord.Embed().set_image(url=self.client.config['Greetings']['welcome_image_url'])

        try:
            await welcome_channel.send(
                welcome_message.format(
                    member=getattr(member, self.client.config['Greetings']['member_function']),
                    rules_channel_id=int(self.client.config['Greetings']['rules_channel_id'])),
                embed=embed)

            self.logger.info(f"Sent welcome message to {member.name}")
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.error(f"Error sending welcome message, {exception}")


async def setup(client) -> None:
    await client.add_cog(Greetings(client))
