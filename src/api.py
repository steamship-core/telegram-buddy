"""Description of your app."""
import json
from typing import Type, Optional, Dict, Any

import requests
from steamship.invocable import Config, post, get, PackageService, InvocableResponse
from steamship import SteamshipError, File, Block, Tag, Steamship, PluginInstance
from steamship.data.tags.tag_constants import TagKind, RoleTag
import logging
from pydantic import Field
import uuid
import random

from steamship.utils.kv_store import KeyValueStore

from util import filter_blocks_for_prompt_length

import re
from typing import Tuple, Optional


COMMANDS = {
    "challenge": [
        re.compile(r'(challenge|challenge me)', re.IGNORECASE)
    ],
    "magic_challenge": [
        re.compile(r'(magic challenge)\s+(.+)', re.IGNORECASE)
    ],
    "add": [
        re.compile(r'(add|add to)\s+list\s+(.+):\s*(.+)', re.IGNORECASE),
    ],
    "clear": [
        re.compile(r'(delete|clear|remove)\s+list\s+(.+)', re.IGNORECASE),
    ],
    "help": [
        re.compile(r'^(help)$', re.IGNORECASE),
    ]
}

class ChoiceTool:
    client: Steamship
    kvs: KeyValueStore

    def __init__(self, client: Steamship, llm: PluginInstance):
        self.client = client
        self.kvs = KeyValueStore(client, "Choices")
        self.llm = llm

    def get_command_for(self, s: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        for cmd in COMMANDS:
            for r in COMMANDS[cmd]:
                match = re.match(r, s)
                if match:
                    cmd_match = match.group(1)
                    try:
                        arg1 = match.group(2)
                    except:
                        arg1 = None
                    try:
                        arg2 = match.group(3)
                    except:
                        arg2 = None
                    return (cmd, arg1, arg2)
        return None

    def matches(self, s: str) -> bool:
        """Matches an incoming chat message if it knows how to run a command"""
        cmd = self.get_command_for(s)
        if cmd is None:
            return False
        return True

    def run(self, s: str) -> Optional[str]:
        if not self.matches(s):
            return None
        cmd = self.get_command_for(s)

        if cmd[0] == "challenge":
            return self.challenge()
        if cmd[0] == "help":
            return self.help()
        elif cmd[0] == "clear":
            return self.clear(cmd[1])
        elif cmd[0] == "magic_challenge":
            return self.magic_challenge(cmd[1])
        elif cmd[0] == "add":
            return self.add(cmd[1], cmd[2])
        else:
            return f"I'm in a funny state! I don't know what the command {cmd[0]} means"

    def help(self) -> str:
        return """Help is on the way!

I will try to just chat with you using the personality you assigned me. But I also have a few specific features:

To items to a list, say:

"add to list NAME: item1, item2 items"

For example:

"add to list location: outside, inside, on the roof

To clear a list, say: 

"clear list NAME"

To generate a challenge from your lists, say:

"challenge"

To generate a MAGICAL challenge from your lists, say:

"magic challenge VERB"

where VERB makes sense for your lists. For example:  

"magic challenge paint", or 
"magic challenge exercise"
"""


    def clean_name(self, name: str) -> str:
        return name.strip().lower()

    def challenge(self) -> Optional[str]:
        selected = []
        for key, value in self.kvs.items():
            items = value.get("items")
            if items:
                choice = random.choice(items)
                selected.append((key, choice))

        features = "\n".join([f"- {key}: {value}" for (key, value) in selected])
        return f"Here is your challenge!\n\n{features}"

    def magic_challenge(self, verb: str) -> Optional[str]:
        selected = []
        for key, value in self.kvs.items():
            items = value.get("items")
            if items:
                choice = random.choice(items)
                selected.append((key, choice))

        features = "\n".join([f"- {key}: {value}" for (key, value) in selected])
        prompt =  f"Please write an encouraging challenge to me, with a call to action to {verb}. When I {verb}, I want it to involve the following attributes:\n{features}\n\nThe call to action should be short, motivational, and specific to the list of attributes above."

        generate_task = self.llm.generate(text=prompt)
        generate_task.wait()
        return generate_task.output.blocks[0].text


    def clear(self, name: str) -> Optional[str]:
        self.kvs.delete(self.clean_name(name))
        return f"OK! I've cleared the list {name} for you."

    def add(self, name: str, items: str) -> Optional[str]:
        existing_list = self.kvs.get(self.clean_name(name))
        if not existing_list:
            existing_list = {"items": []}
        if not existing_list.get("items"):
            existing_list["items"] = []

        new_items = [item.strip().lower() for item in items.split(",")]
        for item in new_items:
            existing_list["items"].append(item)

        self.kvs.set(self.clean_name(name), existing_list)
        return f"OK! I've added {', '.join(new_items)} to the list {name}."


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
        self.choice_tool = ChoiceTool(self.client, self.gpt4)


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


        # HACKETY HACK HACK - START OF MOM BOT
        try:
            if self.choice_tool.matches(message_text):
                response = self.choice_tool.run(message_text)
                return response
        except Exception as e:
            return f"Uh oh, I got an error! {e}"
        # END OF MOM BOT


        chat_file = self.get_file_for_chat(chat_id)

        if self.includes_message(chat_file, message_id):
            return None


        chat_file.append_block(text=message_text, tags=[
            Tag(kind=TagKind.ROLE, name=RoleTag.USER),
            Tag(kind="message_id", name=str(message_id))
        ])
        chat_file.refresh()
        # Limit total tokens passed to fit in context window
        max_tokens = self.max_tokens_for_model()
        retained_blocks = filter_blocks_for_prompt_length(max_tokens, chat_file.blocks)
        generate_task = self.gpt4.generate(input_file_id=chat_file.id, input_file_block_index_list = retained_blocks,
                                           append_output_to_file=True, output_file_id=chat_file.id)

        # TODO: handle moderated input error
        generate_task.wait()
        return generate_task.output.blocks[0].text

    def includes_message(self, file: File, message_id: int):
        """Determine if the message ID has already been processed in this file by checking Block tags."""
        for block in file.blocks:
            for tag in block.tags:
                if tag.kind == "message_id" and tag.name == str(message_id):
                    return True
        return False

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

    def max_tokens_for_model(self) -> int:
        if self.config.use_gpt4:
            # Use 7800 instead of 8000 as buffer for different counting
            return 7800 - self.gpt4.config['max_tokens']
        else:
            # Use 4000 instead of 4097 as buffer for different counting
            return 4097 - self.gpt4.config['max_tokens']


