""" SPH configuration """

import copy
import logging
import os
from typing import Any

import yaml

from sph.sph_exception import SphException


class SphConfig:
    """ SPH configuration """
    NOT_PRESENT = '<Not Set>'
    PRESENT = '<Set>'

    def __init__(self, filename: str, read_from_file) -> None:
        self.filename = filename
        self.config = self.__get_configuration_from_file()
        if read_from_file:
            self.config['read-from-file'] = True
        else:
            self.config['read-from-file'] = False
        logging.info("Config: %s", str(self))

    def has_key(self, key: str) -> bool:
        """ Test for presence of the given key """
        return key in self.config

    def get(self, key: str) -> Any:
        """ Get the configuration for key """
        return self.config[key]

    def get_storage_directory(self):
        if self.has_key("storage-directory"):
            return self.get("storage-directory").rstrip("/")
        else:
            return os.path.dirname(os.path.abspath(self.filename))

    def get_storage_filename(self, filename: str) -> str:
        storage_dir = self.get_storage_directory()
        return storage_dir + "/" + filename

    def __getitem__(self, key: str) -> Any:
        if key in self.config:
            return self.config[key]
        return None

    def __str__(self) -> str:
        if self.config is None:
            return self.NOT_PRESENT

        c: dict[str, Any] = copy.deepcopy(self.config)
        c['user'] = self.__anonymize(c['user'])
        c['password'] = self.__anonymize(c['password'])
        if 'push-over' in c and 'users' in c['push-over']:
            for u in c['push-over']['users']:
                u['user-key'] = u['user-key'][:4] + '...'
                u['api-token'] = u['api-token'][:4] + '...'

        return str(c)

    def __anonymize(self, value: Any) -> str:
        if value is None:
            return self.NOT_PRESENT
        else:
            return self.PRESENT

    def __get_configuration_from_file(self) -> dict[str, Any]:
        with open(self.filename, "r", encoding="utf-8") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                raise SphException(
                    f"Failed to parse configuration file: {str(exc)}") from exc
