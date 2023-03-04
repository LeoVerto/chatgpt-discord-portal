import openai


class AvatarManager:
    def __init__(self):
        self.avatars = {}

    def get_avatar(self, author: str) -> str:
        if author in self.avatars:
            return self.avatars.get(author)
        else:
            response = openai.Image.create(
                prompt=f"Discord avatar for user {author}", n=1, size="256x256"
            )
            image_url = response["data"][0]["url"]
            self.avatars[author] = image_url
            return image_url
