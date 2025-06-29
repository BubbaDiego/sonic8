
"""Learning database package initialisation."""

# Re-export ``verify_all_tables_exist`` so callers can simply::
#
#     from learning_database import verify_all_tables_exist
#
# This maintains compatibility with callers expecting the function at the
# package level.
from .scripts.verify_all_tables_exist import verify, verify_all_tables_exist

__all__ = ["verify_all_tables_exist", "verify"]

