# 文件名称：test_administration.py | 生成/修改日期：2026-11-21
# 版本信息：v0.261115 | 作者：JUN
# 备注：本程序由AI辅助完成。验证迁移、用户授权、不可删除管理员及会话撤销。
from fastapi.testclient import TestClient
from app import create_apps

AUTH = ('admin', 'testing')
HEADERS = {'X-Suishi-Action': 'administration'}


def test_users_permissions_sessions_and_logout(tmp_path):
    decoy, app = create_apps(tmp_path, password='testing')
    client = TestClient(app)
    assert client.get('/').url.path == '/login'
    viewer = {'username': 'reader', 'password': 'reader123!', 'role': 'viewer'}
    assert client.post('/api/users', auth=AUTH, headers=HEADERS, json=viewer).status_code == 200
    assert client.post('/api/users', auth=AUTH, headers=HEADERS, json=viewer).status_code == 409
    assert client.delete('/api/users/admin', auth=AUTH, headers=HEADERS).status_code == 403
    assert client.put('/api/users/admin', auth=AUTH, headers=HEADERS, json={**viewer, 'username': 'admin'}).status_code == 422
    assert client.get('/api/events', auth=('reader', 'reader123!')).status_code == 200
    for path in ('/api/users', '/api/database', '/api/forwarding'):
        assert client.get(path, auth=('reader', 'reader123!')).status_code == 403
    assert client.post('/api/simulations/run', auth=('reader', 'reader123!'), headers=HEADERS, json={'case_ids': ['benign']}).status_code == 403
    assert client.post('/api/login', headers={'X-Suishi-Action':'login'}, json={'username':'reader','password':'reader123!'}).status_code == 200
    token = client.cookies.get('suishi_session')
    assert client.get('/api/me').json()['username'] == 'reader'
    assert client.post('/api/logout', headers=HEADERS).url.path == '/login'
    assert client.get('/api/events').status_code == 401
    client.cookies.set('suishi_session', token)
    assert client.get('/api/events').status_code == 401
    client.cookies.clear()
    client.post('/api/login', headers={'X-Suishi-Action':'login'}, json={'username':'reader','password':'reader123!'})
    assert client.put('/api/users/reader', auth=AUTH, headers=HEADERS, json={**viewer,'enabled':False}).status_code == 200
    assert client.get('/api/events').status_code == 401
    assert client.get('/api/events', auth=('reader','reader123!')).status_code == 401


def test_database_migration_preserves_ids_config_and_users(tmp_path):
    decoy, app = create_apps(tmp_path, password='testing')
    business, client = TestClient(decoy), TestClient(app)
    business.post('/old-record', content='original')
    settings = {'profile': 'portal', 'body_limit': 1024, 'read_timeout': 2}
    client.put('/api/settings', auth=AUTH, headers={'X-Suishi-Action':'settings'}, json=settings)
    config = {'type':'sqlite','file':'new.db'}
    result = client.post('/api/database/initialize', auth=AUTH, headers=HEADERS, json=config)
    assert result.status_code == 200, result.text
    assert result.json()['migrated']['events'] == 1
    business.get('/new-record')
    assert client.get('/api/events', auth=AUTH).json()['total'] == 2
    assert client.get('/api/events/1', auth=AUTH).json()['body_text'] == 'original'
    assert client.get('/api/settings', auth=AUTH).json() == settings
    assert client.post('/api/database/initialize', auth=AUTH, headers=HEADERS, json={'type':'sqlite','file':'suishi.db'}).status_code == 409
    assert client.get('/api/events', auth=AUTH).json()['total'] == 2
    restart, again = create_apps(tmp_path, password='ignored-new-password')
    assert restart.state.database.config.file == 'new.db'
    assert TestClient(again).get('/api/events', auth=AUTH).json()['total'] == 2
    assert client.post('/api/database/test', auth=AUTH, headers=HEADERS, json={'type':'postgresql'}).status_code == 422
