"""Description of your app."""
from collections import Counter
from itertools import zip_longest
from typing import Any, Dict, List, Type

from pydantic import parse_obj_as
from steamship import Block, File, PluginInstance, Steamship, Tag
from steamship.app import App, Response, create_handler, post, get
from steamship.plugin.config import Config

class MyApp(App):

    class MyAppConfig(Config):
        """Config object containing required parameters to initialize a MyApp instance."""
        # This config should match the corresponding configuration in your steamship.json

        default_name: str # Required
        enthusiastic: bool = False # Not required

    def config_cls(self) -> Type[Config]:
        """Return the Configuration class."""
        return self.MyAppConfig

    def __init__(self, **kwargs):
      super().__init__(**kwargs)
  
    @get("greet")
    def greet(self, name: str = None) -> Response:
        """Example post endpoint taking a JSON body."""
        punct = "!" if self.config.enthusiastic else "."
        name = name or self.config.default_name
        return Response(string=f"Hello, {name}{punct}")

handler = create_handler(MyApp)



