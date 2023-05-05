""" Support for sending pushover messages """

import hashlib
import http.client
import json
import logging
import urllib.parse
from datetime import datetime
from typing import Any

from push_over.hashes import Hashes
from sph.sph_exception import SphException


def hash_event(event: dict[str, str]) -> str:
    """ Hash the event """
    return hashlib.md5(json.dumps(event, sort_keys=True, ensure_ascii=True)
                       .encode('utf-8')).hexdigest()


def send_pushover_to_user(user_key: str, api_token: str, message: str) -> None:
    """ Send pushover message to user """
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
                 urllib.parse.urlencode({
                     "token": api_token,
                     "user": user_key,
                     "message": message}), {"Content-type": "application/x-www-form-urlencoded"})
    response = conn.getresponse()
    if response.getcode() != 200:
        logging.error("Failed to send pushover message")


class PushOver:
    """ Pushover Support """

    def __init__(self, push_config: dict[str, Any], config_dir: str) -> None:
        self.enabled = False
        self.push_users = {}

        if push_config is not None:
            if 'enabled' in push_config:
                self.enabled = push_config['enabled']
            if 'users' not in push_config or 'hash-file' not in push_config:
                raise SphException(
                    f"Invalid PushOver configuration: {str(push_config)}")

            self.push_users = push_config['users']
            self.hashes = Hashes(push_config['hash-file'], config_dir)

        if not self.enabled:
            logging.info("PushOver Messages are disabled!")

        for push_user in self.push_users:
            if 'user' not in push_user or 'user-key' not in push_user or 'api-token' not in push_user:
                raise SphException(
                    f"Invalid push user configuration: {str(push_user)}")
            else:
                logging.info("PushOver User %s added, send-errors = %s",
                             push_user['user'], push_user['send-errors'])

    def send_error(self, error_msg: str) -> None:
        """ Send error message """
        error = {
            'Datum': datetime.now().date().strftime('%d.%m.%Y'),
            'Fehlermeldung': error_msg
        }
        self.send(error, f"ERROR: {str(error)}", is_error=True)

    def send(self, event: dict[str, str], push_message: str, is_error: bool = False) -> None:
        """ Send message """
        if not self.enabled:
            logging.info("PushOver Messages NOT delivered: %s", push_message)
            return

        try:
            key = hash_event(event)
            value = str(event)

            if not self.hashes.already_known(key):
                self.hashes.add(key, value)
                self.__send_pushover(push_message, is_error)
                time_str = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.now())
                logging.info("%s New event: %s - %s", time_str, key, value)
        except Exception:
            logging.error("Failed sending event: %s (is_error=%r)",
                          str(event), is_error)

    def __send_pushover(self, message: str, is_error: bool) -> None:
        for push_user in self.push_users:
            if not is_error:
                logging.debug("Sending push message to %s", push_user['user'])
                send_pushover_to_user(push_user['user-key'],
                                      push_user['api-token'],
                                      message)
            elif is_error == push_user['send-errors']:
                logging.debug("Sending push error message to %s",
                              push_user['user'])
                send_pushover_to_user(push_user['user-key'],
                                      push_user['api-token'],
                                      message)
