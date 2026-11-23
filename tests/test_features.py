# ============================================================
# 文件名称：test_features.py
# 生成日期：2026-11-21
# 修改日期：2026-11-21
# 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。
# 文件功能用途：验证攻击特征识别、模拟响应、筛选和配置持久化。
# 注意事项：测试数据与实际采集数据隔离，特征命中不代表真实入侵。
# ============================================================
import hashlib
from fastapi.testclient import TestClient
from app import create_apps
from analysis import analyze

AUTH = ('admin', 'testing')


def test_detection():
    findings, severity = analyze('/?q=UNION%2520SELECT+1', '', 'sqlmap')
    assert severity == '高'
    assert {x['type'] for x in findings} == {'SQL 注入', '自动化扫描'}
    assert analyze('/products', '', 'Mozilla/5.0') == ([], '信息')
    for target in ['/?x=<script>alert(1)</script>', '/../../etc/passwd',
                   '/?url=http://169.254.169.254/latest', '/?x=;whoami']:
        assert analyze(target, '', '')[1] == '高'


def test_scenarios_filters_exports_and_sources(tmp_path):
    decoy, admin = create_apps(tmp_path, password='testing', trusted_proxies=[])
    client, manage = TestClient(decoy), TestClient(admin)
    assert 'name="username"' in client.get('/admin').text
    assert 'Invalid' in client.post('/admin', content='username=x').text
    assert client.get('/actuator/health').json()['status'] == 'UP'
    assert 'APP_ENV=staging' in client.get('/.env').text
    client.get('/?q=UNION%20SELECT%201')
    data = manage.get('/api/events?severity=高&page_size=1', auth=AUTH).json()
    assert data['total'] == 1
    event_id = data['items'][0]['id']
    detail = manage.get(f'/api/events/{event_id}', auth=AUTH).json()
    assert detail['findings'][0]['type'] == 'SQL 注入'
    assert detail['payload_sha256'] == hashlib.sha256(b'').hexdigest()
    exported = manage.get(f'/api/events/{event_id}/export', auth=AUTH)
    assert 'attachment' in exported.headers['content-disposition']
    assert exported.json() == detail
    sources = manage.get('/api/sources', auth=AUTH).json()['items']
    assert sources[0]['requests'] == 5 and sources[0]['high_risk'] == 1
    assert manage.get('/api/events?start=2026-01-01', auth=AUTH).status_code == 422
    assert manage.get('/api/stats', auth=AUTH).json()['attack_top']


def test_settings_persist_and_write_protection(tmp_path):
    decoy, admin = create_apps(tmp_path, password='testing')
    client, manage = TestClient(decoy), TestClient(admin)
    settings = {'profile': 'portal', 'body_limit': 1024, 'read_timeout': 2}
    assert manage.put('/api/settings', json=settings, auth=AUTH).status_code == 403
    assert manage.put('/api/settings', json=settings, auth=AUTH,
                      headers={'X-Suishi-Action': 'settings'}).status_code == 200
    assert 'name="username"' not in client.get('/admin').text
    assert client.post('/upload', content=b'x'*1025).status_code == 413
    _, restarted = create_apps(tmp_path, password='testing')
    assert TestClient(restarted).get('/api/settings', auth=AUTH).json() == settings
    assert manage.post('/api/retention', json={'before':'2999-01-01T00:00:00Z'},
                       auth=AUTH, headers={'X-Suishi-Action':'retention'}).status_code == 422
    assert manage.post('/api/retention', json={'before':'2020-01-01T00:00:00Z'},
                       auth=AUTH).status_code == 403
