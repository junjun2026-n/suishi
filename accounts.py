# 文件名称：accounts.py | 生成/修改日期：2026-11-21
# 版本信息：v0.261115 | 作者：JUN
# 备注：本程序由AI辅助完成。用户、密码哈希与可撤销登录会话；admin 不允许删除或禁用。
import hashlib
import hmac
import secrets
import time
import threading
from collections import OrderedDict

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Literal


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 300000).hex()
    return f'pbkdf2_sha256${salt}${digest}'


def verify(password, encoded):
    try:
        _, salt, digest = encoded.split('$')
        return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 300000).hex(), digest)
    except (ValueError, AttributeError):
        return False


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserInput(BaseModel):
    username: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,64}$')
    password: str = Field(default='', max_length=256)
    role: Literal['admin', 'viewer'] = 'viewer'
    enabled: bool = True


class Accounts:
    def __init__(self, connect, password):
        self.connect = connect
        self.dummy_hash = password_hash(secrets.token_hex(16))
        self.failures = OrderedDict()
        self.lock = threading.Lock()
        with connect() as db:
            if not db.execute("SELECT username FROM users WHERE username='admin'").fetchone():
                db.execute('INSERT INTO users(username,password_hash,role,enabled) VALUES(?,?,?,?)',
                           ('admin', password_hash(password), 'admin', 1))

    def check(self, username, password, peer):
        with self.lock:
            attempts, until = self.failures.get(peer, (0, 0))
            if until > time.time() and attempts >= 10:
                raise HTTPException(429, '登录尝试过多，请十分钟后重试')
        with self.connect() as db:
            user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        valid = verify(password, user['password_hash'] if user else self.dummy_hash)
        if not user or not valid or not user['enabled']:
            with self.lock:
                self.failures[peer] = ((attempts if until > time.time() else 0)+1, time.time()+600)
                self.failures.move_to_end(peer)
                if len(self.failures) > 10000:
                    self.failures.popitem(last=False)
            raise HTTPException(401, '用户名或密码错误')
        with self.lock:
            self.failures.pop(peer, None)
        return user

    def identity(self, request, credentials=None):
        if credentials:
            return self.check(credentials.username, credentials.password, request.client.host if request.client else '')
        token = request.cookies.get('suishi_session', '')
        with self.connect() as db:
            return db.execute('SELECT users.* FROM users JOIN sessions ON users.username=sessions.username '
                              'WHERE sessions.token_hash=? AND sessions.expires>? AND users.enabled=1',
                              (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone() if token else None


def register_accounts(app, accounts, root):
    connect = accounts.connect

    @app.get('/login')
    def login_page():
        return HTMLResponse((root / 'static' / 'login.html').read_text('utf-8'), headers={'Cache-Control': 'no-store'})

    @app.post('/api/login')
    def login(value: Login, request: Request):
        if request.headers.get('x-suishi-action') != 'login':
            raise HTTPException(403, '缺少操作标识')
        user = accounts.check(value.username, value.password, request.client.host if request.client else '')
        token = secrets.token_urlsafe(32)
        with connect() as db:
            db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user['username'], time.time()+28800))
        response = RedirectResponse('/', status_code=303)
        response.set_cookie('suishi_session', token, httponly=True, samesite='strict', secure=request.url.scheme == 'https', max_age=28800)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.post('/api/logout')
    def logout(request: Request):
        if not request.headers.get('x-suishi-action'):
            raise HTTPException(403, '缺少操作标识')
        token = request.cookies.get('suishi_session', '')
        with connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))
        response = RedirectResponse('/login', status_code=303)
        response.delete_cookie('suishi_session')
        return response

    @app.get('/api/me')
    def me(request: Request):
        return {key: request.state.user[key] for key in ('username', 'role')}

    @app.get('/api/users')
    def users():
        with connect() as db:
            return {'items': db.execute('SELECT username,role,enabled FROM users ORDER BY username').fetchall()}

    def save(value, creating):
        if value.username == 'admin' and (not value.enabled or value.role != 'admin'):
            raise HTTPException(422, '默认 admin 用户不能禁用或降权')
        if (creating or value.password) and len(value.password) < 8:
            raise HTTPException(422, '密码至少 8 位')
        with connect() as db:
            existing = db.execute('SELECT username FROM users WHERE username=?', (value.username,)).fetchone()
            if creating and existing:
                raise HTTPException(409, '用户名已存在')
            if not creating and not existing:
                raise HTTPException(404, '用户不存在')
            if creating:
                db.execute('INSERT INTO users VALUES(?,?,?,?)', (value.username, password_hash(value.password), value.role, int(value.enabled)))
            else:
                db.execute('UPDATE users SET role=?,enabled=? WHERE username=?', (value.role, int(value.enabled), value.username))
                if value.password:
                    db.execute('UPDATE users SET password_hash=? WHERE username=?', (password_hash(value.password), value.username))
                db.execute('DELETE FROM sessions WHERE username=?', (value.username,))
        return {'message': '用户已保存'}

    @app.post('/api/users')
    def create_user(value: UserInput):
        return save(value, True)

    @app.put('/api/users/{username}')
    def update_user(username: str, value: UserInput):
        if username != value.username:
            raise HTTPException(422, '用户名不可修改')
        return save(value, False)

    @app.delete('/api/users/{username}')
    def delete_user(username: str):
        if username == 'admin':
            raise HTTPException(403, '默认 admin 用户不可删除')
        with connect() as db:
            db.execute('DELETE FROM sessions WHERE username=?', (username,))
            db.execute('DELETE FROM users WHERE username=?', (username,))
        return {'message': '用户已删除'}
