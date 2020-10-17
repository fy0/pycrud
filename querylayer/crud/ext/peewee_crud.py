from dataclasses import dataclass
from typing import Any

from querylayer.crud.sql_crud import SQLCrud


@dataclass
class PeeweeCrud(SQLCrud):
    db: Any

    async def execute_sql(self, sql):
        return self.db.execute_sql(sql)