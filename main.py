import asyncio
import os
import random
import re
import time

import aiohttp
import discord
from dotenv import load_dotenv

import chatgpt

load_dotenv()

# discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

chat_regex = re.compile(r"\[(.*)\]: (.*)")
cooldown = int(os.getenv("COOLDOWN"))
last_invocation = time.time() - cooldown

chatbot = None


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
            await webhook.send(msg, username=author)
            await asyncio.sleep(2 * random.random() + 0.02 * len(msg))


@client.event
async def on_message(message: discord.Message):
    global last_invocation, chatbot

    if message.author.bot:
        return

    if message.channel.id in map(int, os.getenv("DISCORD_CHANNEL_IDS").split(",")):
        print(f"Received discord message '{message.content}'")

        if message.content.startswith("?reset"):
            print("Triggering reset")
            chatbot = chatgpt.ChatGPT(
                system=chatgpt.system, user_seed=chatgpt.user_seed
            )
            await message.channel.send(
                "The portal briefly snaps closed, then reopens again."
            )
            return

        cur_time = time.time()
        if (cd := last_invocation + cooldown - cur_time) > 0:
            print(f"Message sent to soon, still cooling down for {cd:.1f}s")
            await message.add_reaction("\U0001F975")
            return

        last_invocation = cur_time
        question = f"[{message.author.display_name}]: {message.content}"
        chatbot.user_act(user_input=question)
        answer = chatbot.assistant_act()
        print("Received answer")
        print(answer)
        asyncio.create_task(process_chatlog(answer))


if __name__ == "__main__":
    chatbot = chatgpt.ChatGPT(system=chatgpt.system, user_seed=chatgpt.user_seed)
    client.run(os.getenv("DISCORD_TOKEN"))
