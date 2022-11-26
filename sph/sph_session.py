import json
import logging
import math
import random
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

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
        self.base_domain = 'start.schulportal.hessen.de'
        self.base_url = 'https://%s' % self.base_domain
        self.school_id = school_id
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 ' \
                          'Safari/537.36 '

        self.session = requests.Session()
        self.session.headers.update({'upgrade-insecure-requests': '1'})
        self.session.headers.update({'User-Agent': self.user_agent})

        self.aes = AesCrypto()
        self.session_key = self.aes.encrypt(generate_uuid().encode("utf-8"), generate_uuid().encode("utf-8"))
        logging.debug("Session Key: %s" % self.session_key)
        self.rsa = None

    def print_session(self, explanation: str):
        logging.debug('-' * 80)
        logging.debug('--- Cookies: %s' % explanation)
        for cookie in self.session.cookies:
            logging.debug(cookie)
        logging.debug('-' * 80)

    def login(self):
        self.session.cookies.set('i', self.school_id, domain=self.base_domain, secure=True)
        self.session.cookies.set('complianceCookie', 'on', domain=self.base_domain)

        self.get_ikey()

        self.get_public_key()
        self.print_session('after getting the public key')

        self.post_rsa_handshake()
        self.print_session('after rsa handshake')

        self.ajax_login()
        self.print_session('after ajax login')

        self.ajax_login_user()
        self.print_session('after ajax logging in user')

    def get_ikey(self):
        html = self.get('%s/index.php?i=%s' % (self.base_url, self.school_id))
        soup = BeautifulSoup(html, 'html.parser')
        for i in soup.find_all('input'):
            name = i.get('name')
            if name is not None and name == 'ikey':
                self.ikey = i.get('value')
                logging.debug("ikey=%s" % self.ikey)
                return
        raise Exception("Unable to find ikey")

    def get_public_key(self):
        response = self.session.get('%s/ajax.php?f=rsaPublicKey' % self.base_url)
        response.raise_for_status()
        rsp = json.loads(response.content)
        self.rsa = RsaCrypto(rsp['publickey'])

    def post_rsa_handshake(self):
        # Encrypt the session key with the public RSA key
        enc_session_key = self.rsa.encrypt(self.session_key)
        data = 'key=' + urllib.parse.quote_plus(enc_session_key)

        s = random.randint(0, 1999)

        header = self.session.headers.copy()
        header.update({'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})
        header.update({'origin': self.base_url})
        header.update({'referer': '%s/index.php?i=%s' % (self.base_url, self.school_id)})

        response = self.session.post('%s/ajax.php?f=rsaHandshake&s=%d' % (self.base_url, s), headers=header, data=data)
        response.raise_for_status()

        rsp = json.loads(response.content)
        decrypted_challenge = self.aes.decrypt(rsp['challenge'], self.session_key)
        logging.debug("Decrypted challenge: %s" % decrypted_challenge)

        if self.session_key != decrypted_challenge:
            raise Exception("Decrypted challenge does not match the session key!")

        logging.debug("Decrypted challenge matches session key!")

    def ajax_login(self):
        sid_cookie = self.get_cookie_value('sid')
        if sid_cookie is None:
            return
        response = self.session.post('%s/ajax_login.php' % self.base_url, 'name=%s' % sid_cookie)
        response.raise_for_status()

    def ajax_login_user(self):
        # example form data:
        # "f=alllogin&art=all&sid=&ikey=<ikey.from.index.php>&user=<User.Name>&passw=<User.Pass>"
        form_data = "f=alllogin&art=all&sid=&ikey=%s&user=%s&passw=%s" % (self.ikey, self.user, self.password)
        enc_form_data = self.aes.encrypt(form_data.encode("utf-8"), self.session_key)
        data = 'crypt=' + urllib.parse.quote_plus(enc_form_data)

        header = self.session.headers.copy()
        header.update({'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})
        header.update({'origin': self.base_url})
        header.update({'referer': '%s/index.php' % self.base_url})

        response = self.session.post('%s/ajax.php' % self.base_url, headers=header, data=data)
        response.raise_for_status()
        if len(response.content) == 0:
            raise Exception("Failed to login")

        try:
            rsp = json.loads(response.text)
            if rsp['name'] is None:
                raise Exception("Missing name in response")
            logging.debug("%s logged in!" % rsp['name'])
        except Exception as e:
            raise Exception("Failed to login: %s" % str(e))

    def get_cookie_value(self, name: str):
        for c in self.session.cookies:
            if c.name == name:
                return c.value
        return None

    def logout(self):
        response = self.session.get('%s/index.php?logout=1' % self.base_url)
        response.raise_for_status()

    def get(self, url: str):
        response = self.session.get(url)
        response.raise_for_status()
        self.print_session('after fetching url: %s' % url)

        return response.text
