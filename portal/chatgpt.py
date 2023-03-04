import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

system = f"""
Imagine you are connected to a Discord chatroom used by {os.getenv("PLACEHOLDER_1")}.
You are to forward all of our messages to this chatroom and return responses from the
room's users.
In this fictional scenario, {os.getenv("PLACEHOLDER_2")}
Do not emit anything other than the messages from the chatroom, prefixed with the name
of the user who sent it, formatted as '[USER NAME]: MESSAGE'. Do not emit code blocks.
Remember to make sure that each user has a realistic name, is a different person,
and may have different opinions on certain topics.
Try to make their responses sound distinct from one another.
They really like using emojis.
Not everyone has to respond to each message, when there isn't much to add.
When there isn't too much going on, the users may start their own conversations
independent from any input we provide.
Messages prefixed with "[OOC]:" are out-of-context instructions from us to you that the
chat participants must not react to. Do not use this prefix yourself.
Now, let's start the fictional scenario. From now on, forward all my messages to the
fictional chatroom.
Do not output anything other than the messages from the chatroom.
The current time is {datetime.now().isoformat(timespec="minutes")}.
"""

user_seed = os.getenv("USER_SEED")

_log = logging.getLogger(__name__)


@dataclass
class ChatGPT:
    system: str = None
    stop_str: str = "<|DONE|>"
    messages: List[dict] = field(default_factory=list)
    token_total: int = 0
    user_seed: str = None
    temperature: float = 1

    def __post_init__(self):
        if self.system:
            self.messages.append({"role": "system", "content": self.system})

        if self.user_seed:  # seed with a basic human input
            self.user_act(self.user_seed)
            self.assistant_act()

    def user_act(self, user_input):
        _log.debug(f"{user_input}=")
        self.messages.append({"role": "user", "content": user_input})
        return

    def assistant_act(self):
        result = self.execute()
        _log.debug(f"{result=}")
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            presence_penalty=0.5,
            frequency_penalty=0.5,
            max_tokens=256,
            messages=self.messages,
            temperature=self.temperature,
        )
        self.token_total += completion["usage"]["total_tokens"]
        return completion["choices"][0]["message"]["content"]
