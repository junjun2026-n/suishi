# 文件名称：test_simulations.py
# 生成日期：2026-11-21 | 修改日期：2026-11-21 | 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。验证攻击模拟完整回放、访问控制及日志关联。
from fastapi.testclient import TestClient
from app import create_apps
from simulations import CASES


def test_simulation_suite(tmp_path):
    _, management = create_apps(tmp_path, password='testing')
    client = TestClient(management)
    payload = {'case_ids': [case['id'] for case in CASES]}
    headers = {'X-Suishi-Action': 'simulation'}
    auth = ('admin', 'testing')
    assert client.get('/api/simulations/cases').status_code == 401
    assert client.post('/api/simulations/run', json=payload, auth=auth).status_code == 403
    response = client.post('/api/simulations/run', json=payload, headers=headers, auth=auth)
    assert response.status_code == 200
    result = response.json()
    assert result['status'] == 'completed'
    assert len(result['results']) == 12
    assert all(row['passed'] for row in result['results']), result
    rows = client.get('/api/events?traffic=simulation', auth=auth).json()
    assert rows['total'] == 12
    assert all(row['simulation_run'] == result['id'] for row in rows['items'])
    assert client.get('/api/events?traffic=real', auth=auth).json()['total'] == 0
    for row in result['results']:
        detail = client.get(f"/api/events/{row['event_id']}", auth=auth).json()
        assert detail['simulation_run'] == result['id']
    assert client.get('/api/simulations/runs', auth=auth).json()['items'][0]['id'] == result['id']


def test_validation_and_no_external_target(tmp_path):
    _, management = create_apps(tmp_path, password='testing')
    client = TestClient(management)
    kwargs = {'auth': ('admin', 'testing'), 'headers': {'X-Suishi-Action': 'simulation'}}
    for value in [{'case_ids': []}, {'case_ids': ['unknown']}, {'case_ids': ['normal']*13},
                  {'case_ids':['normal'], 'target':'https://example.com'}]:
        assert client.post('/api/simulations/run', json=value, **kwargs).status_code == 422
    assert client.get('/api/simulations/runs', auth=('admin','testing')).json()['items'] == []
