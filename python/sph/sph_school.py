import json
import logging

import requests


class SphSchool:

    def __init__(self, city, name, school_id) -> None:
        self.school_city = city
        self.school_name = name
        self.school_id = school_id
        self.school_list_url = 'https://startcache.schulportal.hessen.de/exporteur.php?a=schoollist'

        if self.school_id is None:
            if self.school_city is None or self.school_name is None:
                raise Exception("School city and name have to be provided")
            self.school_id = self.search_institution_id()
            logging.debug("Using identified school id: {}"
                          .format(self.school_id))
        else:
            if self.school_city is not None or self.school_name is not None:
                raise Exception("School city and name must not be provided")
            logging.debug("Using provided school id: {}"
                          .format(self.school_id))

    def get_id(self):
        return self.school_id

    def search_institution_id(self) -> str:
        school_list = self.get_school_list()
        for school_area in school_list:
            for school in school_area[u'Schulen']:
                if self.school_name in school[u'Name'] and self.school_city in school[u'Ort']:
                    return school[u'Id']
        raise Exception("Could not find Id for school {name} in {city}"
                        .format(name=self.school_name, city=self.school_city))

    def get_school_list(self):
        session = requests.Session()

        response = session.get(self.school_list_url)
        response.raise_for_status()

        return json.loads(response.text)
