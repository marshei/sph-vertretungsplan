""" Define the school for SPH """

import json
import logging
from typing import Any

import requests

from sph.sph_exception import SphException


class SphSchool:
    """ SPH School """

    def __init__(self, city: str, name: str, school_id: Any) -> None:
        self.school_city = city
        self.school_name = name
        self.school_id = school_id
        self.school_list_url = 'https://startcache.schulportal.hessen.de/exporteur.php?a=schoollist'

        if self.school_id is None:
            if self.school_city is None or self.school_name is None:
                raise SphException("School city and name have to be provided")
            self.school_id = self.__search_institution_id()
            logging.debug("Using identified school id: %s", self.school_id)
        else:
            if self.school_city is not None or self.school_name is not None:
                raise SphException("School city and name must not be provided")
            logging.debug("Using provided school id: %s", self.school_id)

    def get_id(self):
        """ Get id of school """
        return self.school_id

    def __search_institution_id(self) -> str:
        school_list = self.__get_school_list()
        for school_area in school_list:
            for school in school_area[u'Schulen']:
                if self.school_name in school[u'Name'] and self.school_city in school[u'Ort']:
                    return school[u'Id']
        raise SphException(
            f"Could not find Id for school {self.school_name} in {self.school_city}")

    def __get_school_list(self):
        session = requests.Session()

        response = session.get(self.school_list_url)
        response.raise_for_status()

        return json.loads(response.text)
