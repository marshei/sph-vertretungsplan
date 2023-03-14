import logging
import time
import traceback
from datetime import datetime
from typing import Any

import pycron
from push_over.push_over import PushOver


class Execution:

    def __init__(self, execution_config: dict[str, Any], push_service: PushOver) -> None:
        self.interval_seconds = 60
        self.is_executing_callback = False
        self.push_service = push_service
        self.cron = []

        if execution_config is not None:
            if 'cron' not in execution_config:
                raise Exception("Invalid Execution configuration: %s" %
                                execution_config)

            if execution_config['cron'] is not None:
                for spec in execution_config['cron']:
                    self.cron.append(spec.lower())

        for c in self.cron:
            try:
                pycron.is_now(c)
            except Exception as e:
                raise Exception("Invalid cron specification: %s (%s)" %
                                (c, str(e)))

    def is_executing(self) -> bool:
        return self.is_executing_callback
    
    def run_function(self, func) -> None:
        try:
            self.is_executing_callback = True
            func()
        except Exception as e:
            traceback.print_exc()
            error = {
                'Datum': datetime.now().date().strftime('%d.%m.%Y'),
                'Fehlermeldung': str(e)
            }
            try:
                self.push_service.send(error, "ERROR: %s" %
                                       str(error), is_error=True)
            except:
                logging.error("Failed sending error: %s", str(error))
        finally:
            self.is_executing_callback = False

    def run_scheduled(self, func) -> None:
        if len(self.cron) == 0:
            logging.warning(
                "Calling function only once as no cron specifications were given!")
            self.run_function(func)
            return

        need_execution = self.need_execution()
        while True:
            if need_execution:
                self.run_function(func)

            time.sleep(self.interval_seconds)
            need_execution = self.need_execution()

    def need_execution(self) -> bool:
        dt = datetime.now()
        for c in self.cron:
            if pycron.is_now(c, dt):
                return True

        return False
