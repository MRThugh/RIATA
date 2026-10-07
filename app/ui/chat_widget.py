"""
Backward compatibility facade for ChatWidget in R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from app.ui.chat.chat_view import ChatView

ChatWidget = ChatView

__all__ = ["ChatWidget", "ChatView"]
