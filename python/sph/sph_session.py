""" Provide a session to the school portal SPH """

import json
import logging
import math
import random
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup
from requests import HTTPError, Response

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

            self.__get_ikey()

            self.__get_public_key()
            # self.__print_session('after getting the public key')

            self.__post_rsa_handshake()
            # self.__print_session('after rsa handshake')

            self.__ajax_login()
            # self.__print_session('after ajax login')

            self.__ajax_login_user()
            # self.__print_session('after ajax logging in user')

            self.logged_in = True

    def logout(self) -> None:
        """ Logout from the SPH portal if logged in """
        if self.logged_in:
            self.get('index.php?logout=1')
            self.logged_in = False

    def get(self, relative_url: str) -> str:
        """ Return the response text of the given relative URL """
        try:
            response = self.session.get(self.__get_url(relative_url),
                                        timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except HTTPError as exception:
            raise SphSessionException(
                f"Failed to retrieve from URL: {relative_url}") from exception

    def __get_ikey(self):
        html = self.get(f"index.php?i={self.school_id}")
        soup = BeautifulSoup(html, 'html.parser')
        for i in soup.find_all('input'):
            name = i.get('name')
            if name is not None and name == 'ikey':
                self.ikey = i.get('value')
                logging.debug("ikey=%s", self.ikey)
                return
        raise SphSessionException("Unable to find ikey")

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
        header.update({'content-type':
                       'application/x-www-form-urlencoded; charset=UTF-8'})
        header.update({'origin': self.base_url})
        header.update({'referer': self.__get_url('index.php?i={id}'
                                                 .format(id=self.school_id))})

        try:
            response = self.session.post(url=self.__get_url(f"ajax.php?f=rsaHandshake&s={s}"),
                                         headers=header, data=payload, timeout=self.timeout)
            response.raise_for_status()
        except HTTPError as exception:
            raise SphSessionException("Failed to post to URL") from exception

        rsp = json.loads(response.content)
        decrypted_challenge = self.aes.decrypt(rsp['challenge'],
                                               self.session_key)

        if self.session_key != decrypted_challenge:
            raise SphSessionException(
                "Decrypted challenge does not match the session key!")

        logging.debug("Decrypted challenge matches session key!")

    def __ajax_login(self):
        sid_cookie = self.__get_cookie_value('sid')
        if sid_cookie is None:
            return
        try:
            response = self.session.post(url=self.__get_url('ajax_login.php'),
                                         data=f'name={sid_cookie}', timeout=self.timeout)
            response.raise_for_status()
        except HTTPError as exception:
            raise SphSessionException("Failed to post to URL") from exception

    def __ajax_login_user(self):
        # example form data:
        # "f=alllogin&art=all&sid=&ikey=<ikey.from.index.php>&user=<User.Name>&passw=<User.Pass>"
        form_data = f"f=alllogin&art=all&sid=&ikey={self.ikey}&user={self.user}&passw={self.password}"
        enc_form_data = self.aes.encrypt(form_data.encode("utf-8"),
                                         self.session_key)
        data = 'crypt=' + urllib.parse.quote_plus(enc_form_data)

        header = self.session.headers.copy()
        header.update({'content-type':
                       'application/x-www-form-urlencoded; charset=UTF-8'})
        header.update({'origin': self.base_url})
        header.update({'referer': self.__get_url("index.php")})

        try:
            response = self.session.post(self.__get_url('ajax.php'),
                                         headers=header, data=data, timeout=self.timeout)
            response.raise_for_status()
        except HTTPError as exception:
            raise SphSessionException("Failed to post to URL") from exception

        self.__evaluate_login_response(response)

    def __evaluate_login_response(self, response: Response):
        if len(response.content) == 0:
            raise SphSessionException(f"Failed to login: {self.user}")

        if ('text/plain' in response.headers['content-type'] and response.text.startswith("{")) \
                or ('application/json' in response.headers['content-type']):
            try:
                rsp = json.loads(response.text)
                rsp['name'] = '<Set>'
                logging.debug("Received login response: %s\n%s",
                              response.status_code, rsp)
                msg = "logged in!"
            except json.JSONDecodeError as exception:
                logging.debug("Received login response: %s\n%s",
                              response.status_code, response.text)
                msg = str(exception)
        else:
            logging.debug("Received login response: %s\n%s",
                          response.status_code, response.text)
            msg = response.text

        logging.debug("Login result: %s", msg)

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
