from abc import ABC, abstractmethod

from ariadne.domain.models.process_model import EndpointModel
from ariadne.domain.models.traces import EndpointChildSpans


class Plugin(ABC):
    """Base class for all plugins."""

    name: str
    display_name: str
    license: str
    description: str

    def __init__(self, config: dict):
        self.config = config


class MiningAlgorithm(Plugin, ABC):
    """Base class for mining algorithm plugins."""

    @abstractmethod
    def mine_process(self, traces: EndpointChildSpans) -> EndpointModel:
        """Mine a process model from the given traces."""
        raise NotImplementedError
