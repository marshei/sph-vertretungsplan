#!/usr/bin/env python3

""" Checking SPH for delegations
"""

import argparse
import logging
import signal
import sys
import traceback

from datetime import datetime
from typing import Any
import pytz

from bs4 import BeautifulSoup

from delegation_table import DelegationTable
from execution.execution import Execution
from push_over.push_over import PushOver
from school_holidays.school_holidays import SchoolHolidays
from sph.sph_config import SphConfig
from sph.sph_school import SphSchool
from sph.sph_session import SphSessionException
from sph.sph_session import SphSession


class TimezoneAwareLogFormatter(logging.Formatter):
    """ Override logging.Formatter to use an timezone-aware datetime object """

    def converter(self, timestamp) -> datetime:
        """ Adjust the timezone of the timestamp to Europe/Berlin """
        return datetime.fromtimestamp(timestamp, tz=pytz.UTC) \
                       .astimezone(pytz.timezone('Europe/Berlin'))

    def formatTime(self, record, datefmt=None) -> str:
        converted_time = self.converter(record.created)
        if datefmt:
            return converted_time.strftime(datefmt)

        try:
            return converted_time.isoformat(timespec='milliseconds')
        except TypeError:
            return converted_time.isoformat()


logFormatter = TimezoneAwareLogFormatter(
    fmt="%(asctime)s [%(funcName)-12.12s] [%(levelname)-4.7s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %Z")
rootLogger = logging.getLogger()

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.INFO)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)
rootLogger.setLevel(logging.INFO)


class SphException(Exception):
    """ Indicating an exception related to the SPH checks """


class SphExecutor:
    """ Executing the checks in the SPH """

    def __init__(self, config: SphConfig) -> None:
        self.config = config
        self.school = SphSchool(city=config['school-city'], name=config['school-name'],
                                school_id=config['school-id'])
        self.holiday = SchoolHolidays(config['school-holidays'])
        self.push_service = PushOver(config['push-over'], config['config-dir'])
        self.execution = Execution(config['execution'], self.push_service)

        self.session = SphSession(school_id=self.school.get_id(),
                                  user=config['user'], password=config['password'])

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        logging.info("Exiting SPH executor ...")
        self.__logout()

    def run(self) -> None:
        """ Run the SPH checks scheduled or once """
        self.execution.run_scheduled(self.__try_check_sph)

    def __try_check_sph(self) -> None:
        if self.holiday.is_holiday_today():
            self.__logout()
            return

        logging.info("Checking SPH ...")

        if not self.__check_sph():
            logging.info("Checking SPH ... trying once more")
            self.__check_sph()

        logging.info("Checking SPH ... done")

    def __check_sph(self) -> bool:
        if self.__login():
            try:
                self.__parse_delegation_html(self.config['class'],
                                             self.config['fields'])
                return True
            except SphException as exception:
                traceback.print_exc()
                logging.error("Failed to process html: %s", str(exception))
                self.__logout()

        return False

    def __login(self) -> bool:
        try:
            self.session.login()
            return True
        except SphSessionException as exception:
            logging.error("Failed to login: %s", str(exception))
            return False

    def __logout(self) -> None:
        try:
            self.session.logout()
        except SphSessionException as exception:
            logging.error("Failed to logout: %s", str(exception))

    def __parse_delegation_html(self, clazz: str, fields: list[str]):
        soup = self.__get_delegation_html()
        now = datetime.now()
        for div in self.__get_divs_id_beginning_with(soup, 'tag'):
            date = datetime.strptime(
                div.get('id').replace('tag', ''), '%d_%m_%Y').date()
            date_str = date.strftime('%d.%m.%Y')

            if date < now.date():
                logging.info("Skipping %s ...", date.strftime('%d.%m.%Y'))
                continue

            table = div.find_next('table',
                                  {'id': div.get('id').replace('tag', 'vtable')})
            table = DelegationTable(clazz, fields, date_str, table)
            events = table.search_by_class()
            for event in events:
                self.push_service.send(event, self.__push_message(event))

    def __get_delegation_html(self) -> BeautifulSoup:
        try:
            delegation_txt = self.session.get('vertretungsplan.php')
            soup = BeautifulSoup(delegation_txt, 'html.parser')
            try:
                with open(file="vertretungsplan.html", mode='w', encoding="utf-8") as file:
                    file.write(soup.prettify())
            except IOError as io_exception:
                logging.warning("Writing html file failed: %s",
                                str(io_exception))
            self.__check_delegation_html(soup)

            return soup
        except SphSessionException as exception:
            raise SphException("Failed to get delegation html") from exception

    def __check_delegation_html(self, soup: BeautifulSoup) -> None:
        alerts = self.__get_divs_class_beginning_with(soup, "alert")
        if len(alerts) > 0:
            raise SphException("Not logged in any longer!")

    def __get_divs_class_beginning_with(self, soup: BeautifulSoup, div_class_begins_with: str):
        result = []
        for div in soup.find_all('div'):
            class_value = div.get('class')
            if isinstance(class_value, list):
                found = False
                for clazz in class_value:
                    if clazz is not None and clazz.startswith(div_class_begins_with):
                        found = True
                        break
                if found:
                    result.append(div)
            elif isinstance(class_value, str):
                if class_value.startswith(div_class_begins_with):
                    result.append(div)
            elif class_value is None:
                pass
            else:
                raise SphException("Invalid type: " + str(type(class_value)))
        return result

    def __get_divs_id_beginning_with(self, soup: BeautifulSoup, div_id_begins_with: str):
        result = []
        for div in soup.find_all('div'):
            id_value = div.get('id')
            if id_value is not None and id_value.startswith(div_id_begins_with):
                result.append(div)
        return result

    def __push_message(self, event: dict[str, str]) -> str:
        return f"{event['Datum']}: {event['Hinweis']} im Fach {event['Fach']} " \
            "in Stunde {event['Stunde']}"


def parse_arguments() -> Any:
    """ Parse command line arguments and return to the caller """
    parser = argparse.ArgumentParser(
        description='Vertretungsplan im Schulportal Hessen (SPH) prüfen.')
    parser.add_argument('-c', '--config-file', help='Yaml config file',
                        action='store', type=str, required=True)
    parser.add_argument('-d', '--debug', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    return args


def signal_handler(signal_num: int, *_: Any) -> None:
    """ Signal handler that exits from the code """
    logging.info("Exiting on signal %s ...", signal.Signals(signal_num).name)
    sys.exit(0)


def main():
    """ Main method """
    args = parse_arguments()
    if args.debug:
        rootLogger.setLevel(logging.DEBUG)
        for handler in rootLogger.handlers:
            handler.setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.INFO)

    logging.info("Arguments: %s", str(args))

    config = SphConfig(args.config_file, False)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    with SphExecutor(config) as executor:
        executor.run()


if __name__ == '__main__':
    main()
