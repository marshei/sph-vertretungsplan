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

from delegation_table import DelegationTable
from execution.execution import Execution
from information_table import InformationTable
from push_over.push_over import PushOver
from school_holidays.school_holidays import SchoolHolidays
from sph.sph_config import SphConfig
from sph.sph_exception import SphException, SphLoggedOutException
from sph.sph_html import SphHtml
from sph.sph_school import SphSchool
from sph.sph_session import SphSession
from sph.sph_session import SphSessionException


class TimezoneAwareLogFormatter(logging.Formatter):
    """Override logging.Formatter to use an timezone-aware datetime object"""

    def converter(self, timestamp) -> datetime:
        """Adjust the timezone of the timestamp to Europe/Berlin"""
        return datetime.fromtimestamp(timestamp, tz=pytz.UTC).astimezone(
            pytz.timezone("Europe/Berlin")
        )

    def formatTime(self, record, datefmt=None) -> str:
        converted_time = self.converter(record.created)
        if datefmt:
            return converted_time.strftime(datefmt)

        try:
            return converted_time.isoformat(timespec="milliseconds")
        except TypeError:
            return converted_time.isoformat()


logFormatter = TimezoneAwareLogFormatter(
    fmt="%(asctime)s [%(funcName)-12.12s] [%(levelname)-4.7s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %Z",
)
rootLogger = logging.getLogger()

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.INFO)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)
rootLogger.setLevel(logging.INFO)


class SphExecutor:
    """Executing the checks in the SPH"""

    def __init__(self, config: SphConfig) -> None:
        self.config = config
        self.school = SphSchool(
            city=config["school-city"],
            name=config["school-name"],
            school_id=config["school-id"],
        )
        self.holiday = SchoolHolidays(config["school-holidays"])
        self.push_service = PushOver(config["push-over"], self.config.get_storage_directory())
        self.execution = Execution(config["execution"], self.push_service)

        self.session = SphSession(
            school_id=self.school.get_id(),
            user=config["user"],
            password=config["password"],
        )

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        logging.info("Exiting SPH executor ...")
        self.__logout()

    def run(self) -> None:
        """Run the SPH checks scheduled or once"""
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
                self.__parse_delegation_html(
                    self.config["class"], self.config["fields"]
                )
                return True
            except SphLoggedOutException as exception:
                logging.error("Failed to process html: %s", str(exception))
                self.__logout()
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
        sph_html = self.__get_delegation_html()
        now = datetime.now()
        for div in sph_html.get_matching_divs("id", "tag"):
            date = datetime.strptime(
                div.get("id").replace("tag", ""), "%d_%m_%Y"
            ).date()
            date_str = date.strftime("%d.%m.%Y")

            if date < now.date():
                logging.info("Skipping %s ...", date.strftime("%d.%m.%Y"))
                continue

            # Process info table
            info_element = div.find_next("table", {"class": "infos"})
            info_table = InformationTable(clazz, fields, date_str, info_element)
            for info_event in info_table.search_by_class_and_fields():
                self.push_service.send(info_event, self.__push_info_message(info_event))

            # Process delegation table
            table_element = div.find_next(
                "table", {"id": div.get("id").replace("tag", "vtable")}
            )
            table = DelegationTable(clazz, fields, date_str, table_element)
            for event in table.search_by_class():
                self.push_service.send(event, self.__push_message(event))

    def __get_delegation_html(self) -> SphHtml:
        try:
            delegation_txt = self.session.get("vertretungsplan.php")
            sph_html = SphHtml(delegation_txt)
            sph_html.write_html_file(self.config.get_storage_filename("vertretungsplan.html"))
            if sph_html.is_logged_out():
                raise SphLoggedOutException("Not logged in any longer!")
            return sph_html
        except SphSessionException as exception:
            raise SphException("Failed to get delegation html") from exception

    def __push_info_message(self, event: dict[str, str]) -> str:
        return (
            f"{event['Datum']}: {event['Info']}"
        )

    def __push_message(self, event: dict[str, str]) -> str:
        return (
            f"{event['Datum']}: {event['Hinweis']} im Fach {event['Fach']} "
            f"in Stunde {event['Stunde']}"
        )


def parse_arguments() -> Any:
    """Parse command line arguments and return to the caller"""
    parser = argparse.ArgumentParser(
        description="Vertretungsplan im Schulportal Hessen (SPH) prüfen."
    )
    parser.add_argument(
        "-c",
        "--config-file",
        help="Yaml config file",
        action="store",
        type=str,
        required=True,
    )
    parser.add_argument("-d", "--debug", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    return args


def signal_handler(signal_num: int, *_: Any) -> None:
    """Signal handler that exits from the code"""
    logging.info("Exiting on signal %s ...", signal.Signals(signal_num).name)
    sys.exit(0)


def main():
    """Main method"""
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


if __name__ == "__main__":
    main()
