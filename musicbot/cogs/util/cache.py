import collections

from .ytdl import YTDLSource


class QueueTable(collections.MutableSequence):
    def __init__(self, bot, name):
        self._list = []
        self._name = name
        self._bot = bot
        self._database = bot.database
        self._populated = False

    async def _populate(self):
        self._bot.logger.info('Populating queue from last save..')
        if self._check_table_exists(self._name):
            res = self.execute(f"""SELECT * FROM "{self._name}" """)
            self._bot.logger.info(res)
            temp = [None] * len(res)
            for i in res:
                user = self._bot.get_user(i[1])
                temp[i[0]] = await YTDLSource.from_url(i[2], user=user)

            for i in temp:
                self.append(i)
        else:
            self._bot.logger.info(f'Creating table {self._name}')
            self.execute(f"""CREATE TABLE "{self._name}" (idx INTEGER, queuer INTEGER, url TEXT)""")

        self._populated = True

    def _check_table_exists(self, tablename):
        dbcur = self._database.cursor()
        dbcur.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='{0}';
            """.format(tablename.replace('\'', '\'\'')))
        if dbcur.fetchone():
            dbcur.close()
            return True

        dbcur.close()
        return False

    def execute(self, command, *args, commit=True):
        cur = self._database.cursor()
        cur.execute(command, args)
        result = cur.fetchall()
        if commit: self._database.commit()
        cur.close()
        return result

    @property
    def populated(self):
        return self._populated

    def __setitem__(self, key: int, value: YTDLSource):
        self._list[key] = value
        if self.populated:
            self.execute(f"""
            UPDATE "{self._name}"
            SET queuer = ?, url = ?
            WHERE idx = {key}
            """, value.user and value.user.id, value.origin_url)

        return value

    def __getitem__(self, key: int):
        return self._list[key]

    def __delitem__(self, key):
        if key < 0: key %= len(self)
        del self._list[key]
        if self.populated:
            self.execute(f"""
            DELETE FROM "{self._name}"
            WHERE idx = {key}
            """)

            self.execute(f"""
            UPDATE "{self._name}"
            SET idx = idx - 1
            WHERE idx > {key}
            """)
        return key

    def __len__(self):
        return len(self._list)

    def __iter__(self):
        for x in self._list:
            yield x

    def insert(self, index, item: YTDLSource):
        self._list.insert(index, item)
        if self.populated:
            self.execute(f"""
            UPDATE "{self._name}"
            SET idx = idx + 1
            WHERE idx >= {index}
            """, commit=False)

            self.execute(f"""
            INSERT INTO "{self._name}"
            VALUES (?, ?, ?)
            """, min(len(self), index), item.user and item.user.id, item.origin_url)