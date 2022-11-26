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
    conn.getresponse()


class PushOver:

    def __init__(self, push_config: dict[str, Any]) -> None:
        self.enabled = True
        if 'enabled' in push_config:
            self.enabled = push_config['enabled']
        if 'users' not in push_config or 'hash-file' not in push_config:
            raise Exception("Invalid PushOver configuration: %s" % push_config)

        self.push_users = push_config['users']
        self.hashes = Hashes(push_config['hash-file'])
        if not self.enabled:
            logging.info("PushOver Messages are disabled!")

        for push_user in self.push_users:
            if 'user' not in push_user or 'user-key' not in push_user or 'api-token' not in push_user:
                raise Exception("Invalid push user configuration: %s" % push_user)
            else:
                logging.debug("PushOver User %s added" % push_user['user'])

    def send(self, event: dict[str, str], push_message: str) -> None:
        if not self.enabled:
            logging.info("PushOver Messages NOT delivered: %s" % push_message)
            return

        key = hash_event(event)
        value = str(event)

        if not self.hashes.already_known(key):
            self.hashes.add(key, value)
            self.send_pushover(push_message)
            time_str = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.now())
            logging.info("%s New event: %s - %s" % (time_str, key, value))

    def send_pushover(self, message: str) -> None:
        for push_user in self.push_users:
            logging.debug("Sending push message to %s" % push_user['user'])
            send_pushover_to_user(push_user['user-key'], push_user['api-token'], message)
