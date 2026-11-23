# ============================================================
# 文件名称：database.py
# 生成日期：2026-11-21
# 修改日期：2026-11-21
# 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。
# 文件功能用途：实现 SQLite、PostgreSQL、MySQL 连接、初始化和数据迁移。
# 注意事项：数据库凭据保存在运行目录，迁移不得覆盖已有目标数据。
# ============================================================
import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, Text,
                        LargeBinary, Float, inspect, text, select, func)
from sqlalchemy.engine import URL
from sqlalchemy.dialects.mysql import LONGTEXT


def log_text():
    return Text().with_variant(LONGTEXT(), 'mysql')


class DatabaseConfig(BaseModel):
    model_config = {'extra': 'forbid'}
    type: str = 'sqlite'
    file: str = 'suishi.db'
    host: str = ''
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = ''
    username: str = ''
    password: str = ''

    @model_validator(mode='after')
    def check(self):
        if self.type not in ('sqlite', 'postgresql', 'mysql'):
            raise ValueError('仅支持 SQLite、PostgreSQL、MySQL')
        if self.type != 'sqlite' and not all((self.host.strip(), self.database.strip(), self.username.strip())):
            raise ValueError('请填写数据库主机、数据库名和用户名')
        if self.type == 'sqlite' and (not self.file or Path(self.file).name != self.file):
            raise ValueError('SQLite 文件请使用数据目录内的文件名')
        return self


metadata = MetaData()
events = Table('events', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    *[Column(name, log_text(), nullable=False) for name in ['time']],
    *[Column(name, log_text()) for name in ['peer_ip', 'source_ip', 'method', 'path', 'host', 'rule',
       'request_id', 'headers', 'body_base64', 'body_text', 'findings', 'severity', 'scenario',
       'payload_sha256', 'user_agent', 'simulation_run']],
    *[Column(name, Integer) for name in ['body_bytes', 'truncated', 'status', 'read_timed_out']])
settings = Table('settings', metadata, Column('id', Integer, primary_key=True), Column('value', Text, nullable=False))
Table('simulation_runs', metadata, Column('id', String(64), primary_key=True),
      Column('time', Text, nullable=False), Column('status', Text, nullable=False), Column('results', log_text(), nullable=False))
Table('forwarding_config', metadata, Column('id', Integer, primary_key=True), Column('value', Text, nullable=False))
Table('forwarding_queue', metadata, Column('id', Integer, primary_key=True, autoincrement=True),
      Column('payload', LargeBinary(length=2097152), nullable=False),
      Column('attempts', Integer, server_default='0'), Column('next_try', Float(53), server_default='0'))
Table('forwarding_state', metadata, Column('id', Integer, primary_key=True),
      Column('sent', Integer, server_default='0'), Column('dropped', Integer, server_default='0'),
      Column('last_error', Text), Column('last_sent', Text))
Table('users', metadata, Column('username', String(64), primary_key=True),
      Column('password_hash', Text, nullable=False), Column('role', String(16), nullable=False),
      Column('enabled', Integer, nullable=False, server_default='1'))
Table('sessions', metadata, Column('token_hash', String(64), primary_key=True),
      Column('username', String(64), nullable=False), Column('expires', Float(53), nullable=False))


def engine_for(config, directory):
    if config.type == 'sqlite':
        url = URL.create('sqlite', database=str(Path(directory) / config.file))
        options = {'connect_args': {'timeout': 15, 'check_same_thread': False}}
    else:
        url = URL.create('postgresql+psycopg' if config.type == 'postgresql' else 'mysql+pymysql',
                         username=config.username, password=config.password, host=config.host,
                         port=config.port, database=config.database,
                         query={'charset': 'utf8mb4'} if config.type == 'mysql' else {})
        options = {'connect_args': {'connect_timeout': 5}, 'pool_pre_ping': True}
    return create_engine(url, **options)


def initialize(engine):
    metadata.create_all(engine)
    # Preserve older SQLite databases and add capture analysis columns.
    if engine.dialect.name == 'sqlite':
        with engine.begin() as db:
            existing = {c['name'] for c in inspect(engine).get_columns('events')}
            for column in events.columns:
                if column.name not in existing:
                    default = '0' if isinstance(column.type, Integer) else "'[]'" if column.name == 'findings' else "''"
                    db.execute(text(f'ALTER TABLE events ADD COLUMN {column.name} {column.type} DEFAULT {default}'))
            db.execute(text('PRAGMA journal_mode=WAL'))
    with engine.begin() as db:
        if db.execute(text('SELECT COUNT(*) FROM forwarding_state')).scalar() == 0:
            db.execute(text("INSERT INTO forwarding_state(id,sent,dropped,last_error,last_sent) VALUES(1,0,0,'','')"))


class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Result:
    def __init__(self, result, lastrowid=None):
        self.result = result
        self.lastrowid = lastrowid
        self.rowcount = result.rowcount

    def fetchone(self):
        row = self.result.fetchone()
        return Row(row._mapping) if row is not None else None

    def fetchall(self):
        return [Row(row._mapping) for row in self.result.fetchall()]


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, args=()):
        # Application queries use positional parameters; SQLAlchemy binds each value.
        parts = sql.split('?')
        bound = ''.join(part + (f':p{i}' if i < len(parts)-1 else '') for i, part in enumerate(parts))
        dialect = self.connection.dialect.name
        # PostgreSQL text cannot store NUL; body_base64 retains original bytes.
        parameters = {f'p{i}': value.replace('\x00', '\\u0000') if dialect == 'postgresql' and isinstance(value, str) else value for i, value in enumerate(args)}
        if dialect == 'mysql' and 'ON CONFLICT(id) DO UPDATE SET value=excluded.value' in bound:
            bound = bound.replace('ON CONFLICT(id) DO UPDATE SET value=excluded.value', 'ON DUPLICATE KEY UPDATE value=VALUES(value)')
        inserted = sql.lstrip().upper().startswith(('INSERT INTO EVENTS(', 'INSERT INTO FORWARDING_QUEUE('))
        if inserted and dialect == 'postgresql':
            result = self.connection.execute(text(bound + ' RETURNING id'), parameters)
            identifier = result.scalar_one()
        else:
            result = self.connection.execute(text(bound), parameters)
            identifier = getattr(result, 'lastrowid', None) if inserted else None
        return Result(result, identifier)


class Database:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.config_path = self.directory / 'database.json'
        self.config = DatabaseConfig.model_validate_json(self.config_path.read_text('utf-8')) if self.config_path.exists() else DatabaseConfig()
        self.lock = threading.RLock()
        self.engine = engine_for(self.config, self.directory)
        initialize(self.engine)

    @contextmanager
    def connect(self):
        # Switching holds this lock until all old transactions have finished.
        with self.lock:
            with self.engine.begin() as connection:
                yield Connection(connection)

    def test(self, config):
        engine = engine_for(config, self.directory)
        try:
            with engine.connect() as db:
                db.execute(text('SELECT 1'))
        finally:
            engine.dispose()

    def switch(self, config, migrate=True):
        with self.lock:
            target = engine_for(config, self.directory)
            if target.url == self.engine.url:
                target.dispose()
                initialize(self.engine)
                return {'message': '当前数据库已初始化，保留现有数据', 'migrated': {}}
            try:
                initialize(target)
                counts = {}
                with target.begin() as destination:
                    # Never silently overwrite a pre-existing platform database.
                    if any(destination.execute(select(func.count()).select_from(table)).scalar() for table in metadata.sorted_tables if table.name != 'forwarding_state'):
                        raise ValueError('目标数据库已有平台数据；为防止覆盖，请使用空数据库')
                    if migrate:
                        with self.engine.connect() as source:
                            for table in metadata.sorted_tables:
                                if table.name == 'forwarding_state':
                                    destination.execute(table.delete())
                                count = 0
                                result = source.execute(select(table)).mappings()
                                while batch := result.fetchmany(200):
                                    destination.execute(table.insert(), [dict(row) for row in batch])
                                    count += len(batch)
                                counts[table.name] = count
                        if target.dialect.name == 'postgresql':
                            for name in ('events', 'forwarding_queue'):
                                destination.execute(text(f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), COALESCE(MAX(id),1), COUNT(*)>0) FROM {name}"))
                temporary = self.config_path.with_suffix('.tmp')
                temporary.write_text(config.model_dump_json(indent=2), encoding='utf-8')
                if os.name != 'nt':
                    temporary.chmod(0o600)
                temporary.replace(self.config_path)
                previous = self.engine
                self.engine, self.config = target, config
                previous.dispose()
                return {'message': '数据库迁移并切换成功', 'migrated': counts}
            except Exception:
                target.dispose()
                raise


def register_database(app, database, root):
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    @app.get('/administration.js')
    def script():
        return FileResponse(root / 'static' / 'administration.js', media_type='text/javascript', headers={'Cache-Control': 'no-store'})

    @app.get('/api/database')
    def configuration():
        return database.config.model_dump()

    @app.post('/api/database/test')
    def test(value: DatabaseConfig):
        try:
            database.test(value)
            return {'message': '数据库连接成功'}
        except Exception as error:
            # Driver errors may include connection details; return type only.
            raise HTTPException(422, f'数据库连接失败（{type(error).__name__}），请检查地址、账号、密码及数据库权限')

    @app.post('/api/database/initialize')
    def initialize_database(value: DatabaseConfig):
        try:
            return database.switch(value, migrate=True)
        except ValueError as error:
            raise HTTPException(409, str(error))
        except Exception as error:
            raise HTTPException(422, f'初始化或迁移失败（{type(error).__name__}）；当前连接保持原数据库，请检查连接及建表权限')
