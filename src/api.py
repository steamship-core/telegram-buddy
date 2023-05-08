"""Description of your app."""
from typing import Type, Optional, Dict, Any

import requests
from steamship.experimental import ChatFile
from steamship.invocable import Config, post, PackageService, InvocableResponse
from steamship import SteamshipError, Tag
import logging
from pydantic import Field
import uuid



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


    @post("answer", public=True)
    def answer(self, question: str, chat_session_id: Optional[str] = None) -> Dict[str, Any]:
        """Endpoint that implements the contract for Steamship embeddable chat widgets. This is a PUBLIC endpoint since these webhooks do not pass a token."""
        logging.info(f"/answer: {question} {chat_session_id}")

        if not chat_session_id:
            chat_session_id = "default"
        
        message_id = str(uuid.uuid4())

        try:
            response = self.prepare_response(question, chat_session_id, message_id)
        except SteamshipError as e:
            response = f"Sorry, I encountered an error while trying to think of a response: {e.message}"

        return {
            "answer": response,
            "sources": [],
            "is_plausible": True,
        }
    

    @post("respond", public=True)
    def respond(self, update_id: int, message: dict) -> InvocableResponse[str]:
        """Endpoint implementing the Telegram WebHook contract. This is a PUBLIC endpoint since Telegram cannot pass a Bearer token."""

        # TODO: must reject things not from the package
        message_text = message['text']
        chat_id = message['chat']['id']
        message_id = message['message_id']
        try:
            response = self.prepare_response(message_text, chat_id, message_id)
        except SteamshipError as e:
            response = f"Sorry, I encountered an error while trying to think of a response: {e.message}"
        if response is not None:
            self.send_response(chat_id, response)

        return InvocableResponse(string="OK")

    @post("info")
    def info(self) -> dict:
        """Endpoint returning information about this bot."""
        resp = requests.get(self.api_root+'/getMe').json()
        logging.info(f"/info: {resp}")
        return {"telegram": resp.get("result")}

    def prepare_response(self, message_text: str, chat_id: int, message_id: int) -> Optional[str]:
        """ Use the LLM to prepare the next response by appending the user input to the file and then generating. """
        chat_file = self.get_file_for_chat(chat_id)

        if self.includes_message(chat_file, message_id):
            return None


        chat_file.append_user_block(text=message_text, tags=[
            Tag(kind="message_id", name=str(message_id))
        ])

        generate_task = chat_file.generate_next_response()
        # TODO: handle moderated input error
        generate_task.wait()
        return generate_task.output.blocks[0].text

    def includes_message(self, file: ChatFile, message_id: int):
        """Determine if the message ID has already been processed in this file by checking Block tags."""
        for block in file.blocks:
            for tag in block.tags:
                if tag.kind == "message_id" and tag.name == str(message_id):
                    return True
        return False

    def get_file_for_chat(self, chat_id: int) -> ChatFile:
        """ Find the File associated with this chat id, or create it """
        file_handle = str(chat_id)
        try:
            chatfile = ChatFile.get(self.client, handle=file_handle)
        except:
            chatfile = self.create_new_file_for_chat(file_handle)
        return chatfile

    def create_new_file_for_chat(self, file_handle: str) -> ChatFile:
        """ Create a new File for this chat id, beginning with the system prompt based on name and personality."""
        max_tokens = self.max_tokens_for_model()
        return ChatFile.create(self.client, handle=file_handle,
           generator_instance_handle=self.gpt4.handle,
           max_generation_tokens=max_tokens,
           initial_system_prompt = f"Your name is {self.config.bot_name}. Your personality is {self.config.bot_personality}.",
        )


    def send_response(self, chat_id: int, text: str):
        """ Send a response to the chat in Telegram """
        reply_params = {'chat_id': chat_id,
                        'text': text,
                        }
        requests.get(
            self.api_root+'/sendMessage',
            params=reply_params)

    def max_tokens_for_model(self) -> int:
        if self.config.use_gpt4:
            # Use 7800 instead of 8000 as buffer for different counting
            return 7800 - self.gpt4.config['max_tokens']
        else:
            # Use 4000 instead of 4097 as buffer for different counting
            return 4097 - self.gpt4.config['max_tokens']


