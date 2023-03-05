import asyncio
import logging
import os
import random
import re
import time
from datetime import datetime

import aiohttp
import discord
from discord import app_commands, utils

from portal.chatgpt import ChatGPT, system, user_seed
from portal.avatar import AvatarManager

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)
utils.setup_logging()

chat_regex = re.compile(r"\[(\w*)\]: (.*)", re.DOTALL)
cooldown = int(os.getenv("COOLDOWN"))


class PortalClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.guild = discord.Object(id=int(os.getenv("DISCORD_GUILD")))
        self.last_invocation = time.time() - cooldown
        self.channel_whitelist = list(
            map(int, os.getenv("DISCORD_CHANNEL_IDS").split(","))
        )
        self.chatbot = self.new_chatbot()
        self.avatar_man = AvatarManager()
        self.start_time = datetime.now()

    def new_chatbot(self):
        return ChatGPT(system=system, user_seed=user_seed)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=self.guild)
        await self.tree.sync(guild=self.guild)

    async def on_ready(self):
        _log.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.channel.id in self.channel_whitelist:
            _log.debug(f"Input: {message.content}")

            cur_time = time.time()
            if (cd := self.last_invocation + cooldown - cur_time) > 0:
                _log.warning(f"Message sent to soon, still cooling down for {cd:.1f}s")
                await message.add_reaction("\U0001F975")
                return

            self.last_invocation = cur_time

            if message.reference and message.reference.cached_message:
                referenced = message.reference.cached_message
                message_prefix = f"@{referenced.author.display_name} "
            else:
                message_prefix = ""
            user_input = (
                f"[{message.author.display_name}]: {message_prefix}{message.content}"
            )

            self.chatbot.user_act(user_input=user_input)
            answer = self.chatbot.assistant_act()
            _log.debug(f"Output: {answer}")
            asyncio.create_task(self.process_chatlog(answer))

    async def process_chatlog(self, chat: str):
        matches = re.findall(chat_regex, chat)

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(
                os.getenv("DISCORD_WEBHOOK"), session=session
            )
            for match in matches:
                author = match[0]
                msg = match[1].strip()

                if author == "OOC":
                    continue

                await webhook.send(
                    msg, username=author, avatar_url=self.avatar_man.get_avatar(author)
                )
                await asyncio.sleep(2 * random.random() + 0.02 * len(msg))


# discord setup
intents = discord.Intents.default()
intents.message_content = True
client = PortalClient(intents=intents)


@client.tree.command(description="reset portal")
@app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild_id, i.user.id))
async def reset(interaction: discord.Interaction):
    if interaction.channel.id not in client.channel_whitelist:
        _log.warning("Attempt to run reset in non-whitelisted channel.")

    _log.info("Resetting conversation")
    await interaction.response.send_message("Resetting conversation", ephemeral=True)
    client.chatbot = client.new_chatbot()
    await interaction.channel.send(
        "The portal briefly snaps closed, then reopens again."
    )


@client.tree.command(description="generate more messages without user input")
@app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
async def generate(interaction: discord.Interaction):
    if interaction.channel.id not in client.channel_whitelist:
        _log.warning("Attempt to run generate in non-whitelisted channel.")

    _log.info("Generating more output")
    await interaction.response.send_message("Generating more output", ephemeral=True)
    client.chatbot.user_act(user_input="<OOC>: generate some more messages, please")
    answer = client.chatbot.assistant_act()
    _log.debug(f"Output: {answer}")
    asyncio.create_task(client.process_chatlog(answer))


@client.tree.command(description="bot status")
async def status(interaction: discord.Interaction):
    if interaction.channel.id not in client.channel_whitelist:
        _log.warning("Attempt to run generate in non-whitelisted channel.")

    await interaction.response.send_message(
        f"Start time: {client.start_time.isoformat()}\n"
        f"Tokens used: {client.chatbot.token_total}",
        ephemeral=True,
    )


def main():
    client.run(os.getenv("DISCORD_TOKEN"), log_handler=None)
