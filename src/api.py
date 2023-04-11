"""Description of your app."""
import json
from typing import Type

import requests
from steamship.invocable import Config, post, PackageService, InvocableResponse
from steamship import SteamshipError, File, Block, Tag
from steamship.data.tags.tag_constants import TagKind, RoleTag
import logging
from pydantic import Field

class TelegramBuddyConfig(Config):
    """Config object containing required parameters to initialize a MyPackage instance."""

    bot_name: str = Field(description='What the bot should call itself')
    bot_personality: str = Field(description='Complete the sentence, "The bot\'s personality is _." Writing a longer, more detailed description will yield less generic results.')
    bot_token: str = Field(description="The secret token for your Telegram bot")
    use_gpt4: bool = Field(False, description="If True, use GPT-4 instead of GPT-3.5 to generate responses. GPT-4 creates better responses at higher cost and with longer wait times.")

class TelegramBuddy(PackageService):
    """Telegram Buddy package.  Stores individual chats in Steamship Files for chat history."""

    config: TelegramBuddyConfig

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_root = f'https://api.telegram.org/bot{self.config.bot_token}'
        model = "gpt-4" if self.config.use_gpt4 else "gpt-3.5-turbo"
        self.gpt4 = self.client.use_plugin("gpt-4", config={"model": model, "temperature": 0.8})


    @classmethod
    def config_cls(cls) -> Type[Config]:
        """Return the Configuration class."""
        return TelegramBuddyConfig

    def instance_init(self):
        """This instance init method is called automatically when an instance of this package is created. It registers the URL of the instance as the Telegram webhook for messages."""
        webhook_url = self.context.invocable_url + 'respond'
        response = requests.get(f'{self.api_root}/setWebhook', params={"url": webhook_url, "allowed_updates": ['message']})
        if not response.ok:
            raise SteamshipError(f"Could not set webhook for bot. Webhook URL was {webhook_url}. Telegram response message: {response.text}")
        logging.info(f"Initialized webhook with URL {webhook_url}")


    @post("respond", public=True)
    def respond(self, update_id: int, message: dict) -> InvocableResponse[str]:
        """ This is the responder method for the telegram webhook. It is public since Telegram cannot pass a Bearer token. """

        # TODO: must reject things not from the package
        message_text = message['text']
        chat_id = message['chat']['id']
        logging.info(f"{message_text} {chat_id} {type(chat_id)}")
        response = self.prepare_response(message_text, chat_id)
        self.send_response(chat_id, response)

        return InvocableResponse(string="OK")


    def prepare_response(self, message_text: str, chat_id: int) -> str:
        """ Use the LLM to prepare the next response by appending the user input to the file and then generating. """
        chat_file = self.get_file_for_chat(chat_id)
        chat_file.append_block(text=message_text, tags=[Tag(kind=TagKind.ROLE, name=RoleTag.USER)])
        generate_task = self.gpt4.generate(input_file_id=chat_file.id, append_output_to_file=True, output_file_id=chat_file.id)

        # TODO: handle errors here (including moderated input)
        generate_task.wait()
        return generate_task.output.blocks[0].text

    def get_file_for_chat(self, chat_id: int) -> File:
        """ Find the File associated with this chat id, or create it """
        file_handle = str(chat_id)
        try:
            file = File.get(self.client, handle=file_handle)
        except:
            file = self.create_new_file_for_chat(file_handle)
        return file

    def create_new_file_for_chat(self, file_handle: str):
        """ Create a new File for this chat id, beginning with the system prompt based on name and personality."""
        return File.create(self.client, handle=file_handle, blocks=[
            Block(text=f"Your name is {self.config.bot_name}. Your personality is {self.config.bot_personality}.",
                  tags=[Tag(kind=TagKind.ROLE, name=RoleTag.SYSTEM)])
        ])


    def send_response(self, chat_id: int, text: str):
        """ Send a response to the chat in Telegram """
        reply_params = {'chat_id': chat_id,
                        'text': text,
                        }
        requests.get(
            self.api_root+'/sendMessage',
            params=reply_params)




