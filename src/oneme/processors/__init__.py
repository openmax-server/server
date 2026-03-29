from .assets import AssetsProcessors
from .auth import AuthProcessors
from .calls import CallsProcessors
from .chats import ChatsProcessors
from .complains import ComplainsProcessors
from .folders import FoldersProcessors
from .history import HistoryProcessors
from .main import MainProcessors
from .messages import MessagesProcessors
from .search import SearchProcessors
from .sessions import SessionsProcessors

class Processors(
    AssetsProcessors,
    AuthProcessors,
    CallsProcessors,
    ChatsProcessors,
    ComplainsProcessors,
    FoldersProcessors,
    HistoryProcessors,
    MainProcessors,
    MessagesProcessors,
    SearchProcessors,
    SessionsProcessors
):
    pass