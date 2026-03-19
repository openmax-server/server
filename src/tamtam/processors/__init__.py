from .main import MainProcessors
from .auth import AuthProcessors

class Processors(MainProcessors, AuthProcessors):
    pass