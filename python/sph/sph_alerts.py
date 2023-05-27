"""Evaluate alerts from SPH"""
import logging
import bs4


class SphAlertClass:
    """Evaluate the class of an alert from SPH"""

    def __init__(self, clazz: str) -> None:
        self.clazz = "" if clazz is None else clazz

    def is_warning(self) -> bool:
        """True if alert is warning"""
        return "warning" in self.clazz

    def is_danger(self) -> bool:
        """True if alert is a danger"""
        return "danger" in self.clazz


class SphAlerts:
    """Recieved Alerts from SPH"""

    def __init__(self, alerts: list[bs4.element.Tag]) -> None:
        self.dangers = []
        self.warnings = []
        for alert in alerts:
            self.__classify_alert(alert)

    def is_logged_out(self) -> bool:
        """Logged out from SPH?"""
        self.__print_alerts()
        return len(self.dangers) > 0

    def __print_alerts(self) -> None:
        """Print all detected alerts"""
        for warning in self.warnings:
            logging.debug("%s", warning)
        for danger in self.dangers:
            logging.debug("%s", danger)

    def __classify_alert(self, alert: bs4.element.Tag) -> None:
        for clazz in self.__get_class_list(alert):
            sph_alert_clazz = SphAlertClass(clazz)
            alert_text = self.__get_alert_text(alert)
            if sph_alert_clazz.is_warning():
                if not self.__ignore_alert(alert_text):
                    self.warnings.append(f"WARNING: {alert_text}")
                    return
            if sph_alert_clazz.is_danger():
                self.dangers.append(f"DANGER: {alert_text}")
                return

    def __get_class_list(self, alert: bs4.element.Tag) -> list[str]:
        class_value = alert.get("class")
        if isinstance(class_value, list):
            return class_value
        if isinstance(class_value, str):
            return [class_value]
        return []

    def __get_alert_text(self, alert: bs4.element.Tag) -> str:
        text = alert.text.replace("\n", " ").replace("\r", "")
        return " ".join(text.split())
    
    def __ignore_alert(self, alert_text:str) -> bool:
        if alert_text.startswith("Keine Einträge"):
            return True
        
        return False
