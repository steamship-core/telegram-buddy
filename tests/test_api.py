import json
from steamship import Steamship
from src.api import QuestionAnswer
from steamship.data.embedding import EmbedAndSearchResponse

import os
from typing import List

__copyright__ = "Steamship"
__license__ = "MIT"

def test_greeting():
    """We can test the app like a regular python object!"""
    client = Steamship()
    app = EmptyApp(client)

    assert(app.greet().body == "Hello, World!")
    assert(app.greet(name="Ted").body == "Hello, Ted!")
