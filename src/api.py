"""Description of your app."""
from typing import Type, Optional, Dict, Any, cast, List

from steamship.experimental.package_starters.telegram_bot import TelegramBotConfig, TelegramBot
from steamship.experimental.transports.chat import ChatMessage
from steamship.invocable import Config, post, get, PackageService, InvocableResponse
from steamship import SteamshipError, File, Block, Tag, PluginInstance
from steamship.data.tags.tag_constants import TagKind, RoleTag
from pydantic import Field

from util import filter_blocks_for_prompt_length


class TelegramBuddyConfig(TelegramBotConfig):
    """Config object containing required parameters to initialize a MyPackage instance."""

    bot_name: str = Field(description='What the bot should call itself')
    bot_personality: str = Field(description='Complete the sentence, "The bot\'s personality is _." Writing a longer, more detailed description will yield less generic results.')
    use_gpt4: bool = Field(False, description="If True, use GPT-4 instead of GPT-3.5 to generate responses. GPT-4 creates better responses at higher cost and with longer wait times.")

class TelegramBuddy(TelegramBot):
    """Telegram Buddy package.  Stores individual chats in Steamship Files for chat history."""

    config: TelegramBuddyConfig
    gpt4: Optional[PluginInstance]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = "gpt-4" if self.config.use_gpt4 else "gpt-3.5-turbo"
        self.gpt4 = None

    def get_gpt4(self) -> PluginInstance:
        if self.gpt4 is not None:
            return self.gpt4
        else:
            self.gpt4 = self.client.use_plugin("gpt-4", config={"model": self.model, "temperature": 0.8})
            return self.gpt4

    @classmethod
    def config_cls(cls) -> Type[Config]:
        """Return the Configuration class."""
        return TelegramBuddyConfig

    def create_response(self, incoming_message: ChatMessage) -> Optional[List[ChatMessage]]:
        """ Use the LLM to prepare the next response by appending the user input to the file and then generating. """
        chat_file = self.get_file_for_chat(incoming_message.get_chat_id())

        if self.includes_message(chat_file, incoming_message.get_message_id()):
            return None

        if incoming_message.text is None or incoming_message.text == "":
            return None

        chat_file.append_block(text=incoming_message.text, tags=[
            Tag(kind=TagKind.ROLE, name=RoleTag.USER),
            Tag(kind="message_id", name=incoming_message.get_message_id())
        ])
        chat_file.refresh()
        # Limit total tokens passed to fit in context window
        max_tokens = self.max_tokens_for_model()
        retained_blocks = filter_blocks_for_prompt_length(max_tokens, chat_file.blocks)
        generate_task = self.get_gpt4().generate(input_file_id=chat_file.id, input_file_block_index_list = retained_blocks,
                                           append_output_to_file=True, output_file_id=chat_file.id)

        # TODO: handle moderated input error
        generate_task.wait()
        return [ChatMessage.from_block(block, chat_id=incoming_message.get_chat_id()) for block in generate_task.output.blocks]

    def includes_message(self, file: File, message_id: str):
        """Determine if the message ID has already been processed in this file by checking Block tags."""
        for block in file.blocks:
            for tag in block.tags:
                if tag.kind == "message_id" and tag.name == message_id:
                    return True
        return False

    def get_file_for_chat(self, chat_id: str) -> File:
        """ Find the File associated with this chat id, or create it """
        file_handle = chat_id
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


    def max_tokens_for_model(self) -> int:
        if self.config.use_gpt4:
            # Use 7800 instead of 8000 as buffer for different counting
            return 7800 - self.get_gpt4().config['max_tokens']
        else:
            # Use 4000 instead of 4097 as buffer for different counting
            return 4097 - self.get_gpt4().config['max_tokens']





