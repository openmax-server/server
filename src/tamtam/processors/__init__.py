from .main import MainProcessors
from .auth import AuthProcessors
from .search import SearchProcessors
from .history import HistoryProcessors

class Processors(MainProcessors, 
                 AuthProcessors, 
                 SearchProcessors,
                 HistoryProcessors):
    pass