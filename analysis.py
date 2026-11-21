# 文件名称：analysis.py
# 生成日期：2026-11-21 | 修改日期：2026-11-21 | 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。HTTP攻击特征分析及安全模拟响应；不执行载荷。
import re
from urllib.parse import unquote

PATTERNS = [
    ('SQL 注入', '高', r"union\s+(?:all\s+)?select|\bor\s+['\"]?1['\"]?\s*=\s*['\"]?1|sleep\s*\(|information_schema|\bdrop\s+table\b"),
    ('跨站脚本', '高', r'<script\b|javascript\s*:|on(?:error|load)\s*='),
    ('路径穿越', '高', r'\.\.[/\\]|/etc/passwd|windows[/\\]win.ini'),
    ('命令执行探测', '高', r'\$\(|`[^`]+`|[;|&]\s*(?:cat|whoami|wget|curl|id|bash|sh|powershell)\b'),
    ('SSRF 探测', '高', r'https?://(?:127\.0\.0\.1|localhost|169\.254\.169\.254)|file://|gopher://'),
    ('敏感文件探测', '中', r'/(?:\.env|\.git|\.svn)(?:[/?.\s]|$)|(?:backup|dump)\.(?:sql|zip)|wp-config\.php'),
    ('自动化扫描', '中', r'sqlmap|nikto|nuclei|masscan|zgrab|acunetix'),
    ('管理入口探测', '低', r'/(?:admin|wp-admin|wp-login\.php|phpmyadmin|actuator)(?:[/?.\s]|$)'),
    ('XML 外部实体探测', '高', r'<!ENTITY\s+\S+\s+(?:SYSTEM|PUBLIC)\b'),
    ('模板注入探测', '高', r'\{\{\s*\d+\s*\*\s*\d+\s*\}\}|\$\{\s*\d+\s*\*\s*\d+\s*\}'),
    ('脚本上传探测', '高', r'filename\s*=\s*[\"\'][^\r\n\"\']*\.(?:php\d*|jsp|jspx|asp|aspx|phtml)[\"\']'),
]
COMPILED = [(name, severity, re.compile(pattern, re.I)) for name, severity, pattern in PATTERNS]


def analyze(target, body, user_agent, waf_rule=''):
    text = target + '\n' + body + '\n' + user_agent
    for _ in range(2):
        text = unquote(text)
    matches = []
    for name, severity, pattern in COMPILED:
        match = pattern.search(text)
        if match:
            matches.append({'type': name, 'severity': severity, 'evidence': match.group(0)[:160]})
    if waf_rule:
        matches.append({'type': 'WAF 规则命中', 'severity': '中', 'evidence': waf_rule[:512]})
    severity = next((level for level in ['高', '中', '低'] if any(m['severity'] == level for m in matches)), '信息')
    return matches, severity


def respond(path, method, profile):
    """Return only static decoy data; never interpolate attacker-controlled text."""
    path = path.lower()
    if profile == 'portal':
        return 'portal', '<h1>Service Portal</h1><p>Your request has been received.</p>', 'text/html'
    if '/.env' in path:
        return 'environment', '# Environment template\nAPP_ENV=staging\nAPP_DEBUG=false\n', 'text/plain'
    if '/.git' in path:
        return 'git', '[core]\nrepositoryformatversion = 0\nbare = false\n', 'text/plain'
    if '/actuator' in path or path.startswith('/api/'):
        return 'api', '{"status":"UP","service":"gateway","version":"1.0"}', 'application/json'
    if any(s in path for s in ['/admin', '/login', '/wp-login', '/phpmyadmin']):
        if method == 'POST':
            return 'login', '<h1>Sign in</h1><p>Invalid username or password.</p>', 'text/html'
        return 'login', ('<!doctype html><title>Administration</title><h1>Administration</h1>'
                         '<form method="post"><label>Username <input name="username" autocomplete="off"></label>'
                         '<label>Password <input name="password" type="password"></label>'
                         '<button>Sign in</button></form>'), 'text/html'
    return 'portal', '<h1>Service Portal</h1><p>Your request has been received.</p>', 'text/html'
