import logging
from datetime import date
from typing import Any, List


class SchoolHolidays:

    def __init__(self, holiday_config: List[dict[Any, Any]]) -> None:
        self.today = date.today()
        self.holiday_config = None
        for year in holiday_config:
            if self.today.year in year:
                self.holiday_config = year[self.today.year]

    def is_holiday_today(self) -> bool:
        if self.holiday_config is None:
            logging.debug("No school holidays configured for %d!" % self.today.year)
            return False

        for holiday in self.holiday_config:
            if 'name' not in holiday or 'from' not in holiday or 'to' not in holiday:
                raise Exception("Invalid holiday configuration: %s" % holiday)

            if not isinstance(holiday['from'], date) or not isinstance(holiday['to'], date):
                raise Exception("Invalid holiday configuration: %s" % holiday)

            if holiday['from'] <= self.today <= holiday['to']:
                logging.debug("Today is a holiday in %s" % holiday['name'])
                return True
        return False
