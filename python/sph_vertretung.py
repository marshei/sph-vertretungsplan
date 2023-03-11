#!/usr/bin/env python3

import argparse
import logging
import traceback
from datetime import datetime

from bs4 import BeautifulSoup

from delegation_table import DelegationTable
from execution.execution import Execution
from push_over.push_over import PushOver
from school_holidays.school_holidays import SchoolHolidays
from sph.config import Config
from sph.sph_school import SphSchool
from sph.sph_session import SphSession

logFormatter = logging.Formatter(
    "%(asctime)s [%(funcName)-12.12s] [%(levelname)-4.7s] %(message)s")
rootLogger = logging.getLogger()

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.INFO)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)
rootLogger.setLevel(logging.INFO)


def get_delegation_html(config: Config) -> BeautifulSoup:
    sph_school = SphSchool(
        city=config['school-city'], name=config['school-name'], school_id=config['school-id'])
    sph_session = SphSession(school_id=sph_school.get_id(
    ), user=config['user'], password=config['password'])

    sph_session.login()
    try:
        delegation_txt = sph_session.get(
            'https://start.schulportal.hessen.de/vertretungsplan.php')
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


def push_message(event):
    return event['Datum'] + ": " + event['Hinweis'] + " im Fach " + event['Fach'] + " in Stunde " + event['Stunde']


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Vertretungsplan im Schulportal Hessen (SPH) prüfen.')
    parser.add_argument('-c', '--config-file', help='Yaml config file',
                        action='store', type=str, required=True)
    parser.add_argument('-d', '--debug', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    return args


def check_sph(config: Config, holiday: SchoolHolidays, push_service: PushOver):
    if holiday.is_holiday_today():
        return

    soup = get_delegation_html(config)
    parse_delegation_html(push_service, soup, config['class'], config['fields'])


def main():
    args = parse_arguments()
    if args.debug:
        rootLogger.setLevel(logging.DEBUG)
        for handler in rootLogger.handlers:
            handler.setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.INFO)

    logging.debug("Arguments: %s", args)

    config = Config(args.config_file, False)
    holiday = SchoolHolidays(config['school-holidays'])
    push_service = PushOver(config['push-over'], config['config-dir'])
    execution = Execution(config['execution'], push_service)

    try:
        execution.run_scheduled(lambda: check_sph(config, holiday, push_service))
    except Exception as e:
        traceback.print_exc()
        error = {
            'Datum': datetime.now().date().strftime('%d.%m.%Y'),
            'Fehlermeldung': str(e)
        }
        push_service.send(error, "ERROR: %s" % str(error), is_error=True)


if __name__ == '__main__':
    main()
