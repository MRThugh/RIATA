"""
Backward compatibility facade for InputWidget in R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from app.ui.input.message_input import MessageInputWidget

InputWidget = MessageInputWidget

__all__ = ["InputWidget", "MessageInputWidget"]
