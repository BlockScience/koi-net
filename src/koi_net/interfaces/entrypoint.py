from typing import Protocol


class EntryPoint(Protocol):
    def run(self): ...