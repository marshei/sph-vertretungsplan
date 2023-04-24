import json
import logging
import math
import random
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup
from requests import Response

from sph.crypto import AesCrypto, RsaCrypto


def generate_uuid():
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


class SphSession:

    def __init__(self, school_id: str, user: str, password: str) -> None:
        self.user = user
        self.password = password
        self.ikey = None
        self.timeout = 30
        self.base_domain = 'start.schulportal.hessen.de'
        self.base_url = 'https://{}'.format(self.base_domain)
        self.school_id = school_id
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 ' \
                          'Safari/537.36 '
        self.logged_in = False

        self.session = requests.Session()
        self.session.headers.update({'upgrade-insecure-requests': '1'})
        self.session.headers.update({'User-Agent': self.user_agent})

        self.aes = AesCrypto()
        self.session_key = self.aes.encrypt(
            generate_uuid().encode("utf-8"), generate_uuid().encode("utf-8"))
        logging.debug("Session Key: {key}".format(key=self.session_key))
        self.rsa = None

    def login(self):
        self.logged_in = False
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
        if self.logged_in:
            self.get('index.php?logout=1')
            self.logged_in = False

    def get(self, relative_url: str) -> str:
        response = self.session.get(self.__get_url(relative_url),
                                    timeout=self.timeout)
        response.raise_for_status()

        return response.text

    def __get_ikey(self):
        html = self.get('index.php?i={id}'.format(id=self.school_id))
        soup = BeautifulSoup(html, 'html.parser')
        for i in soup.find_all('input'):
            name = i.get('name')
            if name is not None and name == 'ikey':
                self.ikey = i.get('value')
                logging.debug("ikey={}".format(self.ikey))
                return
        raise Exception("Unable to find ikey")

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

        response = self.session.post(url=self.__get_url('ajax.php?f=rsaHandshake&s={s}'
                                                        .format(s=s)),
                                     headers=header, data=payload, timeout=self.timeout)
        response.raise_for_status()

        rsp = json.loads(response.content)
        decrypted_challenge = self.aes.decrypt(rsp['challenge'],
                                               self.session_key)

        if self.session_key != decrypted_challenge:
            raise Exception(
                "Decrypted challenge does not match the session key!")

        logging.debug("Decrypted challenge matches session key!")

    def __ajax_login(self):
        sid_cookie = self.__get_cookie_value('sid')
        if sid_cookie is None:
            return
        response = self.session.post(url=self.__get_url('ajax_login.php'),
                                     data='name={}'.format(sid_cookie), timeout=self.timeout)
        response.raise_for_status()

    def __ajax_login_user(self):
        # example form data:
        # "f=alllogin&art=all&sid=&ikey=<ikey.from.index.php>&user=<User.Name>&passw=<User.Pass>"
        form_data = "f=alllogin&art=all&sid=&ikey={ikey}&user={user}&passw={pw}".format(
            ikey=self.ikey, user=self.user, pw=self.password)
        enc_form_data = self.aes.encrypt(form_data.encode("utf-8"),
                                         self.session_key)
        data = 'crypt=' + urllib.parse.quote_plus(enc_form_data)

        header = self.session.headers.copy()
        header.update({'content-type':
                       'application/x-www-form-urlencoded; charset=UTF-8'})
        header.update({'origin': self.base_url})
        header.update({'referer':
                       '{base_url}/index.php'.format(base_url=self.base_url)})

        response = self.session.post('{base_url}/ajax.php'.format(base_url=self.base_url),
                                     headers=header, data=data, timeout=self.timeout)
        response.raise_for_status()

        self.__evaluate_login_response(response)

    def __evaluate_login_response(self, response: Response):
        if len(response.content) == 0:
            raise Exception("Failed to login: {}".format(self.user))

        if ('text/plain' in response.headers['content-type'] and response.text.startswith("{")) \
                or ('application/json' in response.headers['content-type']):
            try:
                rsp = json.loads(response.text)
                rsp['name'] = '<Set>'
                logging.debug("Received login response: {code}\n{r}"
                              .format(code=response.status_code, r=rsp))
                msg = "logged in!"
            except Exception as e:
                logging.debug("Received login response: {code}\n{r}"
                              .format(code=response.status_code, r=response.text))
                msg = str(e)
        else:
            logging.debug("Received login response: {code}\n{r}"
                          .format(code=response.status_code, r=response.text))
            msg = response.text

        logging.debug("Login result: {}".format(msg))

    def __get_cookie_value(self, name: str):
        for c in self.session.cookies:
            if c.name == name:
                return c.value
        return None

    def __get_url(self, relative_url: str) -> str:
        return "{base_url}/{url}".format(base_url=self.base_url,
                                         url=relative_url)

    def __print_session(self, explanation: str):
        logging.debug('-' * 80)
        logging.debug('--- Cookies: {}'.format(explanation))
        for cookie in self.session.cookies:
            logging.debug(cookie)
        logging.debug('-' * 80)
