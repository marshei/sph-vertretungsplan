""" School Holidays """

import logging
from datetime import date, datetime
from typing import Any, List

from sph.sph_exception import SphException


def check_date(date_value) -> date:
    if isinstance(date_value, str):
        return datetime.strptime(date_value, '%Y-%m-%d').date()
    if isinstance(date_value, date):
        return date_value
    raise SphException(f"Invalid holiday date configuration: {str(date_value)}, type: {type(date_value)}")


class SchoolHolidays:
    """ School Holidays """

    def __init__(self, holiday_config: List[dict[Any, Any]]) -> None:
        year = date.today().year
        self.holiday_config = None
        if holiday_config is not None:
            for year_config in holiday_config:
                if year in year_config:
                    self.holiday_config = year_config[year]
                if str(year) in year_config:
                    self.holiday_config = year_config[str(year)]

        if self.holiday_config is not None:
            for holiday in self.holiday_config:
                if 'name' not in holiday or 'from' not in holiday or 'to' not in holiday:
                    raise SphException(f"Invalid holiday configuration: {str(holiday)}")

                holiday['from'] = check_date(holiday['from'])
                holiday['to'] = check_date(holiday['to'])

    def is_holiday_today(self) -> bool:
        """ Checks whether today is a school holiday """
        today = date.today()
        if self.holiday_config is None:
            logging.debug("No school holidays configured for %s", today.year)
            return False

        for holiday in self.holiday_config:
            if holiday['from'] <= today <= holiday['to']:
                logging.debug("Today is a holiday in %s", holiday['name'])
                return True
        return False
