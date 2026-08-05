"""CRC algorithm selection factory."""

from __future__ import annotations

from config import CRC_ALGORITHM
from services.crc.crc_algorithms import (
    CRC16Algorithm,
    CRC32Algorithm,
    CRC32CAlgorithm,
    CRC64Algorithm,
    CRCAlgorithm,
)
from services.crc.crc_exceptions import CRCUnsupportedAlgorithmError


class CRCFactory:
    """Create CRC algorithm instances by name."""

    _registry: dict[str, type[CRCAlgorithm]] = {
        "crc16": CRC16Algorithm,
        "crc32": CRC32Algorithm,
        "crc32c": CRC32CAlgorithm,
        "crc64": CRC64Algorithm,
    }

    @classmethod
    def get_algorithm(cls, algorithm_name: str | None = None) -> CRCAlgorithm:
        name = (algorithm_name or CRC_ALGORITHM).strip().lower()
        if name in cls._registry:
            return cls._registry[name]()

        normalized = name.replace('-', '').replace('_', '')
        for registered_name, algorithm_type in cls._registry.items():
            if registered_name.replace('-', '').replace('_', '') == normalized:
                return algorithm_type()

        raise CRCUnsupportedAlgorithmError(
            f"Unsupported CRC algorithm '{algorithm_name or CRC_ALGORITHM}'. "
            f"Supported algorithms: {', '.join(sorted(cls._registry))}."
        )

    @classmethod
    def available_algorithms(cls) -> tuple[str, ...]:
        return tuple(sorted(cls._registry))
