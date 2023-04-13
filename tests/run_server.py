from steamship import Steamship

from src.api import TelegramBuddy
from utils import use_local_with_ngrok

if __name__ == "__main__":
    client = Steamship()
    use_local_with_ngrok(client, TelegramBuddy, config={
        "botName": "ted",
        "botPersonality": "happy",
        "botToken": "5720939969:AAEQTYUatOLJz2t6mpR7kkYqlE2850DSFMg"
    },
    port=8082)
