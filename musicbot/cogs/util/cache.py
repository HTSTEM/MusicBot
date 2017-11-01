import collections

from .ytdl import YTDLSource


class CachedList(collections.MutableSequence):
    def __init__(self, bot, name):
        self._list = []
        self._name = name
        self._bot = bot
        self._database = bot.database
        
    async def _populate(self):
        self._bot.logger.info('Populating queue from last save..')
    
        if self._name == 'queue':
            if self._check_table_exists(self._name):
                cur = self._database.cursor()
                cur.execute("""SELECT * FROM {}""".format(self._name))
                
                res = cur.fetchall()
                temp = [None] * len(res)
                for i in res:
                    user = self._bot.get_user(i[1])
                    
                    temp[i[0]] = await YTDLSource.from_url(i[2], user=user)
                cur.close()
                self._database.commit()
                for i in temp:
                    self.append(i)
        
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
        
    def _save(self):
        cur = self._database.cursor()
        
        if self._check_table_exists(self._name):
            cur.execute("""DROP TABLE {}""".format(self._name))
        
        if self._name == 'queue':
            cur.execute("""CREATE TABLE {} (idx INTEGER, queuer INTEGER, url TEXT)""".format(self._name))
            
            n = 0
            for i in self:
                if i.user:
                    cur.execute("""INSERT INTO {} (idx, queuer, url) VALUES (?, ?, ?)""".format(self._name),
                        (
                         n, i.user.id, i.origin_url
                        ))
                    n += 1
            
            self._database.commit()
        else:
            self._bot.logger.warning(f'WARNING! TRIED TO SAVE CACHED LIST {self._name} BUT NOT RECOGNISED!')
            
        cur.close()
        

    def __setitem__(self, key, value):
        self._list[key] = value
        return self._save()

    def __getitem__(self, key):
        return self._list[key]

    def __delitem__(self, key):
        del self._list[key]
        return self._save()

    def __len__(self): return len(self._list)
    def insert(self, index, item):
        self._list.insert(index, item)
        return self._save()