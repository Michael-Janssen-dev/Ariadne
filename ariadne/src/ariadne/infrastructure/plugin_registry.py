from importlib.metadata import entry_points
from typing import Generic, Iterable, TypeVar
from ariadne.domain.plugins import ConformanceChecker, Plugin, MiningAlgorithm

import logging

P = TypeVar("P", bound=Plugin)


logger = logging.getLogger(__name__)


class Registry(Generic[P]):
    def __init__(self, plugin_class: type[P], entry_point_group: str) -> None:
        self._registry: dict[str, type[P]] = {}
        self.entry_point_group = entry_point_group
        self.plugin_abc = plugin_class
        self._initialized = False

    def _load_plugins(self):
        """Load mining algorithms from entry points"""
        for entry_point in entry_points(group=self.entry_point_group):
            try:
                algorithm_class = entry_point.load()

                if issubclass(algorithm_class, self.plugin_abc):
                    self._registry[algorithm_class.name] = algorithm_class
                else:
                    logger.warning(
                        f"Warning: Plugin {entry_point.name} doesn't implement {self.plugin_abc.__name__} protocol"
                    )
            except Exception as e:
                logger.error(f"Failed to load mining plugin {entry_point.name}: {e}")
                pass
        self._initialized = True

    def __getitem__(self, name: str) -> type[P]:
        self._initialize()
        return self._registry[name]

    def __contains__(self, name: str) -> bool:
        self._initialize()
        return name in self._registry

    def values(self) -> Iterable[type[P]]:
        self._initialize()
        return self._registry.values()

    def list_plugins(self) -> list[str]:
        self._initialize()
        return list(self._registry.keys())

    def _initialize(self):
        if not self._initialized:
            self._load_plugins()


mining_registry = Registry(MiningAlgorithm, "ariadne.mining_algorithms")
conformance_registry = Registry(ConformanceChecker, "ariadne.conformance_checkers")
