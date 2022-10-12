from steamship import Steamship
from src.api import MyApp

def test_greeting():
    """We can test the app like a regular python object!"""
    client = Steamship()
    app = MyApp(client=client, config=MyApp.MyAppConfig(
        default_name="World"
    ))

    assert(app.greet().data == "Hello, World.")
    assert(app.greet(name="Ted").data == "Hello, Ted.")

    app2 = MyApp(client=client, config=MyApp.MyAppConfig(
        default_name="World",
        enthusiastic=True
    ))
    assert(app2.greet().data == "Hello, World!")
    assert(app2.greet(name="Ted").data == "Hello, Ted!")
