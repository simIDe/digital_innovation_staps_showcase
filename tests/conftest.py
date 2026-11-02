import shutil
from pathlib import Path

import pytest

SAMPLES = Path(__file__).parents[1] / "data" / "samples"


@pytest.fixture
def batch_folder(tmp_path):
    """A writable copy of a sample batch, to break it on purpose."""

    def copy(name: str = "batch1") -> Path:
        return Path(shutil.copytree(SAMPLES / name, tmp_path / name))

    return copy
