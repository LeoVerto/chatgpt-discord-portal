import asyncio
import os
import random
import re
import time

import aiohttp
import discord
from dotenv import load_dotenv
from discord import app_commands

import chatgpt
from avatar import AvatarManager

load_dotenv()

chat_regex = re.compile(r"\[(.*)\]: (.*)")
cooldown = int(os.getenv("COOLDOWN"))
last_invocation = time.time() - cooldown
channel_whitelist = map(int, os.getenv("DISCORD_CHANNEL_IDS").split(","))
guild = discord.Object(id=int(os.getenv("DISCORD_GUILD")))

chatbot = None
avatars = None


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


# discord setup
intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


async def process_chatlog(chat: str):
    matches = re.findall(chat_regex, chat)

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(
            os.getenv("DISCORD_WEBHOOK"), session=session
        )

        for match in matches:
            author = match[0]
            msg = match[1]

            if author == "OOC":
                continue

            await webhook.send(
                msg, username=author, avatar_url=avatars.get_avatar(author)
            )
            await asyncio.sleep(2 * random.random() + 0.02 * len(msg))


@client.event
async def on_message(message: discord.Message):
    global last_invocation, chatbot, channel_whitelist

    if message.author.bot:
        return

    if message.channel.id in channel_whitelist:
        print(f"Received discord message '{message.content}'")

        cur_time = time.time()
        if (cd := last_invocation + cooldown - cur_time) > 0:
            print(f"Message sent to soon, still cooling down for {cd:.1f}s")
            await message.add_reaction("\U0001F975")
            return

        last_invocation = cur_time
        user_input = f"[{message.author.display_name}]: {message.content}"
        chatbot.user_act(user_input=user_input)
        answer = chatbot.assistant_act()
        print("Received answer")
        print(answer)
        asyncio.create_task(process_chatlog(answer))


@client.tree.command(name="reset", description="reset portal")
@app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild_id, i.user.id))
async def reset(context):
    global chatbot, channel_whitelist

    if context.channel.id not in channel_whitelist:
        print("Attempt to run reset in non-whitelisted channel.")

    print("Triggering reset")
    chatbot = chatgpt.ChatGPT(system=chatgpt.system, user_seed=chatgpt.user_seed)
    await context.channel.send("The portal briefly snaps closed, then reopens again.")


@client.tree.command(
    name="generate", description="generate more messages without user input"
)
@app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
async def generate(context):
    global chatbot, channel_whitelist

    if context.channel.id not in channel_whitelist:
        print("Attempt to run generate in non-whitelisted channel.")

    print("Generating more output")
    chatbot.user_act(user_input="<OOC>: generate some more messages, please")
    answer = chatbot.assistant_act()
    print(answer)
    asyncio.create_task(process_chatlog(answer))


if __name__ == "__main__":
    chatbot = chatgpt.ChatGPT(system=chatgpt.system, user_seed=chatgpt.user_seed)
    avatars = AvatarManager()
    client.run(os.getenv("DISCORD_TOKEN"))
