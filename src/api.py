from typing import Dict
from steamship import Steamship
from steamship.app import App, Response, Error, post, create_handler

class EmptyApp(App):
  def __init__(self, client: Steamship):
    # In production, the lambda handler will provide a Steamship client:
    # - Authenticated to the appropriate user
    # - Bound to the appropriate space
    self.client = client
  
  @post('greet')
  def greet(self, name: str = None) -> Response:
    """Example post endpoint taking a JSON body."""
    if name is None:
      name = "World"
   
    return Response(text="Hello, {}!".format(name))

handler = create_handler(EmptyApp)



