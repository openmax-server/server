from .main import MainProcessors
from .auth import AuthProcessors
from .search import SearchProcessors
from .history import HistoryProcessors
from .assets import AssetsProcessors
from .chats import ChatsProcessors
from .contacts import ContactsProcessors
from .messages import MessagesProcessors
from .sessions import SessionsProcessors

class Processors(MainProcessors, 
                 AuthProcessors, 
                 SearchProcessors,
                 HistoryProcessors,
                 AssetsProcessors,
                 ChatsProcessors,
                 ContactsProcessors,
                 MessagesProcessors,
                 SessionsProcessors):
    pass
