"""Classes to help structure the I/O for easier extension and hacking."""
from typing import Optional, List
from steamship.base.model import CamelModel


class TelegramChatInput(CamelModel):
    """Extends ChatInput to provide Telegram specific handling."""
    chat_id: Optional[int]
    message_id: int
    update_id: Optional[int]

    from_role: Optional[str]
    from_handle: Optional[str]
    from_id: Optional[str]
    from_first: Optional[str]
    from_last: Optional[str]

    text: str

    @staticmethod
    def from_steamship_chat_widget(question: str, chat_session_id: Optional[str] = None) -> "TelegramChatInput":
        if not chat_session_id:
            chat_session_id = "default"

        message_id = 000

        return TelegramChatInput(
            text=question,
            chat_id=chat_session_id,
            message_id=message_id
        )

    @staticmethod
    def from_telegram_message(update_id: int, message: dict) -> "TelegramChatInput":
        user = message.get("from", {})
        return TelegramChatInput(
            update_id = update_id,
            text = message.get("text"),
            chat_id = message.get("chat", {}).get("id"),
            message_id = message.get("message_id"),
            from_handle = user.get("username"),
            from_first = user.get("first_name")
        )


class TelegramChatOutput(CamelModel):
    """Extends ChatOutput to provide Telegram specific handling."""
    text: Optional[str]
    image_url: Optional[str]

    # Confidence
    is_plausible: Optional[bool]
    sources: List[any]


