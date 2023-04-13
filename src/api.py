"""Description of your app."""

from typing import Type, Optional, Dict, Any
from steamship import SteamshipError, File, Block, Tag
from steamship.data.tags.tag_constants import TagKind, RoleTag

from bot_base import TelegramBuddyBase
from data_model import TelegramChatOutput, TelegramChatInput
from util import filter_blocks_for_prompt_length

class TelegramBuddy(TelegramBuddyBase):
    """Telegram Buddy package.

    - Stores individual chats in Steamship Files for chat history.
    - Permits selection of ChatGPT and GPT-4

    See the base class in `bot_base.py` for the full harness. This subclass contains only the
    core "response" method that will result in a message being sent back to Telegram.
    """

    def __init__(self, **kwargs):
        """This initialization method is where you should register any Steamship plugins.

        - GPT
        - DALL-E
        - Elevenlabs
        - ..etc
        """
        super().__init__(**kwargs)

        # Select which GPT model to use
        model = "gpt-4" if self.config.use_gpt4 else "gpt-3.5-turbo"
        self.gpt4 = self.client.use_plugin("gpt-4", config={"model": model, "temperature": 0.8})

    def prepare_response(self, input: TelegramChatInput) -> Optional[TelegramChatOutput]:
        """Respond to an incoming chat message.

        Long-running state management is done by appending the user input to a Steamship file and then generating based
        on that file.
        """
        chat_file = self.get_file_for_chat(input.chat_id)

        if self.includes_message(chat_file, input.message_id):
            return None

        chat_file.append_block(text=input.text, tags=[
            Tag(kind=TagKind.ROLE, name=RoleTag.USER),
            Tag(kind="message_id", name=str(input.message_id))
        ])
        chat_file.refresh()
        # Limit total tokens passed to fit in context window
        max_tokens = self.max_tokens_for_model()
        retained_blocks = filter_blocks_for_prompt_length(max_tokens, chat_file.blocks)
        generate_task = self.gpt4.generate(input_file_id=chat_file.id, input_file_block_index_list = retained_blocks,
                                           append_output_to_file=True, output_file_id=chat_file.id)
        # TODO: handle moderated input error
        generate_task.wait()

        text = generate_task.output.blocks[0].text
        return TelegramChatOutput(text=text)

