from steamship import Steamship

from src.api import TelegramBuddy
from utils import use_local_with_ngrok

if __name__ == "__main__":
    client = Steamship()
    use_local_with_ngrok(client, TelegramBuddy, config={
        "botName": "buddy",
        "botPersonality": "happy",
        "botToken": "YOUR-KEY"
    },
    port=8083)
