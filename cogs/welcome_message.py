import discord
from discord.ext import commands


class WelcomeMessage(commands.Cog, name='Welcome Message'):
    def __init__(self, client) -> None:
        self.client = client
        self.config = self.client.config
        self.logger = self.client.logger

    '''
    Send a welcome message to the welcome channel when a new member joins the server
    '''
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        welcome_channel = self.client.get_channel(int(self.config['welcome_message_settings']['welcome_channel_id']))
        welcome_message = f"{self.config['welcome_message_settings']['welcome_message']}"
        embed = discord.Embed().set_image(url=self.config['welcome_message_settings']['welcome_image_url'])

        try:
            await welcome_channel.send(
                welcome_message.format(
                    member=getattr(member, self.config['welcome_message_settings']['member_function']),
                    rules_channel_id=int(self.config['welcome_message_settings']['rules_channel_id'])),
                embed=embed)

            self.logger.info(f"Successfully sent welcome message to {member.name} width member id {member.id}")
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.error(
                f"Error sending welcome message | Member ID: [{member.id}], Member Name: [{member.name}], "
                f"| {exception}"
            )


async def setup(client) -> None:
    await client.add_cog(WelcomeMessage(client))
