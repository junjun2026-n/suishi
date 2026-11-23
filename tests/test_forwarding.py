# ============================================================
# 文件名称：test_forwarding.py
# 生成日期：2026-11-21
# 修改日期：2026-11-21
# 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。
# 文件功能用途：验证 UDP/TCP 日志收发、队列重试及配置保护。
# 注意事项：套接字仅使用回环地址，测试结束需释放连接。
# ============================================================
import json
import socket
import sqlite3

from fastapi.testclient import TestClient
from app import create_apps

AUTH = ('admin', 'testing')
HEADERS = {'X-Suishi-Action': 'forwarding'}


def test_udp_queue_and_configuration(tmp_path):
    decoy, admin = create_apps(tmp_path, password='testing')
    client, manage = TestClient(decoy), TestClient(admin)
    assert manage.get('/api/forwarding').status_code == 401
    client.get('/disabled')
    assert decoy.state.forwarder.status()['pending'] == 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(('127.0.0.1', 0)); receiver.settimeout(3)
        config = {'enabled': True, 'host': '127.0.0.1', 'port': receiver.getsockname()[1]}
        assert manage.put('/api/forwarding', auth=AUTH, json=config).status_code == 403
        assert manage.put('/api/forwarding', auth=AUTH, headers=HEADERS, json=config).status_code == 200
        client.post('/capture', content='secret-body')
        assert decoy.state.forwarder.status()['pending'] == 1
        assert decoy.state.forwarder.deliver_one()
        data = json.loads(receiver.recv(65535))
        assert data['platform'] == 'suishi' and data['path'] == '/capture'
        assert 'body_text' not in data and 'body_base64' not in data
        assert decoy.state.forwarder.status()['sent'] == 1
        assert manage.post('/api/forwarding/test', auth=AUTH, headers=HEADERS).status_code == 200
        assert json.loads(receiver.recv(65535))['scenario'] == 'forwarding_test'
    restarted, _ = create_apps(tmp_path, password='testing')
    assert restarted.state.forwarder.config().host == '127.0.0.1'
    for template in ['{source_ip.__class__}', '{time!r}', '{bad}', '{time:999}', '{']:
        assert manage.put('/api/forwarding', auth=AUTH, headers=HEADERS,
                          json={**config, 'format': 'custom', 'template': template}).status_code == 422


def test_tcp_retry_disable_and_body(tmp_path):
    decoy, _ = create_apps(tmp_path, password='testing')
    forwarder = decoy.state.forwarder
    with socket.socket() as receiver:
        receiver.bind(('127.0.0.1', 0))
        port = receiver.getsockname()[1]
        from forwarding import ForwardConfig
        forwarder.save(ForwardConfig(enabled=True, host='127.0.0.1', port=port, protocol='tcp', include_body=True))
        assert TestClient(decoy).post('/test', content='hello').status_code == 200
        forwarder.deliver_one()  # Bound socket has not started listening yet.
        assert forwarder.status()['pending'] == 1 and forwarder.status()['last_error']
        forwarder.save(ForwardConfig())
        assert forwarder.deliver_one() is False
        forwarder.save(ForwardConfig(enabled=True, host='127.0.0.1', port=port, protocol='tcp'))
        receiver.listen(); receiver.settimeout(3)
        with sqlite3.connect(tmp_path / 'suishi.db') as db:
            db.execute('UPDATE forwarding_queue SET next_try=0')
        forwarder.deliver_one()
        connection, _ = receiver.accept()
        with connection:
            data = b''
            while not data.endswith(b'\n'):
                data += connection.recv(65536)
        assert json.loads(data)['body_text'] == 'hello'  # Payload is frozen at collection time.
        assert forwarder.status()['pending'] == 0 and forwarder.status()['sent'] == 1


def test_formats_and_udp_limit():
    import pytest
    from forwarding import ForwardConfig, encode_event, send_message
    event = {'time': '2026-11-21T00:00:00Z', 'path': '/x\nforged', 'source_ip': '127.0.0.1', 'body_text': 'secret'}
    encoded = encode_event(event, ForwardConfig(format='syslog'))
    assert encoded.startswith(b'<134>1 ') and b'\n' not in encoded
    assert encode_event(event, ForwardConfig(format='custom', template='{source_ip} {path} {body_text}')) == b'127.0.0.1 /x\\nforged '
    with pytest.raises(ValueError, match='60000'):
        send_message(b'x'*60001, ForwardConfig())
