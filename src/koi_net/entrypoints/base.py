from abc import ABC, abstractmethod


class EntryPoint(ABC):
    """Abstract class for entry point components."""
    @abstractmethod
    def run(self): 
        ...