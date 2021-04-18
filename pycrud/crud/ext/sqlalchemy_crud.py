import inspect
from dataclasses import dataclass
from typing import Any, Union, Dict, Type

import pypika
import typing


from pycrud.types import Entity
from pycrud.crud.sql_crud import SQLCrud, PlaceHolderGenerator, SQLExecuteResult
from pycrud.error import DBException, UnknownDatabaseException

if typing.TYPE_CHECKING:
    try:
        from sqlalchemy.future import Engine
    except ImportError:
        pass


@dataclass
class SQLAlchemyCrud(SQLCrud):
    entity2model: Dict[Type[Entity], Union[str, Any]]
    db: 'Engine'

    def __post_init__(self):
        import sqlalchemy
        import sqlalchemy.types
        import sqlalchemy.exc
        import sqlalchemy.inspection
        from sqlalchemy.orm import sessionmaker

        super().__post_init__()

        def is_sqlalchemy_model(v: Type):
            if inspect.isclass(v):
                try:
                    return sqlalchemy.inspection.inspect(v)
                except sqlalchemy.exc.NoInspectionAvailable:
                    pass

        self._primary_keys = {}
        for k, v in self.entity2model.items():
            model_info = is_sqlalchemy_model(v)

            if model_info:
                self._primary_keys[k] = [key.name for key in model_info.primary_key]

                for c in v.__table__.c:
                    if isinstance(c.type, sqlalchemy.types.ARRAY):
                        self._table_cache[k]['array_fields'].add(c.name)
                    elif isinstance(c.type, sqlalchemy.types.JSON):
                        self._table_cache[k]['json_fields'].add(c.name)

        for k, v in self.entity2model.items():
            if is_sqlalchemy_model(v):
                self.entity2model[k] = pypika.Table(v.__table__.name)

        self._phg_cache = None
        self.Session = sessionmaker(bind=self.db)

    def get_placeholder_generator(self) -> PlaceHolderGenerator:
        self._phg_cache = ':v{count}'
        return PlaceHolderGenerator(self._phg_cache, self.json_dumps_func)

    async def execute_sql(self, sql: str, phg: PlaceHolderGenerator):
        # https://stackoverflow.com/questions/52232979/sqlalchemy-rollback-when-exception
        import sqlalchemy
        session = self.Session()
        params = dict(zip([x[1:] for x in phg.keys], phg.values))

        try:
            ret: sqlalchemy.engine.cursor.CursorResult = session.execute(sql, params)
            session.commit()

            if sql.startswith('SELECT'):
                values = [x for x in ret.fetchall()]
                return SQLExecuteResult(None, values)
            else:
                if sql.startswith('INSERT INTO'):
                    return SQLExecuteResult(ret.lastrowid)
                else:
                    return SQLExecuteResult(ret.rowcount)
        except Exception as e:
            session.rollback()
            raise DBException(*e.args)
