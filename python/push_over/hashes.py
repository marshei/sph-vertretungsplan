""" Hash File Support """

import logging
import os


class Hashes:
    """Hash File Support"""

    def __init__(self, filename: str, config_dir: str) -> None:
        if filename.startswith("/"):
            self.filename = filename
        else:
            self.filename = config_dir + "/" + filename
        with open(file=self.filename, mode="a", encoding="utf-8"):
            pass
        logging.debug("Using hash file %s", self.filename)
        self.separator = " - "
        self.hashes = {}
        with open(self.filename, "r", encoding="utf-8") as file:
            for line in file.readlines():
                parts = line.split(self.separator)
                self.hashes.update({parts[0]: parts[1]})

    def already_known(self, key):
        """Hash already known"""
        return key in self.hashes

    def add(self, key, value):
        """Add hash"""
        with open(self.filename, "a", encoding="utf-8") as file:
            file.write(key + self.separator + value + "\n")
            self.hashes.update({key: value})
