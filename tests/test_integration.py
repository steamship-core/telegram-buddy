"""Unit tests for the package."""

import json
import random
import string
from pathlib import Path

from steamship import Steamship

STEAMSHIP_JSON = Path(__file__).parent.parent / "steamship.json"


def package_name():
    """Return the package name recorded in steamship.json."""
    with open(STEAMSHIP_JSON, "r") as f:
        manifest = json.loads(f.read())
        return manifest.get("handle")


def random_name() -> str:
    """Return a random name suitable for a handle that has low likelihood of colliding with another.

    Output format matches test_[a-z0-9]+, which should be a valid handle.
    """
    letters = string.digits + string.ascii_letters
    return f"test_{''.join(random.choice(letters) for _ in range(10))}".lower()  # noqa: S311


def test_greeting():
    """When your package runs in the cloud, you invoke it with Steamship.use."""
    # Create an instance of this package with a random name.
    instance = Steamship.use(package_name(), random_name(), config={"default_name": "Beautiful"})

    assert instance.invoke("greet") == "Hello, Beautiful."
    assert instance.invoke("greet", name="Ted") == "Hello, Ted."

    instance2 = Steamship.use(
        package_name(), random_name(), config={"default_name": "World", "enthusiastic": True}
    )

    assert instance2.invoke("greet") == "Hello, World!"
    assert instance2.invoke("greet", name="Ted") == "Hello, Ted!"
