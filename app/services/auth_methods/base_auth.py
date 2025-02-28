from abc import ABC, abstractmethod

class BaseAuth(ABC):
    @abstractmethod
    def authenticate(self, *args, **kwargs):
        pass 