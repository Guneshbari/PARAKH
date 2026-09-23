"""
PARAKH Synthetic Credit Application Generator - Random State Management
Implements deterministic, independent random substreams derived from a master seed.
Guarantees stage-level isolation and worker-level reproducibility without
relying on uncontrolled global random state.
"""

from enum import Enum
import hashlib
import random
from typing import Dict, List, Optional, Union

from src.data.synthetic.config import MASTER_SEED
from src.data.synthetic.exceptions import ConfigurationError


class Substream(str, Enum):
    """Major generation stages requiring isolated random substreams."""
    APPLICANTS = "applicants"
    COHORTS = "cohorts"
    PROFILES = "profiles"
    HISTORICAL_TELEMETRY = "historical_telemetry"
    APPLICATIONS = "applications"
    MISSINGNESS = "missingness"
    FORWARD_SIMULATION = "forward_simulation"
    VALIDATION = "validation"


class RandomStateManager:
    """
    Manages deterministic, isolated random substreams derived from a master seed.
    Each substream operates its own independent PRNG instance (random.Random).
    If NumPy is available in the environment, it can also provide np.random.Generator.
    """

    def __init__(self, master_seed: int = MASTER_SEED):
        if not isinstance(master_seed, int):
            raise ConfigurationError(f"master_seed must be an integer, got {type(master_seed)}")
        self._master_seed = master_seed
        self._streams: Dict[str, random.Random] = {}
        self._numpy_generators: Dict[str, object] = {}
        self._init_streams()

    @property
    def master_seed(self) -> int:
        return self._master_seed

    def _derive_seed(self, substream_name: str) -> int:
        """
        Deterministically derive an integer seed for a given substream
        using SHA-256 cryptographic hashing of (master_seed, substream_name).
        Returns a 32-bit positive integer (in range [1, 2**31 - 1]).
        """
        payload = f"{self._master_seed}:{substream_name}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        # Extract 8 hex chars -> 32-bit integer, map to [1, 2147483647]
        raw_int = int(digest[:8], 16)
        return (raw_int % 2147483647) + 1

    def _init_streams(self) -> None:
        """Initialize all registered major substreams."""
        for substream in Substream:
            seed = self._derive_seed(substream.value)
            self._streams[substream.value] = random.Random(seed)

    def get_stream(self, substream: Union[str, Substream]) -> random.Random:
        """
        Retrieve the independent random.Random instance for a major stage.
        If a new stream name is passed, it is deterministically derived and cached.
        """
        name = substream.value if isinstance(substream, Substream) else str(substream)
        if name not in self._streams:
            seed = self._derive_seed(name)
            self._streams[name] = random.Random(seed)
        return self._streams[name]

    def get_substream_seed(self, substream: Union[str, Substream]) -> int:
        """Get the deterministic derived integer seed for a substream."""
        name = substream.value if isinstance(substream, Substream) else str(substream)
        return self._derive_seed(name)

    def spawn_applicant_seeds(self, n_applicants: int) -> List[int]:
        """
        Derive n deterministic, distinct seeds for per-applicant generation.
        Enables worker-level determinism regardless of batching or sorting order.
        """
        seeds: List[int] = []
        for i in range(n_applicants):
            payload = f"{self._master_seed}:applicant:{i}".encode("utf-8")
            digest = hashlib.sha256(payload).hexdigest()
            raw_int = int(digest[:8], 16)
            seed = (raw_int % 2147483647) + 1
            seeds.append(seed)
        return seeds

    def get_numpy_generator(self, substream: Union[str, Substream]):
        """
        Retrieve an independent numpy.random.Generator for a substream.
        Returns None if NumPy is not installed.
        """
        try:
            import numpy as np
        except ImportError:
            return None

        name = substream.value if isinstance(substream, Substream) else str(substream)
        if name not in self._numpy_generators:
            seed = self._derive_seed(name)
            self._numpy_generators[name] = np.random.default_rng(seed)
        return self._numpy_generators[name]

    def reset(self) -> None:
        """Reset all substreams back to their initial deterministic states."""
        self._streams.clear()
        self._numpy_generators.clear()
        self._init_streams()
