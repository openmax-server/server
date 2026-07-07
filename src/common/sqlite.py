class SQLiteCursorCompat:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = None

    async def __aenter__(self):
        self.cursor = await self.connection.cursor()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.cursor is not None:
            await self.cursor.close()
        self.cursor = None

    @property
    def lastrowid(self):
        return None if self.cursor is None else self.cursor.lastrowid

    def _normalize_query(self, query):
        return query.replace("%s", "?").replace(
            "UNIX_TIMESTAMP()", "CAST(strftime('%s','now') AS INTEGER)"
        )

    async def execute(self, query, params=()):
        normalized_query = self._normalize_query(query)
        if params is None:
            params = ()
        elif not isinstance(params, (tuple, list, dict)):
            params = (params,)
        await self.cursor.execute(normalized_query, params)

    async def fetchone(self):
        row = await self.cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetchall(self):
        rows = await self.cursor.fetchall()
        return [dict(row) for row in rows]

class SQLiteConnectionCompat:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        await self.connection.commit()

    def cursor(self):
        return SQLiteCursorCompat(self.connection)

class SQLitePoolCompat:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return SQLiteConnectionCompat(self.connection)
