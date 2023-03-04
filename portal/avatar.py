import json
import os

import openai


class AvatarManager:
    avatar_db = "avatars.json"

    def __init__(self):
        self.avatars = {}
        self.load_db()
        self.dalle_avatars = os.getenv("DALLE_AVATARS", False)

    def load_db(self):
        if os.path.exists(self.avatar_db):
            with open(self.avatar_db, "r") as f:
                self.avatars = json.load(f)

    def save_db(self):
        with open(self.avatar_db, "w") as f:
            json.dump(self.avatars, f)

    def get_avatar(self, author: str) -> str:
        if author in self.avatars:
            return self.avatars.get(author)
        elif self.dalle_avatars:
            try:
                response = openai.Image.create(
                    prompt=f"Discord avatar for user {author}", n=1, size="256x256"
                )
                image_url = response["data"][0]["url"]
            except openai.error.OpenAIError as e:
                print(e.http_status)
                print(e.error)
                return ""

            self.avatars[author] = image_url
            self.save_db()
            return image_url
        else:
            return ""
