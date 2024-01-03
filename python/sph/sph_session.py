""" Provide a session to the school portal SPH """

import json
import logging
import math
import random
import time
import urllib.parse

import requests
from requests import HTTPError
from sph.crypto import AesCrypto, RsaCrypto


def generate_uuid():
    """ Generate a random UUID """
    d = time.time_ns()
    uuid = ""

    for c in 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx-xxxxxx3xx':
        r = (d + int(random.random() * 16)) % 16 | 0
        d = math.floor(d / 16)
        if c == 'x':
            uuid = uuid + "{0:x}".format(r)
        elif c == 'y':
            uuid = uuid + "{0:x}".format((r & 0x3 | 0x8))
        else:
            uuid = uuid + c

    return uuid


class SphSessionException(Exception):
    """ Indicating an exception related to the SPH session """


class SphSession:
    """ Provide a session for the SPH """

    def __init__(self, school_id: str, user: str, password: str) -> None:
        self.user = user
        self.password = password
        self.ikey = None
        self.timeout = 30
        self.base_domain = 'start.schulportal.hessen.de'
        self.base_url = f'https://{self.base_domain}'
        self.login_domain = 'login.schulportal.hessen.de'
        self.login_base_url = f'https://{self.login_domain}'
        self.school_id = school_id
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 ' \
                          'Safari/537.36 '
        self.logged_in = False

        self.session = None
        self.session_key = None

        self.aes = AesCrypto()
        self.rsa = None

    def login(self):
        """ Perform the login procedure if not yet logged in """
        if not self.logged_in:
            self.session = requests.Session()
            self.session.headers.update({'upgrade-insecure-requests': '1'})
            self.session.headers.update({'User-Agent': self.user_agent})

            self.session_key = self.aes.encrypt(generate_uuid().encode("utf-8"),
                                                generate_uuid().encode("utf-8"))
            logging.debug("Session Key: %s", self.session_key)

            self.session.cookies.set('i', self.school_id,
                                     domain=self.base_domain, secure=True)
            self.session.cookies.set('complianceCookie', 'on',
                                     domain=self.base_domain)

            self.__initial_login()

            self.__get_public_key()
            # self.__print_session('after getting the public key')

            self.__post_rsa_handshake()
            # self.__print_session('after rsa handshake')

            self.__ajax_login()
            # self.__print_session('after ajax login')

            self.logged_in = True

    def logout(self) -> None:
        """ Logout from the SPH portal if logged in """
        if self.logged_in:
            self.get('index.php?logout=1')
            self.logged_in = False
            logging.debug("Logged out")

    def get(self, relative_url: str) -> str:
        """ Return the response text of the given relative URL """
        try:
            response = self.session.get(self.__get_url(relative_url), timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except HTTPError as exception:
            raise SphSessionException(
                f"Failed to retrieve from URL: {relative_url}") from exception

    def __initial_login(self):
        payload = 'user2=' + self.user + '&user=' + self.school_id + '.' + self.user + \
                  '&password=' + self.password
        url = f"{self.login_base_url}/?i={self.school_id}"

        header = self.session.headers.copy()
        header.update({'content-type': 'application/x-www-form-urlencoded'})
        header.update({'origin': self.login_base_url})
        header.update({'referer': url})

        try:
            response = self.session.post(url=url, headers=header, data=payload, timeout=self.timeout)
            response.raise_for_status()
        except HTTPError as exception:
            raise SphSessionException(
                f"Failed to post to URL: {url}; HTTP code: {exception.response.status_code}") from exception

    def __get_public_key(self):
        response = self.get('ajax.php?f=rsaPublicKey')
        rsp = json.loads(response)
        self.rsa = RsaCrypto(rsp['publickey'])

    def __post_rsa_handshake(self):
        # Encrypt the session key with the public RSA key
        enc_session_key = self.rsa.encrypt(self.session_key)
        payload = 'key=' + urllib.parse.quote_plus(enc_session_key)

        s = random.randint(0, 1999)

        header = self.session.headers.copy()
        header.update({'content-type': 'application/x-www-form-urlencoded'})
        header.update({'origin': self.base_url})
        header.update({'referer': self.__get_url(f'index.php?i={self.school_id}')})

        url = self.__get_url(f"ajax.php?f=rsaHandshake&s={s}")
        try:
            response = self.session.post(url=url, headers=header, data=payload, timeout=self.timeout)
            response.raise_for_status()
        except HTTPError as exception:
            raise SphSessionException(
                f"Failed to post to URL: {url}; HTTP code: {exception.response.status_code}") from exception

        rsp = json.loads(response.content)
        decrypted_challenge = self.aes.decrypt(rsp['challenge'], self.session_key)

        if self.session_key != decrypted_challenge:
            raise SphSessionException("Decrypted challenge does not match the session key!")

        logging.debug("Decrypted challenge matches session key!")

    def __ajax_login(self):
        sid_cookie = self.__get_cookie_value('sid')
        if sid_cookie is None:
            return
        url = self.__get_url('ajax_login.php')
        try:
            response = self.session.post(url=url, data=f'name={sid_cookie}', timeout=self.timeout)
            response.raise_for_status()
        except HTTPError as exception:
            raise SphSessionException(
                f"Failed to post to URL: {url}; HTTP code: {exception.response.status_code}") from exception

    def __get_cookie_value(self, name: str):
        for c in self.session.cookies:
            if c.name == name:
                return c.value
        return None

    def __get_url(self, relative_url: str) -> str:
        return f"{self.base_url}/{relative_url}"

    # def __print_session(self, explanation: str):
    #    logging.debug("-" * 80)
    #    logging.debug("--- Cookies: %s", explanation)
    #    for cookie in self.session.cookies:
    #        logging.debug(cookie)
    #    logging.debug("-" * 80)
