# ============================================================
# 文件名称：decoys.py
# 生成日期：2026-11-22 | 修改日期：2026-11-22
# 版本信息：v0.261115 | 作者：JUN
# 备注：本程序由AI辅助完成。
# 文件功能用途：提供可引流的 Web 服务诱饵目录与固定响应。
# 注意事项：不连接真实服务、不返回真实凭据、不执行表达式或命令。
# ============================================================
CATALOG = [
    {'id':'wordpress','name':'WordPress / CMS','paths':['/wp-login.php','/wp-admin/','/wp-json/','/xmlrpc.php'],
     'description':'模拟 CMS 登录、REST 接口与 XML-RPC 入口。'},
    {'id':'spring','name':'Spring 运维接口','paths':['/actuator/health','/actuator/env','/actuator/mappings'],
     'description':'模拟健康检查、配置与路由信息探测面。'},
    {'id':'jenkins','name':'Jenkins 自动化平台','paths':['/jenkins/','/jenkins/login','/jenkins/api/json','/jenkins/script'],
     'description':'模拟流水线平台登录、任务查询与控制台探测；不运行脚本。'},
    {'id':'gitlab','name':'GitLab 代码平台','paths':['/users/sign_in','/api/v4/projects','/gitlab/'],
     'description':'模拟代码管理登录与固定项目列表。'},
    {'id':'containers','name':'Docker / Kubernetes','paths':['/version','/containers/json','/v1.41/containers/json','/api/v1/namespaces','/api/v1/pods'],
     'description':'仅 HTTP API 外观，不连接 Docker Socket、集群或创建容器。'},
    {'id':'data','name':'Elasticsearch / 数据管理','paths':['/_cluster/health','/_cat/indices','/_search','/phpmyadmin/','/adminer.php'],
     'description':'模拟搜索集群及数据库 Web 管理入口，不提供数据库协议监听。'},
    {'id':'gateway','name':'网关 / VPN / OA 门户','paths':['/vpn/login','/remote/login','/oa/login','/cgi-bin/luci/'],
     'description':'模拟网关、远程接入和办公系统登录页面。'},
    {'id':'files','name':'文件 / 备份 / 调试入口','paths':['/server-status','/swagger.json','/backup.sql','/.git/HEAD','/debug/pprof/'],
     'description':'模拟信息暴露、备份及调试接口；所有内容为虚构样例。'},
]
PROFILES = ['adaptive','portal'] + [item['id'] for item in CATALOG]


def login(title, method):
    notice = '<p>Invalid username or password.</p>' if method=='POST' else ''
    return ('<!doctype html><title>'+title+'</title><h1>'+title+'</h1>'+notice+
        '<form method="post"><label>Username <input name="username" autocomplete="off"></label>'
        '<label>Password <input name="password" type="password" autocomplete="off"></label>'
        '<button>Sign in</button></form>')


def response(path, method, profile):
    """Only static payloads; path chooses a scenario but is never echoed."""
    p=path.lower()
    if profile=='portal':
        return None
    family = next((item['id'] for item in CATALOG if p in [v.lower() for v in item['paths']]), None)
    if not family:
        for prefix, group in [('/wp-','wordpress'),('/jenkins','jenkins'),('/gitlab','gitlab'),
            ('/actuator','spring'),('/api/v1/','containers'),('/vpn','gateway'),('/oa/','gateway'),
            ('/remote/','gateway'),('/cgi-bin/','gateway'),('/debug/','files')]:
            if p.startswith(prefix):family=group;break
    if not family:
        family=profile if profile not in ('adaptive','portal') else None
    if not family:
        return None
    media='application/json'
    if family=='wordpress':
        if p=='/xmlrpc.php':content='XML-RPC server accepts POST requests only.';media='text/plain'
        elif p.startswith('/wp-json'):content='{"name":"Corporate Portal","namespaces":["wp/v2"],"routes":{}}'
        else:content=login('WordPress Sign In',method);media='text/html'
    elif family=='spring':
        if p.endswith('/env'):content='{"activeProfiles":["production"],"propertySources":[{"name":"applicationConfig","properties":{"server.port":{"value":8080},"database.password":{"value":"******"}}}]}'
        elif p.endswith('/mappings'):content='{"contexts":{"application":{"mappings":{"dispatcherServlets":{"dispatcherServlet":[{"predicate":"{GET [/api/status]}"}]}}}}}'
        else:content='{"status":"UP","components":{"diskSpace":{"status":"UP"}}}'
    elif family=='jenkins':
        if p.endswith('/api/json'):content='{"mode":"NORMAL","nodeDescription":"controller","jobs":[{"name":"portal-build","color":"blue"}]}'
        elif p.endswith('/script'):content='<h1>Script Console</h1><p>Authentication required.</p>';media='text/html'
        else:content=login('Jenkins Sign In',method);media='text/html'
    elif family=='gitlab':
        if p.startswith('/api/v4/'):content='[{"id":1,"name":"portal-demo","visibility":"private","archived":false}]'
        else:content=login('GitLab Sign In',method);media='text/html'
    elif family=='containers':
        if '/containers' in p:content='[{"Id":"decoy-0001","Names":["/portal"],"Image":"nginx:stable","State":"running"}]'
        elif '/pods' in p:content='{"kind":"PodList","apiVersion":"v1","items":[{"metadata":{"name":"portal-demo","namespace":"default"},"status":{"phase":"Running"}}]}'
        elif '/namespaces' in p:content='{"kind":"NamespaceList","apiVersion":"v1","items":[{"metadata":{"name":"default"}}]}'
        else:content='{"Version":"24.0.0","ApiVersion":"1.43","Os":"linux","Arch":"amd64"}'
    elif family=='data':
        if p.startswith('/phpmyadmin') or p=='/adminer.php':content=login('Database Administration',method);media='text/html'
        elif p=='/_cat/indices':content='green open portal-demo 1 0 0 0 208b 208b\n';media='text/plain'
        elif p=='/_search':content='{"took":1,"timed_out":false,"hits":{"total":{"value":0,"relation":"eq"},"hits":[]}}'
        else:content='{"cluster_name":"search-gateway","status":"green","number_of_nodes":1}'
    elif family=='gateway':
        content=login('Secure Access Portal',method);media='text/html'
    else:
        media='text/plain'
        if p=='/.git/head':content='ref: refs/heads/main\n'
        elif p=='/backup.sql':content='-- Example database backup\nCREATE TABLE portal_demo (id INTEGER, title VARCHAR(80));\n'
        elif p=='/swagger.json':content='{"swagger":"2.0","info":{"title":"Gateway API","version":"1.0"},"paths":{"/api/status":{"get":{"responses":{"200":{"description":"OK"}}}}}}';media='application/json'
        elif p=='/server-status':content='Server uptime: 7200 seconds\nTotal accesses: 128\nBusyWorkers: 1\nIdleWorkers: 7\n'
        else:content='Debug service\nAvailable profiles: heap, goroutine\n'
    return family,content,media
