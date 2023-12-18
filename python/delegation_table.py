""" Support the delegation table delivered via SPH """

import bs4.element

from sph.sph_exception import SphException


def get_value(cells, idx: int) -> str:
    """ Extract a value or '' """
    value = cells[idx].find(text=True)
    if value is not None:
        return value.strip()
    else:
        return ''


class DelegationTable:
    """ Support the delegation table delivered via SPH """

    def __init__(self, clazz: str, fields: list[str], date: str,
                 delegation_table: bs4.element.PageElement) -> None:
        self.clazz = clazz
        self.fields = fields
        self.date = date
        self.table = delegation_table
        self.table_headers = self.table.find_all('th')
        self.class_idx = -1
        self.hour_idx = -1
        self.field_idx = -1
        self.room_idx = -1
        self.note_idx = -1
        self.note2_idx = -1

        # print(self.table)
        count = 0
        for header in self.table_headers:
            txt = header.text.strip()
            if txt == 'Klasse':
                self.class_idx = count
            elif txt == 'Stunde':
                self.hour_idx = count
            elif txt == 'Fach':
                self.field_idx = count
            elif txt == 'Raum':
                self.room_idx = count
            elif txt == 'Hinweis':
                self.note_idx = count
            elif txt == 'Hinweis2':
                self.note2_idx = count
            count += 1

        if self.class_idx == -1:
            raise SphException("Unable to find class column")
        if self.hour_idx == -1:
            raise SphException("Unable to find hour column")
        if self.field_idx == -1:
            raise SphException("Unable to find field column")
        if self.room_idx == -1:
            raise SphException("Unable to find room column")
        if self.note_idx == -1:
            raise SphException("Unable to find note column")
        if self.note2_idx == -1:
            raise SphException("Unable to find second note column")

    def search_by_class(self):
        """ Search events in the table for the given class or grade """
        result = []
        for row in self.table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 1:
                class_txt = get_value(cells, self.class_idx)
                field_txt = get_value(cells, self.field_idx)
                if self.clazz in class_txt and self.__field_match(field_txt):
                    result.append(self.__row_to_dict(cells))
        return result

    def __field_match(self, field: str):
        for f in self.fields:
            if field.startswith(f):
                return True
        return False

    def __row_to_dict(self, cells):
        return {
            'Datum': self.date,
            'Klasse': get_value(cells, self.class_idx),
            'Stunde': get_value(cells, self.hour_idx),
            'Fach': get_value(cells, self.field_idx),
            'Raum': get_value(cells, self.room_idx),
            'Hinweis': self.__get_note(cells)
        }

    def __get_note(self, cells):
        note = get_value(cells, self.note_idx)
        note2 = get_value(cells, self.note2_idx)
        if len(note2) > 0:
            return f"{note} ({note2})"
        else:
            return note
