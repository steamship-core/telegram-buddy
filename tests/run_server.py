from steamship import Steamship

from src.api import TelegramBuddy
from utils import use_local_with_ngrok

if __name__ == "__main__":
    client = Steamship()
    use_local_with_ngrok(client, TelegramBuddy, config={
        "botName": "buddy",
        "botPersonality": "happy",
        "botToken": "6122588092:AAEioCXNaLm6zH7dfi-pvGoxcU6BrgmQrX8"
    },
    port=8083)
