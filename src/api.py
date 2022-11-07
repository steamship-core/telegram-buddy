"""Description of your app."""
from typing import Type

from steamship.invocable import Config, create_handler, post, PackageService


class MyPackageConfig(Config):
    """Config object containing required parameters to initialize a MyPackage instance."""

    # This config should match the corresponding configuration in your steamship.json
    default_name: str  # Required
    enthusiastic: bool = False  # Not required


class MyPackage(PackageService):
    """Example steamship Package."""

    config: MyPackageConfig

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def config_cls(self) -> Type[Config]:
        """Return the Configuration class."""
        return MyPackageConfig

    @post("greet")
    def greet(self, name: str = None) -> str:
        """Return a greeting to the user."""
        punct = "!" if self.config.enthusiastic else "."
        name = name or self.config.default_name
        return f"Hello, {name}{punct}"


handler = create_handler(MyPackage)
