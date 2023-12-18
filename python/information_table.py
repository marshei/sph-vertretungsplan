""" Support the delegation table delivered via SPH """

import bs4.element


def get_value(cell) -> str:
    """ Extract a value or '' """
    value = cell.find(text=True)
    if value is not None:
        return value.strip()
    else:
        return ''


class InformationTable:
    """ Support the delegation table delivered via SPH """

    def __init__(self, clazz: str, fields: list[str], date: str,
                 information_table: bs4.element.PageElement) -> None:
        self.clazz = clazz
        self.fields = fields
        self.date = date
        self.table = information_table

        # print(self.table)

    def search_by_class_and_fields(self):
        """ Search events in the table for the given class and fields """
        result = []
        if self.table is None:
            return result

        for row in self.table.find_all('tr'):
            cells = row.find_all('td')
            for cell in cells:
                info = get_value(cell)
                if self.__match_class_and_field(info):
                    result.append(self.__row_to_dict(info))
        return result

    def __match_class_and_field(self, value: str) -> bool:
        for f in self.fields:
            search = f"{self.clazz}{f}"
            if search in value:
                return True
        return False

    def __row_to_dict(self, info):
        return {
            'Datum': self.date,
            'Info': info
        }
