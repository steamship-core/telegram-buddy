"""Unit tests for the package."""

from steamship import Steamship

from src.api import MyPackage


def test_greeting():
    """Test the app like a regular Python object."""
    client = Steamship()
    app = MyPackage(client=client, config={"default_name": "World"})

    assert app.greet().data == "Hello, World."
    assert app.greet(name="Ted").data == "Hello, Ted."

    app2 = MyPackage(client=client, config={"default_name": "World", "enthusiastic": True})
    assert app2.greet().data == "Hello, World!"
    assert app2.greet(name="Ted").data == "Hello, Ted!"
