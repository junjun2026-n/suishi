# 文件名称：simulations.py
# 生成日期：2026-11-21 | 修改日期：2026-11-21 | 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。内置蜜罐验证样例，仅在本应用内回放，不执行载荷。
CASES = [
    {'id': 'sqli', 'name': 'SQL 注入', 'method': 'GET', 'path': '/products?id=1%20UNION%20SELECT%201', 'body': '', 'expected': 'SQL 注入'},
    {'id': 'xss', 'name': '跨站脚本 XSS', 'method': 'POST', 'path': '/search', 'body': '<script>alert("suishi-test")</script>', 'expected': '跨站脚本'},
    {'id': 'traversal', 'name': '目录穿越 / 文件读取探测', 'method': 'GET', 'path': '/download?file=../../etc/passwd', 'body': '', 'expected': '路径穿越'},
    {'id': 'command', 'name': '命令执行探测', 'method': 'POST', 'path': '/tools/ping', 'body': 'host=example.invalid;whoami', 'expected': '命令执行探测'},
    {'id': 'ssrf', 'name': 'SSRF 探测', 'method': 'POST', 'path': '/api/fetch', 'body': 'url=http://169.254.169.254/latest/meta-data/', 'expected': 'SSRF 探测'},
    {'id': 'sensitive', 'name': '敏感文件扫描', 'method': 'GET', 'path': '/.env', 'body': '', 'expected': '敏感文件探测'},
    {'id': 'scanner', 'name': '扫描器指纹', 'method': 'GET', 'path': '/', 'body': '', 'user_agent': 'nuclei/suishi-test', 'expected': '自动化扫描'},
    {'id': 'login', 'name': '管理登录探测', 'method': 'POST', 'path': '/admin/login', 'body': 'username=demo&password=suishi-example', 'expected': '管理入口探测'},
    {'id': 'xxe', 'name': 'XML 外部实体探测', 'method': 'POST', 'path': '/api/xml', 'body': '<!DOCTYPE test [<!ENTITY example SYSTEM "file:///suishi-nonexistent">]><test>&example;</test>', 'expected': 'XML 外部实体探测'},
    {'id': 'template', 'name': '模板注入探测', 'method': 'POST', 'path': '/render', 'body': 'template={{7*7}}', 'expected': '模板注入探测'},
    {'id': 'upload', 'name': '脚本文件上传探测', 'method': 'POST', 'path': '/upload', 'body': '--suishi\r\nContent-Disposition: form-data; name="file"; filename="example.php"\r\n\r\n<?php /* suishi inert sample */ ?>\r\n--suishi--', 'content_type': 'multipart/form-data; boundary=suishi', 'expected': '脚本上传探测'},
    {'id': 'normal', 'name': '正常访问对照', 'method': 'GET', 'path': '/products?category=books', 'body': '', 'expected': ''},
]
