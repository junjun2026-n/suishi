# ============================================================
# 文件名称：app.py
# 生成日期：2026-11-21
# 修改日期：2026-11-21
# 版本信息：v0.261115
# 作    者：JUN
# 备    注：本程序由AI辅助完成。
#           文件功能：邃室蜜罐请求接收、日志存储与管理接口。
#           注意事项：请求内容仅存储分析，不执行；管理端口限制受信网络访问。
# ============================================================
import base64
import ipaddress
import json
import os
import secrets
import hashlib
import anyio
import asyncio
import httpx
from contextvars import ContextVar
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, RedirectResponse
from pydantic import BaseModel, Field
from typing import Literal
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.concurrency import run_in_threadpool
from analysis import analyze, respond
from simulations import CASES
from forwarding import Forwarder, ForwardConfig, encode_event, send_message
from database import Database, register_database
from accounts import Accounts, register_accounts

ROOT = Path(__file__).resolve().parent
MAX_BODY = 64 * 1024
security = HTTPBasic(auto_error=False)


class Settings(BaseModel):
    profile: Literal['adaptive', 'portal'] = 'adaptive'
    body_limit: int = Field(default=MAX_BODY, ge=1024, le=1048576)
    read_timeout: int = Field(default=10, ge=1, le=30)


class Retention(BaseModel):
    before: datetime


class SimulationInput(BaseModel):
    model_config = {'extra': 'forbid'}
    case_ids: list[str] = Field(min_length=1, max_length=12)


def create_apps(data_dir=None, password=None, trusted_proxies=None):
    directory = Path(data_dir or os.getenv('SUISHI_DATA_DIR', str(ROOT / 'runtime')))
    directory.mkdir(parents=True, exist_ok=True)
    db_path = directory / 'suishi.db'
    password = password or os.getenv('SUISHI_ADMIN_PASSWORD')
    if not password:
        password_file = directory / 'admin-password.txt'
        if not password_file.exists():
            with password_file.open('x', encoding='utf-8') as output:
                output.write(secrets.token_urlsafe(24))
            if os.name != 'nt':
                password_file.chmod(0o600)
        password = password_file.read_text(encoding='utf-8').strip()
    proxies = [ipaddress.ip_network(s.strip()) for s in (
        trusted_proxies if trusted_proxies is not None else
        os.getenv('SUISHI_TRUSTED_PROXIES', '127.0.0.1/32,::1/128').split(',')) if s.strip()]

    database = Database(directory)
    connect = database.connect
    accounts = Accounts(connect, password)
    with connect() as db:
        db.execute("UPDATE simulation_runs SET status='interrupted' WHERE status='running'")

    simulation_context = ContextVar('simulation_run', default='')
    simulation_lock = asyncio.Lock()

    def get_settings():
        with connect() as db:
            row = db.execute('SELECT value FROM settings WHERE id=1').fetchone()
        return Settings.model_validate_json(row[0]) if row else Settings()

    def authenticated(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
        if request.url.path in ('/login', '/api/login', '/api/logout'):
            return
        user = accounts.identity(request, credentials)
        if not user:
            raise HTTPException(401, 'Login required')
        request.state.user = user
        admin_area = request.url.path.startswith(('/api/database', '/api/users', '/api/forwarding'))
        if user['role'] != 'admin' and (request.method not in ('GET', 'HEAD') or admin_area):
            raise HTTPException(403, 'Administrator permission required')
        if request.method not in ('GET', 'HEAD') and not request.headers.get('x-suishi-action'):
            raise HTTPException(403, 'Missing action header')

    forwarder = Forwarder(connect)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(forwarder.worker())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    decoy = FastAPI(title='Web Service', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    decoy.state.forwarder = forwarder
    decoy.state.database = database
    management = FastAPI(title='邃室管理', docs_url=None, redoc_url=None, openapi_url=None,
                         dependencies=[Depends(authenticated)])
    register_accounts(management, accounts, ROOT)
    register_database(management, database, ROOT)

    @management.middleware('http')
    async def management_headers(request, call_next):
        if request.url.path == '/' and not request.headers.get('authorization') and not await run_in_threadpool(accounts.identity, request):
            return RedirectResponse('/login', status_code=303)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    def insert(values):
        with connect() as db:
            cursor = db.execute('''INSERT INTO events(time,peer_ip,source_ip,method,path,host,rule,
                request_id,headers,body_base64,body_text,body_bytes,truncated,status,
                findings,severity,scenario,payload_sha256,user_agent,read_timed_out,simulation_run)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', values)
            forwarder.enqueue(db, cursor.lastrowid)
            return cursor.lastrowid

    @decoy.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'])
    async def capture(request: Request, path: str):
        peer = request.client.host if request.client else ''
        trusted = False
        try:
            trusted = any(ipaddress.ip_address(peer) in net for net in proxies)
        except ValueError:
            pass
        source = peer
        if trusted:
            try:
                source = str(ipaddress.ip_address(request.headers.get('x-forwarded-for', '').split(',')[0].strip()))
            except ValueError:
                pass
        body = bytearray()
        truncated = False
        read_timed_out = False
        settings = await run_in_threadpool(get_settings)
        try:
            with anyio.fail_after(settings.read_timeout):
                async for chunk in request.stream():
                    remaining = settings.body_limit - len(body)
                    body.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        truncated = True
                        break
        except TimeoutError:
            read_timed_out = True
        hidden = {'authorization', 'proxy-authorization', 'cookie', 'set-cookie'}
        headers = {k: ('[已隐藏]' if k.lower() in hidden else v[:4096]) for k, v in request.headers.items()}
        rule = request.headers.get('x-waf-rule', '')[:512] if trusted else ''
        request_id = request.headers.get('x-waf-request-id', '')[:256] if trusted else ''
        target = request.url.path + ('?' + request.url.query if request.url.query else '')
        status = 408 if read_timed_out else 413 if truncated else 200
        user_agent = request.headers.get('user-agent', '')[:2048]
        findings, severity = analyze(target, body.decode('utf-8', errors='replace'), user_agent, rule)
        scenario, content, media_type = respond(request.url.path, request.method, settings.profile)
        if status != 200:
            content, media_type = '<h1>Request rejected</h1>', 'text/html'
        run_id = simulation_context.get()
        event_id = await run_in_threadpool(insert, (
            datetime.now(timezone.utc).isoformat(), peer, source, request.method,
            target[:8192], request.headers.get('host', '')[:512], rule, request_id,
            json.dumps(headers, ensure_ascii=False), base64.b64encode(body).decode(),
            body.decode('utf-8', errors='replace'), len(body), int(truncated), status,
            json.dumps(findings, ensure_ascii=False), severity, scenario,
            hashlib.sha256(body).hexdigest(), user_agent, int(read_timed_out), run_id))
        response_headers = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                            'Content-Security-Policy': "default-src 'none'; form-action 'self'; frame-ancestors 'none'"}
        if run_id:
            response_headers['X-Suishi-Event-ID'] = str(event_id)
        return Response(content, status_code=status, media_type=media_type,
                        headers=response_headers)

    @management.get('/')
    def index():
        return FileResponse(ROOT / 'static' / 'index.html', headers={'Cache-Control': 'no-store'})

    @management.get('/simulation.js')
    def simulation_script():
        return FileResponse(ROOT / 'static' / 'simulation.js', media_type='text/javascript',
                            headers={'Cache-Control': 'no-store'})

    @management.get('/settings.js')
    def settings_script():
        return FileResponse(ROOT / 'static' / 'settings.js', media_type='text/javascript',
                            headers={'Cache-Control': 'no-store'})

    @management.get('/forwarding.js')
    def forwarding_script():
        return FileResponse(ROOT / 'static' / 'forwarding.js', media_type='text/javascript',
                            headers={'Cache-Control': 'no-store'})

    @management.get('/api/forwarding')
    def forwarding_config():
        return forwarder.config().model_dump()

    @management.get('/api/forwarding/status')
    def forwarding_status():
        return forwarder.status()

    @management.put('/api/forwarding')
    def forwarding_save(value: ForwardConfig, request: Request):
        if request.headers.get('x-suishi-action') != 'forwarding':
            raise HTTPException(403, '缺少操作标识')
        return forwarder.save(value)

    @management.post('/api/forwarding/test')
    def forwarding_test(request: Request):
        if request.headers.get('x-suishi-action') != 'forwarding':
            raise HTTPException(403, '缺少操作标识')
        config = forwarder.config()
        if not config.enabled:
            raise HTTPException(422, '请先启用并保存日志转发配置')
        event = {key: '' for key in ('id', 'peer_ip', 'source_ip', 'method', 'path', 'host', 'severity', 'rule', 'status', 'request_id', 'scenario', 'simulation_run')}
        event.update(time=datetime.now(timezone.utc).isoformat(), findings=[], scenario='forwarding_test', path='/forwarding-test', method='TEST')
        try:
            send_message(encode_event(event, config), config)
        except Exception as error:
            raise HTTPException(502, str(error)[:500])
        return {'message': '测试日志已发送，请在接收服务器确认。UDP 无接收确认机制。'}

    @management.get('/api/simulations/cases')
    def simulation_cases():
        return {'items': CASES, 'target': '本机蜜罐内部回放', 'max_requests': 12}

    @management.get('/api/simulations/runs')
    def simulation_runs():
        with connect() as db:
            rows = db.execute('SELECT * FROM simulation_runs ORDER BY time DESC LIMIT 30').fetchall()
        return {'items': [{**dict(row), 'results': json.loads(row['results'])} for row in rows]}

    @management.post('/api/simulations/run')
    async def simulate(value: SimulationInput, request: Request):
        if request.headers.get('x-suishi-action') != 'simulation':
            raise HTTPException(403, '缺少操作标识')
        selected = list(dict.fromkeys(value.case_ids))
        catalog = {case['id']: case for case in CASES}
        if any(case_id not in catalog for case_id in selected):
            raise HTTPException(422, '包含未知模拟场景')
        if simulation_lock.locked():
            raise HTTPException(409, '已有模拟任务正在运行')
        async with simulation_lock:
            run_id = secrets.token_hex(12)
            timestamp = datetime.now(timezone.utc).isoformat()
            with connect() as db:
                db.execute('INSERT INTO simulation_runs VALUES (?,?,?,?)', (run_id, timestamp, 'running', '[]'))
            results = []
            token = simulation_context.set(run_id)
            try:
                # In-process ASGI transport: no sockets, DNS or user-selected destination.
                transport = httpx.ASGITransport(app=decoy, client=('127.0.0.1', 0))
                async with httpx.AsyncClient(transport=transport, base_url='http://simulation.invalid',
                                            follow_redirects=False) as client:
                    with anyio.fail_after(30):
                        for case_id in selected:
                            case = catalog[case_id]
                            response = await client.request(case['method'], case['path'], content=case['body'], headers={
                                'User-Agent': case.get('user_agent', 'suishi-simulation/1.0'),
                                'Content-Type': case.get('content_type', 'text/plain; charset=utf-8')})
                            event_id = int(response.headers['x-suishi-event-id'])
                            event = await run_in_threadpool(detail, event_id)
                            detected = [finding['type'] for finding in event['findings']]
                            passed = (case['expected'] in detected if case['expected'] else not detected) and response.status_code == 200
                            results.append({'case_id': case_id, 'name': case['name'], 'event_id': event_id,
                                            'expected': case['expected'], 'detected': detected,
                                            'status': response.status_code, 'passed': passed})
                            await asyncio.sleep(0.1)
                state = 'completed'
            except Exception:
                state = 'failed'
            finally:
                simulation_context.reset(token)
                with connect() as db:
                    db.execute('UPDATE simulation_runs SET status=?,results=? WHERE id=?',
                               (locals().get('state', 'interrupted'), json.dumps(results, ensure_ascii=False), run_id))
            return {'id': run_id, 'time': timestamp, 'status': state, 'results': results}

    @management.get('/api/events')
    def events(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
               q: str = Query('', max_length=200), source_ip: str = Query('', max_length=64),
               severity: Literal['', '高', '中', '低', '信息'] = '',
               traffic: Literal['all', 'real', 'simulation'] = 'all',
               start: datetime | None = None, end: datetime | None = None):
        clauses = ['(source_ip LIKE ? OR path LIKE ? OR rule LIKE ?)'] if q else []
        args = ['%' + q + '%'] * 3 if q else []
        if traffic != 'all':
            clauses.append("simulation_run != ''" if traffic == 'simulation' else "simulation_run = ''")
        for column, value in [('source_ip', source_ip), ('severity', severity)]:
            if value:
                clauses.append(column + '=?')
                args.append(value)
        for op, value in [('>=', start), ('<=', end)]:
            if value:
                if value.tzinfo is None:
                    raise HTTPException(422, '时间必须带时区')
                clauses.append('time' + op + '?')
                args.append(value.astimezone(timezone.utc).isoformat())
        where = 'WHERE ' + ' AND '.join(clauses) if clauses else ''
        with connect() as db:
            total = db.execute('SELECT COUNT(*) FROM events ' + where, args).fetchone()[0]
            rows = db.execute('SELECT id,time,source_ip,method,path,host,rule,status,truncated,severity,scenario,simulation_run FROM events '
                              + where + ' ORDER BY id DESC LIMIT ? OFFSET ?',
                              [*args, page_size, (page - 1) * page_size]).fetchall()
        return {'total': total, 'page': page, 'page_size': page_size, 'items': [dict(row) for row in rows]}

    @management.get('/api/events/{event_id}')
    def detail(event_id: int):
        with connect() as db:
            row = db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
        if row is None:
            raise HTTPException(404, '记录不存在')
        result = dict(row)
        result['headers'] = json.loads(result['headers'])
        result['findings'] = json.loads(result['findings'])
        return result

    @management.get('/api/events/{event_id}/export')
    def export(event_id: int):
        result = detail(event_id)
        return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type='application/json',
                        headers={'Content-Disposition': f'attachment; filename="suishi-event-{event_id}.json"',
                                 'Cache-Control': 'no-store'})

    @management.get('/api/settings')
    def configuration():
        return get_settings().model_dump()

    @management.put('/api/settings')
    def save_settings(value: Settings, request: Request):
        # Do not permit cross-site writes using a browser's cached Basic credentials.
        if request.headers.get('x-suishi-action') != 'settings':
            raise HTTPException(403, '缺少操作标识')
        with connect() as db:
            db.execute('INSERT INTO settings VALUES (1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value',
                       (value.model_dump_json(),))
        return value.model_dump()

    @management.post('/api/retention')
    def retention(value: Retention, request: Request):
        if request.headers.get('x-suishi-action') != 'retention':
            raise HTTPException(403, '缺少操作标识')
        if value.before.tzinfo is None or value.before >= datetime.now(timezone.utc):
            raise HTTPException(422, '请提供带时区的历史截止时间')
        with connect() as db:
            count = db.execute('DELETE FROM events WHERE time < ?',
                               (value.before.astimezone(timezone.utc).isoformat(),)).rowcount
        return {'deleted': count}

    @management.get('/api/sources')
    def sources():
        with connect() as db:
            rows = db.execute('''SELECT source_ip,COUNT(*) requests,MIN(time) first_seen,MAX(time) last_seen,
                COUNT(DISTINCT path) paths,SUM(CASE WHEN severity='高' THEN 1 ELSE 0 END) high_risk
                FROM events GROUP BY source_ip ORDER BY requests DESC,source_ip''').fetchall()
        return {'items': [dict(row) for row in rows]}

    @management.get('/api/stats')
    def stats():
        with connect() as db:
            total = db.execute('SELECT COUNT(*) AS total,COUNT(DISTINCT source_ip) AS sources FROM events').fetchone()
            top = db.execute('SELECT source_ip,COUNT(*) count FROM events GROUP BY source_ip ORDER BY count DESC LIMIT 5').fetchall()
            risks = db.execute('SELECT severity,COUNT(*) count FROM events GROUP BY severity').fetchall()
            scenarios = db.execute('SELECT scenario,COUNT(*) count FROM events GROUP BY scenario ORDER BY count DESC LIMIT 5').fetchall()
            attacks = db.execute("SELECT findings FROM events WHERE findings != '[]' ORDER BY id DESC LIMIT 5000").fetchall()
        counts = {}
        for row in attacks:
            for finding in json.loads(row[0]):
                counts[finding['type']] = counts.get(finding['type'], 0) + 1
        return {'total': total[0], 'sources': total[1], 'top_ips': [dict(row) for row in top],
                'risks': [dict(row) for row in risks], 'scenarios': [dict(row) for row in scenarios],
                'attack_top': sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5],
                'attack_sample_limit': 5000}

    return decoy, management
