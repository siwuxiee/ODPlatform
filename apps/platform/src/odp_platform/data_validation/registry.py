import pkgutil
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


_CHECK_MODULE_PREFIX = __name__.rsplit(".", 1)[0] + ".checks"


class CheckSeverity:
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    PASS = "PASS"

    _RANK = {ERROR: 3, WARNING: 2, INFO: 1, PASS: 0}

    @classmethod
    def rank(cls, level: str) -> int:
        return cls._RANK.get(level, -1)


@dataclass
class CheckResult:
    name: str
    severity: str
    summary: str
    details: Dict[str, Any]

    @property
    def passed(self) -> bool:
        return self.severity in (CheckSeverity.PASS, CheckSeverity.INFO)


@dataclass
class CheckContext:
    yaml_path: Path
    snapshot: Optional[Any] = None


@dataclass
class CheckEntry:
    name: str
    func: Callable[["CheckContext"], CheckResult]


_REGISTRY: Dict[str, CheckEntry] = {}
_INITIALIZED: bool = False


def check(name: str):
    def decorator(func):
        if name in _REGISTRY:
            raise ValueError(f"Check '{name}' is already registered")
        _REGISTRY[name] = CheckEntry(name=name, func=func)
        return func
    return decorator


def _discover_checks() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    try:
        check_pkg = importlib.import_module(_CHECK_MODULE_PREFIX)
    except ModuleNotFoundError:
        _INITIALIZED = True
        return
    for _, module_name, _ in pkgutil.iter_modules(check_pkg.__path__, check_pkg.__name__ + "."):
        if module_name.split(".")[-1].startswith("_"):
            continue
        importlib.import_module(module_name)
    _INITIALIZED = True


def get_all_checks() -> List[CheckEntry]:
    _discover_checks()
    return list(_REGISTRY.values())
