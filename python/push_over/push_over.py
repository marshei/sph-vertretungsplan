import hashlib
import http.client
import json
import logging
import urllib.parse
from datetime import datetime
from typing import Any

from push_over.hashes import Hashes


def hash_event(event: dict[str, str]):
    return hashlib.md5(json.dumps(event, sort_keys=True, ensure_ascii=True).encode('utf-8')).hexdigest()


def send_pushover_to_user(user_key: str, api_token: str, message: str) -> None:
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

    def __init__(self, push_config: dict[str, Any], config_dir: str) -> None:
        self.enabled = False
        self.push_users = {}

        if push_config is not None:
            if 'enabled' in push_config:
                self.enabled = push_config['enabled']
            if 'users' not in push_config or 'hash-file' not in push_config:
                raise Exception("Invalid PushOver configuration: {}"
                                .format(push_config))

            self.push_users = push_config['users']
            self.hashes = Hashes(push_config['hash-file'], config_dir)

        if not self.enabled:
            logging.info("PushOver Messages are disabled!")

        for push_user in self.push_users:
            if 'user' not in push_user or 'user-key' not in push_user or 'api-token' not in push_user:
                raise Exception("Invalid push user configuration: {user_cfg}"
                                .format(user_cfg=push_user))
            else:
                logging.info("PushOver User {user} added, send-errors = {errs}"
                             .format(user=push_user['user'], errs=push_user['send-errors']))

    def send_error(self, error_msg: str) -> None:
        error = {
            'Datum': datetime.now().date().strftime('%d.%m.%Y'),
            'Fehlermeldung': error_msg
        }
        self.send(error, "ERROR: {err}".format(err=str(error)), is_error=True)

    def send(self, event: dict[str, str], push_message: str, is_error: bool = False) -> None:
        if not self.enabled:
            logging.info("PushOver Messages NOT delivered: {msg}"
                         .format(msg=push_message))
            return

        try:
            key = hash_event(event)
            value = str(event)

            if not self.hashes.already_known(key):
                self.hashes.add(key, value)
                self.__send_pushover(push_message, is_error)
                time_str = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.now())
                logging.info("{time} New event: {k} - {v}"
                             .format(time=time_str, k=key, v=value))
        except:
            logging.error("Failed sending event: {e}, {is_err}"
                          .format(e=str(event), is_err=is_error))

    def __send_pushover(self, message: str, is_error: bool) -> None:
        for push_user in self.push_users:
            if not is_error:
                logging.debug("Sending push message to {user}"
                              .format(user=push_user['user']))
                send_pushover_to_user(push_user['user-key'], push_user['api-token'],
                                      message)
            elif is_error == push_user['send-errors']:
                logging.debug("Sending push message to {user}"
                              .format(user=push_user['user']))
                send_pushover_to_user(push_user['user-key'], push_user['api-token'],
                                      message)
