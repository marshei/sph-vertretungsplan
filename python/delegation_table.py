import bs4.element


def get_value(cells, idx: int) -> str:
    value = cells[idx].find(text=True)
    if value is not None:
        return value.strip()
    else:
        return ''


class DelegationTable:

    def __init__(self, clazz: str, fields: list[str], date: str, delegation_table: bs4.element.PageElement) -> None:
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

        # print(self.table.prettify())
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
            raise Exception("Unable to find class column")
        if self.hour_idx == -1:
            raise Exception("Unable to find hour column")
        if self.field_idx == -1:
            raise Exception("Unable to find field column")
        if self.room_idx == -1:
            raise Exception("Unable to find room column")
        if self.note_idx == -1:
            raise Exception("Unable to find note column")
        if self.note2_idx == -1:
            raise Exception("Unable to find second note column")

    def search_by_class(self):
        result = []
        for row in self.table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 1:
                class_txt = get_value(cells, self.class_idx)
                field_txt = get_value(cells, self.field_idx)
                if self.clazz in class_txt and self.field_match(field_txt):
                    result.append(self.row_to_dict(cells))
        return result

    def field_match(self, field: str):
        for f in self.fields:
            if field.startswith(f):
                return True
        return False

    def row_to_dict(self, cells):
        return {
            'Datum': self.date,
            'Klasse': get_value(cells, self.class_idx),
            'Stunde': get_value(cells, self.hour_idx),
            'Fach': get_value(cells, self.field_idx),
            'Raum': get_value(cells, self.room_idx),
            'Hinweis': self.get_note(cells)
        }

    def get_note(self, cells):
        note = get_value(cells, self.note_idx)
        note2 = get_value(cells, self.note2_idx)
        if len(note2) > 0:
            return "{n} ({n2})".format(n=note, n2=note2)
        else:
            return note
