from datetime import datetime
import time
import logging
import traceback
import pycron
from typing import Any

from push_over.push_over import PushOver


class Execution:

    def __init__(self, execution_config: dict[str, Any], push_service: PushOver) -> None:
        self.interval_seconds = 60
        self.push_service = push_service
        self.cron = []

        if execution_config is not None:
            if 'cron' not in execution_config:
                raise Exception("Invalid Execution configuration: %s" %
                                execution_config)

            self.interval_seconds = execution_config['interval'] * 60
            if self.interval_seconds < 60:
                logging.warning("Increasing execution interval from %d to %d seconds" %
                                (self.interval_seconds, 60))
                self.interval_seconds = 60
            if execution_config['cron'] is not None:
                self.cron = execution_config['cron']

        for c in self.cron:
            try:
                pycron.is_now(c)
            except Exception as e:
                raise Exception("Invalid cron sepcification: %s (%s)" %
                                (c, str(e)))

    def run_function(self, func) -> None:
        try:
            func()
        except Exception as e:
            traceback.print_exc()
            error = {
                'Datum': datetime.now().date().strftime('%d.%m.%Y'),
                'Fehlermeldung': str(e)
            }
            self.push_service.send(error, "ERROR: %s" %
                                   str(error), is_error=True)

    def run_scheduled(self, func) -> None:
        if len(self.cron) == 0:
            logging.warning(
                "Calling function only once as no cron sepcifications were given!")
            self.run_function(func)
            return

        need_execution = self.need_execution()
        while True:
            if need_execution:
                self.run_function(func)
                since = datetime.now()

            time.sleep(self.interval_seconds)
            need_execution = self.need_execution()

    def need_execution(self):
        dt = datetime.now()
        for c in self.cron:
            if pycron.is_now(c, dt):
                return True

        return False
