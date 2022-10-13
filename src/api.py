"""Description of your app."""
from typing import Type

from steamship.app import App, Response, create_handler, get
from steamship.plugin.config import Config


class MyPackage(App):
    """Example steamship Package."""

    class MyPackageConfig(Config):
        """Config object containing required parameters to initialize a MyApp instance."""

        # This config should match the corresponding configuration in your steamship.json
        defaultname: str  # Required
        enthusiastic: bool = False  # Not required

    def config_cls(self) -> Type[Config]:
        """Return the Configuration class."""
        return self.MyPackageConfig

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = MyPackage.MyPackageConfig(**kwargs)

    @get("greet")
    def greet(self, name: str = None) -> Response:
        """Return a greeting to the user."""
        punct = "!" if self.config.get("enthusiastic") else "."
        name = name or self.config.get("defaultname")
        return Response(string=f"Hello, {name}{punct}")


handler = create_handler(MyPackage)
