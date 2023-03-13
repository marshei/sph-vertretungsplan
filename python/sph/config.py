import copy
import logging
import os
from typing import Any

import yaml


class Config:
    NOT_PRESENT = '<Not Set>'
    PRESENT = '<Set>'

    def __init__(self, filename: str, read_from_file) -> None:
        self.filename = filename
        self.config = self.__get_configuration_from_file()
        if read_from_file:
            self.config['read-from-file'] = True
        else:
            self.config['read-from-file'] = False
        self.config['config-dir'] = os.path.dirname(os.path.abspath(self.filename))
        logging.info("Config: %s" % self)

    def has_key(self, key: str) -> bool:
        return key in self.config

    def get(self, key: str) -> Any:
        return self.config[key]

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
        with open(self.filename, "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                raise Exception(
                    "Failed to parse configuration file: %s" % str(exc))
