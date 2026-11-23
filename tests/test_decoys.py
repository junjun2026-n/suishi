# 文件名称：test_decoys.py | 生成日期：2026-11-22 | 修改日期：2026-11-22
# 版本信息：v0.261115 | 作者：JUN
# 备注：本程序由AI辅助完成。用途：验证固定诱饵、模式持久化与引流关联；注意：使用隔离测试数据。
import json
from fastapi.testclient import TestClient
from app import create_apps
from decoys import CATALOG


def test_all_decoy_paths_and_waf_correlation(tmp_path):
    decoy,admin=create_apps(tmp_path,password='testing',trusted_proxies=['127.0.0.1/32'])
    client=TestClient(decoy,client=('127.0.0.1',1234));manage=TestClient(admin)
    assert manage.get('/api/decoys').status_code==401
    assert len(manage.get('/api/decoys',auth=('admin','testing')).json()['items'])==8
    for item in CATALOG:
        for path in item['paths']:
            response=client.get(path,headers={'X-Forwarded-For':'203.0.113.7','X-WAF-Rule':'test-rule','X-WAF-Request-ID':'trace-123'})
            assert response.status_code==200
            if 'application/json' in response.headers['content-type']:json.loads(response.text)
            assert 'default-src' in response.headers['content-security-policy']
            event=manage.get('/api/events?page_size=1',auth=('admin','testing')).json()['items'][0]
            assert event['scenario']==item['id'],path
            detail=manage.get('/api/events/'+str(event['id']),auth=('admin','testing')).json()
            assert detail['source_ip']=='203.0.113.7' and detail['request_id']=='trace-123'


def test_profiles_and_no_interpolation(tmp_path):
    decoy,admin=create_apps(tmp_path,password='testing')
    client,manage=TestClient(decoy),TestClient(admin)
    for item in CATALOG:
        settings={'profile':item['id'],'body_limit':65536,'read_timeout':10}
        assert manage.put('/api/settings',json=settings,auth=('admin','testing'),headers={'X-Suishi-Action':'settings'}).status_code==200
        response=client.post('/unknown',content='<script>unique-attacker-marker</script>')
        assert response.status_code==200 and 'unique-attacker-marker' not in response.text
        assert manage.get('/api/events?page_size=1',auth=('admin','testing')).json()['items'][0]['scenario']==item['id']
    _,restarted=create_apps(tmp_path,password='testing')
    assert TestClient(restarted).get('/api/settings',auth=('admin','testing')).json()['profile']=='files'
    response=manage.put('/api/settings',json={'profile':'invalid'},auth=('admin','testing'),headers={'X-Suishi-Action':'settings'})
    assert response.status_code==422
