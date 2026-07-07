from .assets import AssetsProcessors
from .auth import AuthProcessors
from .calls import CallsProcessors
from .chats import ChatsProcessors
from .complaints import ComplaintsProcessors
from .contacts import ContactsProcessors
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
    ComplaintsProcessors,
    ContactsProcessors,
    FoldersProcessors,
    HistoryProcessors,
    MainProcessors,
    MessagesProcessors,
    SearchProcessors,
    SessionsProcessors
):
    pass