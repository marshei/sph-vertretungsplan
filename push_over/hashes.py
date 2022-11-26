class Hashes:

    def __init__(self, filename) -> None:
        self.filename = filename
        self.separator = ' - '
        self.hashes = {}
        try:
            f = open(self.filename, 'r')
            for line in f.readlines():
                parts = line.split(self.separator)
                self.hashes.update({parts[0]: parts[1]})
            f.close()
        except FileNotFoundError:
            pass

    def already_known(self, key):
        return key in self.hashes

    def add(self, key, value):
        f = open(self.filename, 'a')
        f.write(key + self.separator + value + '\n')
        f.close()
        self.hashes.update({key: value})
