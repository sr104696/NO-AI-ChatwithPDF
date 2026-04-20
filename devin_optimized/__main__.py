"""Allow running as ``python -m devin_optimized``."""

from .cli import main
import sys

sys.exit(main())
