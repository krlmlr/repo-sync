"""The test suite.

Importable as a package so that `scripts/` is on the path before any test module loads:
the collector and the renderer are scripts rather than an installed distribution, which is what the
two entry points are, and pretending otherwise in the tests would test a different arrangement.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
