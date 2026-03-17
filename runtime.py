import subprocess
import sys


class Runtime:
    """Base class for running commands in a desktop environment."""

    def exec(self, cmd: str, decode: bool = True):
        """Run a shell command in the desktop environment."""
        raise NotImplementedError

    def start(self):
        """Start the desktop environment."""
        raise NotImplementedError

    def stop(self):
        """Stop the desktop environment."""
        raise NotImplementedError