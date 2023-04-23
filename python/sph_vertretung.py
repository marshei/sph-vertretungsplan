#!/usr/bin/env python3

import argparse
import logging
import signal
import sys
import traceback
import pytz

from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from delegation_table import DelegationTable
from execution.execution import Execution
from push_over.push_over import PushOver
from school_holidays.school_holidays import SchoolHolidays
from sph.sph_config import SphConfig
from sph.sph_school import SphSchool
from sph.sph_session import SphSession


class TimezoneAwareLogFormatter(logging.Formatter):
    """override logging.Formatter to use an timezone-aware datetime object"""

    def converter(self, timestamp):
        # Create datetime in UTC
        dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        # Change datetime's timezone
        return dt.astimezone(pytz.timezone('Europe/Berlin'))

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec='milliseconds')
            except TypeError:
                s = dt.isoformat()
        return s


logFormatter = TimezoneAwareLogFormatter(
    fmt="%(asctime)s [%(funcName)-12.12s] [%(levelname)-4.7s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %Z")
rootLogger = logging.getLogger()

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.INFO)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)
rootLogger.setLevel(logging.INFO)


def get_delegation_html(school: SphSchool, user: str, password: str) -> BeautifulSoup:
    sph_session = SphSession(school_id=school.get_id(),
                             user=user, password=password)

    sph_session.login()
    try:
        delegation_txt = sph_session.get('vertretungsplan.php')
        soup = BeautifulSoup(delegation_txt, 'html.parser')
        file = open("vertretungsplan.html", 'w')
        file.write(soup.prettify())
        file.close()
    finally:
        sph_session.logout()

    return soup


def parse_delegation_html(push_service: PushOver, soup: BeautifulSoup, clazz: str, fields: list[str]):
    now = datetime.now()
    for div in get_divs_id_beginning_with(soup, 'tag'):
        date = datetime.strptime(
            div.get('id').replace('tag', ''), '%d_%m_%Y').date()
        date_str = date.strftime('%d.%m.%Y')

        if date < now.date():
            logging.info("Skipping " + date.strftime('%d.%m.%Y') + " ...")
            continue

        table = div.find_next(
            'table', {'id': div.get('id').replace('tag', 'vtable')})
        dt = DelegationTable(clazz, fields, date_str, table)
        events = dt.search_by_class()
        for event in events:
            push_service.send(event, push_message(event))


def get_divs_id_beginning_with(soup: BeautifulSoup, div_id_begins_with: str):
    result = []
    for div in soup.find_all('div'):
        id_value = div.get('id')
        if id_value is not None and id_value.startswith(div_id_begins_with):
            result.append(div)
    return result


def push_message(event) -> str:
    return event['Datum'] + ": " + event['Hinweis'] + " im Fach " + event['Fach'] + " in Stunde " + event['Stunde']


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Vertretungsplan im Schulportal Hessen (SPH) prüfen.')
    parser.add_argument('-c', '--config-file', help='Yaml config file',
                        action='store', type=str, required=True)
    parser.add_argument('-d', '--debug', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    return args


def check_sph(config: SphConfig, school: SphSchool, holiday: SchoolHolidays, push_service: PushOver) -> None:
    if holiday.is_holiday_today():
        return

    logging.info("Checking SPH ...")
    soup = get_delegation_html(school, config['user'], config['password'])
    parse_delegation_html(push_service, soup,
                          config['class'], config['fields'])


def signal_handler(signal_num: int, frame: Any) -> None:
    logging.info("Exiting on signal {sig} ..."
                 .format(sig=signal.Signals(signal_num).name))
    sys.exit(0)


def main():
    args = parse_arguments()
    if args.debug:
        rootLogger.setLevel(logging.DEBUG)
        for handler in rootLogger.handlers:
            handler.setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.INFO)

    logging.info("Arguments: {}".format(args))

    config = SphConfig(args.config_file, False)
    school = SphSchool(city=config['school-city'], name=config['school-name'],
                       school_id=config['school-id'])
    holiday = SchoolHolidays(config['school-holidays'])
    push_service = PushOver(config['push-over'], config['config-dir'])
    execution = Execution(config['execution'], push_service)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        execution.run_scheduled(lambda: check_sph(config, school,
                                                  holiday, push_service))
    except Exception as e:
        traceback.print_exc()
        push_service.send_error(str(e))


if __name__ == '__main__':
    main()
