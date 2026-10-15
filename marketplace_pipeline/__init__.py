"""Assignment pipeline stages.

The public interface is ``run_pipeline``. Individual stage functions are kept in
their matching modules so they can also be inspected or tested in isolation.
"""

from .runner import run_pipeline

__all__ = ["run_pipeline"]
