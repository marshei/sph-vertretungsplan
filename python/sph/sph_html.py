"""Evaluate HTMl pages from SPH"""
import logging
from bs4 import BeautifulSoup
import bs4
from sph.sph_exception import SphException

from sph.sph_alerts import SphAlerts


class SphHtml:
    """Parse HTML pages from SPH"""

    def __init__(self, page_text: str) -> None:
        self.soup = BeautifulSoup(page_text, "html.parser")
        self.alerts = SphAlerts(self.get_matching_divs("class", "alert"))

    def is_logged_out(self) -> bool:
        """True if logged out"""
        return self.alerts.is_logged_out()

    def write_html_file(self, file_name: str) -> None:
        """Write page contents to file"""
        try:
            with open(file=file_name, mode="w", encoding="utf-8") as file:
                file.write(self.soup.prettify())
        except IOError as io_exception:
            logging.warning(
                "Writing html file %s failed: %s", file_name, str(io_exception)
            )

    def get_matching_divs(
        self, tag_name: str, tag_begins_with: str
    ) -> list[bs4.element.Tag]:
        """List of matching divs"""
        result = []
        for div in self.soup.find_all("div"):
            if self.__div_tag_matches(div.get(tag_name), tag_begins_with):
                result.append(div)
        return result

    def __div_tag_matches(self, tag_value, tag_begins_with: str) -> bool:
        if isinstance(tag_value, list):
            for value in tag_value:
                if value is not None and value.startswith(tag_begins_with):
                    return True
        elif isinstance(tag_value, str):
            if tag_value.startswith(tag_begins_with):
                return True
        elif tag_value is None:
            pass
        else:
            raise SphException("Invalid type: " + str(type(tag_value)))

        return False
