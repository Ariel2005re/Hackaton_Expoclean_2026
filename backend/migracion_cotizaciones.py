"""Compatibility entry point for the unified migration."""

from backend.migrate import migrate


if __name__ == "__main__":
    migrate()
