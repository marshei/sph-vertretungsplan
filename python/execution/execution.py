""" Period or one-time Execuition of a callback """

import logging
import time
import traceback
from datetime import datetime
from typing import Any

import pycron
from push_over.push_over import PushOver
from sph.sph_exception import SphException


class Execution:
    """ Period or one-time Execuition of a callback """

    def __init__(self, execution_config: dict[str, Any], push_service: PushOver) -> None:
        self.interval_seconds = 60
        self.is_executing_callback = False
        self.push_service = push_service
        self.cron = []

        if execution_config is not None:
            if 'cron' not in execution_config:
                raise SphException(
                    f"Invalid Execution configuration: {str(execution_config)}")

            if execution_config['cron'] is not None:
                for spec in execution_config['cron']:
                    self.cron.append(spec.lower())

        for cron_entry in self.cron:
            try:
                pycron.is_now(cron_entry)
            except Exception as exc:
                raise SphException(
                    f"Invalid cron specification: {cron_entry} ({str(exc)})") from exc

    def run_scheduled(self, func) -> None:
        """ Run the callback once or periodically """
        if len(self.cron) == 0:
            logging.warning("No schedule, executing once!")
            self.__run_function(func)
            return

        while True:
            need_execution = self.__need_execution()
            if need_execution:
                self.__run_function(func)

            time.sleep(self.interval_seconds)

    def __run_function(self, func) -> None:
        try:
            self.is_executing_callback = True
            func()
        except Exception as exc:
            traceback.print_exc()
            self.push_service.send_error(str(exc))
        finally:
            self.is_executing_callback = False

    def __need_execution(self) -> bool:
        dt = datetime.now()
        for c in self.cron:
            if pycron.is_now(c, dt):
                return True

        return False
