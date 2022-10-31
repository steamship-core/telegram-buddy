"""Unit tests for the package."""

from steamship import Steamship

from src.api import MyPackage


def test_greeting():
    """You can test your app like a regular Python object."""
    print("Running")
    client = Steamship()
    app = MyPackage(client=client, config={"default_name": "World"})

    assert app.greet() == "Hello, World."
    assert app.greet(name="Ted") == "Hello, Ted."

    app2 = MyPackage(client=client, config={"default_name": "World", "enthusiastic": True})
    assert app2.greet() == "Hello, World!"
    assert app2.greet(name="Ted") == "Hello, Ted!"
