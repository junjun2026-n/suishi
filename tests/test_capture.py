# 文件名称：test_capture.py | 生成/修改日期：2026-11-21 | 版本：v0.261115 | 作者：JUN
# 备注：本程序由AI辅助完成。验证引流、访问隔离及采集边界。
from fastapi.testclient import TestClient
from app import create_apps, MAX_BODY


def test_capture_and_access_boundary(tmp_path):
    decoy, admin = create_apps(tmp_path, password='test-password', trusted_proxies=['127.0.0.1/32'])
    business = TestClient(decoy, client=('127.0.0.1', 1234))
    management = TestClient(admin)
    assert management.get('/api/events').status_code == 401
    response = business.post('/login?a=1', content=b'username=example', headers={
        'X-Forwarded-For': '198.51.100.10', 'X-WAF-Rule': 'SQLI',
        'X-WAF-Request-ID': 'req-123', 'Authorization': 'secret'})
    assert response.status_code == 200
    auth = ('admin', 'test-password')
    item = management.get('/api/events', auth=auth).json()['items'][0]
    detail = management.get('/api/events/' + str(item['id']), auth=auth).json()
    assert detail['source_ip'] == '198.51.100.10'
    assert detail['rule'] == 'SQLI' and detail['request_id'] == 'req-123'
    assert detail['body_text'] == 'username=example'
    assert detail['headers']['authorization'] == '[已隐藏]'
    # The business listener must never expose management data.
    assert 'body_base64' not in business.get('/api/events').text
    assert management.get('/api/events?q=SQLI', auth=auth).json()['total'] == 1


def test_untrusted_forwarding_and_body_limit(tmp_path):
    decoy, admin = create_apps(tmp_path, password='test-password', trusted_proxies=[])
    business = TestClient(decoy, client=('198.51.100.20', 1234))
    assert business.post('/upload', content=b'x'*(MAX_BODY+1), headers={
        'X-Forwarded-For': '1.2.3.4', 'X-WAF-Rule': 'forged'}).status_code == 413
    data = TestClient(admin).get('/api/events/1', auth=('admin','test-password')).json()
    assert data['source_ip'] == '198.51.100.20' and data['rule'] == ''
    assert data['truncated'] == 1 and data['body_bytes'] == MAX_BODY
