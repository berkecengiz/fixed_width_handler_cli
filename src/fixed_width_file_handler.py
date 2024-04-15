"""Module for IO operations on fixed-width files. """


class FixedWidthFileManager:
    """
    Handles reading and writing fixed-width files.

    Args:
        filename (str): The filename of the fixed-width file.
    """

    def __init__(self, filename):
        self.filename = filename

    def read_lines(self):
        """Read lines from the file and return them as a list."""
        with open(self.filename, "r", encoding="utf-8", newline="") as file:
            return file.read().splitlines()

    def write_lines(self, lines):
        """Write lines to the file."""
        with open(self.filename, "w", encoding="utf-8", newline="") as file:
            file.write("\n".join(lines))
