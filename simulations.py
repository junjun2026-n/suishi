# ============================================================
# 文件名称：simulations.py
# 生成日期：2026-11-21
# 修改日期：2026-11-22
# 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。
# 文件功能用途：定义用于蜜罐功能验证的固定模拟请求样例。
# 注意事项：样例仅供内部回放，不执行载荷或向外部目标发起攻击。
# ============================================================
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
    {'id':'wordpress','name':'WordPress REST 接口探测','method':'GET','path':'/wp-json/','body':'','expected':'CMS 接口探测'},
    {'id':'xmlrpc','name':'WordPress XML-RPC 探测','method':'POST','path':'/xmlrpc.php','body':'<methodCall><methodName>system.listMethods</methodName></methodCall>','expected':'CMS 接口探测'},
    {'id':'spring','name':'Spring 配置接口探测','method':'GET','path':'/actuator/env','body':'','expected':'运维接口探测'},
    {'id':'jenkins','name':'Jenkins 控制台探测','method':'GET','path':'/jenkins/script','body':'','expected':'运维接口探测'},
    {'id':'gitlab','name':'GitLab 项目接口探测','method':'GET','path':'/api/v4/projects','body':'','expected':'代码平台探测'},
    {'id':'docker','name':'Docker API 探测','method':'GET','path':'/v1.41/containers/json','body':'','expected':'容器接口探测'},
    {'id':'kubernetes','name':'Kubernetes Pod 探测','method':'GET','path':'/api/v1/pods','body':'','expected':'容器接口探测'},
    {'id':'elastic','name':'Elasticsearch 索引探测','method':'GET','path':'/_cat/indices','body':'','expected':'数据服务探测'},
    {'id':'gateway','name':'VPN 网关登录探测','method':'GET','path':'/vpn/login','body':'','expected':'网关门户探测'},
    {'id':'oa','name':'OA 办公登录探测','method':'POST','path':'/oa/login','body':'username=demo&password=sample','expected':'网关门户探测'},
    {'id':'swagger','name':'Swagger 接口文档探测','method':'GET','path':'/swagger.json','body':'','expected':'调试接口探测'},
    {'id':'debug','name':'运行时调试接口探测','method':'GET','path':'/debug/pprof/','body':'','expected':'调试接口探测'},
    {'id':'nosql','name':'NoSQL 注入探测','method':'POST','path':'/api/auth','body':'{"username":{"$ne":null},"password":{"$ne":null}}','content_type':'application/json','expected':'NoSQL 注入探测'},
    {'id':'ldap','name':'LDAP 注入探测','method':'POST','path':'/login','body':'username=*)(|(uid=*))','expected':'LDAP 注入探测'},
    {'id':'deserialize','name':'Java 序列化特征探测','method':'POST','path':'/api/session','body':'rO0AB-suishi-inert-marker','expected':'反序列化特征'},
]
