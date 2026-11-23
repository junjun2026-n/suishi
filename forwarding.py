# ============================================================
# 文件名称：forwarding.py
# 生成日期：2026-11-21
# 修改日期：2026-11-21
# 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。
# 文件功能用途：实现日志格式化、持久转发队列和失败重试。
# 注意事项：UDP 发送不代表接收成功，队列有容量上限。
# ============================================================
import asyncio
import json
import socket
import string
import time
from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator
from typing import Literal


class ForwardConfig(BaseModel):
    model_config = {'extra': 'forbid'}
    enabled: bool = False
    host: str = Field(default='', max_length=253)
    port: int = Field(default=514, ge=1, le=65535)
    protocol: Literal['udp', 'tcp'] = 'udp'
    format: Literal['json', 'syslog', 'custom'] = 'json'
    template: str = Field(default='{time} {source_ip} {method} {path} {severity}', max_length=4096)
    include_body: bool = False

    @model_validator(mode='after')
    def validate_config(self):
        self.host = self.host.strip()
        if self.enabled and (not self.host or any(c.isspace() for c in self.host) or any(c in self.host for c in '/\\\x00')):
            raise ValueError('请填写有效接收服务器 IP 或主机名，不含协议或路径')
        if self.format == 'custom':
            allowed = {'id', 'time', 'source_ip', 'peer_ip', 'method', 'path', 'host', 'severity', 'rule', 'status', 'request_id', 'scenario', 'body_text', 'findings', 'simulation_run'}
            for _, field, spec, conversion in string.Formatter().parse(self.template):
                if field is not None and (field not in allowed or spec or conversion):
                    raise ValueError('自定义模板仅支持文档中的字段，不支持表达式或格式指令')
        return self


def encode_event(event, config):
    event = dict(event)
    for key in ('headers', 'findings'):
        if isinstance(event.get(key), str):
            event[key] = json.loads(event[key])
    if not config.include_body:
        event.pop('body_text', None)
        event.pop('body_base64', None)
    document = {'platform': 'suishi', 'type': 'honeypot_request', **event}
    if config.format == 'custom':
        fields = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v) for k, v in document.items()}
        fields.setdefault('body_text', '')
        message = config.template.format_map(fields)
    else:
        message = json.dumps(document, ensure_ascii=False, separators=(',', ':'))
        if config.format == 'syslog':
            stamp = event.get('time') or datetime.now(timezone.utc).isoformat()
            message = f'<134>1 {stamp} suishi suishi - honeypot - {message}'
    # One event per line; prevent payloads from injecting additional log records.
    return message.replace('\r', '\\r').replace('\n', '\\n').encode('utf-8')


def send_message(payload, config):
    if config.protocol == 'udp' and len(payload) > 60000:
        raise ValueError('UDP 日志超过 60000 字节，请改用 TCP 或关闭正文转发')
    if config.protocol == 'tcp':
        with socket.create_connection((config.host, config.port), timeout=3) as sock:
            sock.settimeout(3)
            sock.sendall(payload + b'\n')
    else:
        addresses = socket.getaddrinfo(config.host, config.port, type=socket.SOCK_DGRAM)
        family, kind, proto, _, address = addresses[0]
        with socket.socket(family, kind, proto) as sock:
            sock.settimeout(3)
            sock.sendto(payload, address)


class Forwarder:
    def __init__(self, connect):
        self.connect = connect

    def config(self):
        with self.connect() as db:
            row = db.execute('SELECT value FROM forwarding_config WHERE id=1').fetchone()
        return ForwardConfig.model_validate_json(row[0]) if row else ForwardConfig()

    def save(self, value):
        with self.connect() as db:
            db.execute('INSERT INTO forwarding_config VALUES(1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value', (value.model_dump_json(),))
        return value.model_dump()

    def enqueue(self, db, event_id):
        row = db.execute('SELECT value FROM forwarding_config WHERE id=1').fetchone()
        config = ForwardConfig.model_validate_json(row[0]) if row else ForwardConfig()
        if not config.enabled:
            return
        # Bound storage; honeypot collection must continue during receiver outages.
        if db.execute('SELECT COUNT(*) FROM forwarding_queue').fetchone()[0] >= 10000:
            db.execute("UPDATE forwarding_state SET dropped=dropped+1,last_error='转发队列已满，新日志仅保存在本地' WHERE id=1")
            return
        event = dict(db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone())
        db.execute('INSERT INTO forwarding_queue(payload) VALUES(?)', (encode_event(event, config),))

    def status(self):
        with self.connect() as db:
            result = dict(db.execute('SELECT sent,dropped,last_error,last_sent FROM forwarding_state WHERE id=1').fetchone())
            result['pending'] = db.execute('SELECT COUNT(*) FROM forwarding_queue').fetchone()[0]
        return result

    def deliver_one(self):
        config = self.config()
        if not config.enabled:
            return False
        with self.connect() as db:
            row = db.execute('SELECT * FROM forwarding_queue WHERE next_try<=? ORDER BY id LIMIT 1', (time.time(),)).fetchone()
        if not row:
            return False
        try:
            send_message(row['payload'], config)
        except Exception as error:
            with self.connect() as db:
                db.execute('UPDATE forwarding_queue SET attempts=attempts+1,next_try=? WHERE id=?', (time.time()+min(300, 2**min(row['attempts']+1, 8)), row['id']))
                db.execute('UPDATE forwarding_state SET last_error=? WHERE id=1', (str(error)[:500],))
        else:
            with self.connect() as db:
                db.execute('DELETE FROM forwarding_queue WHERE id=?', (row['id'],))
                db.execute("UPDATE forwarding_state SET sent=sent+1,last_error='',last_sent=? WHERE id=1", (datetime.now(timezone.utc).isoformat(),))
        return True

    async def worker(self):
        while True:
            try:
                busy = await asyncio.to_thread(self.deliver_one)
            except Exception:
                busy = False
            await asyncio.sleep(0.02 if busy else 1)
