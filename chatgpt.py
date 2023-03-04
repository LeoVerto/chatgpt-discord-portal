import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import openai
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

load_dotenv()

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


@dataclass
class ChatGPT:
    system: str = None
    stop_str: str = "<|DONE|>"
    messages: List[dict] = field(default_factory=list)
    token_total: int = 0
    user_seed: str = None
    temperature: float = 1

    def __post_init__(self):
        self.console = Console(width=60, record=True)
        if self.system:
            self.messages.append({"role": "system", "content": self.system})

        if self.user_seed:  # seed with a basic human input
            self.user_act(self.user_seed)
            self.assistant_act()

    def __call__(self):
        result = ""
        self.console.print(
            "Started new conversation.",
            highlight=False,
            style="italic",
        )

        while self.stop_str not in result:
            self.user_act()
            result = self.assistant_act()

        self.console.print(
            f"End of conversation.\n{self.token_total:,} total ChatGPT tokens used.",
            highlight=False,
            style="italic",
        )
        self.console.save_html(f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

    def user_act(self, user_input=None):
        if not user_input:
            user_input = self.console.input().strip()
            self.console.print("You:", user_input, sep="\n", highlight=False)
        else:
            self.console.print(
                user_input,
                highlight=False,
                style="sea_green1",
                sep="",
            )
        self.messages.append({"role": "user", "content": user_input})
        return

    def assistant_act(self):
        result = self.execute()
        self.console.print(
            Markdown(result.replace(self.stop_str, "")),
            highlight=False,
            style="bright_magenta",
            sep="",
        )
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


if __name__ == "__main__":
    ChatGPT(system=system, user_seed=user_seed)()
