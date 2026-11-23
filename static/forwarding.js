// ============================================================
// 文件名称：forwarding.js
// 生成日期：2026-11-21
// 修改日期：2026-11-22
// 版本信息：v0.261115
// 作者：JUN
// 备注：本程序由AI辅助完成。
// 文件功能用途：提供日志转发配置、测试发送和队列状态界面。
// 注意事项：外部消息只按文本显示，启用正文转发前确认接收端权限。
// ============================================================
(() => {
  const button = document.createElement('button');
  button.textContent = '日志转发';
  document.getElementById('simulation-tab').after(button);
  const view = document.createElement('section');
  view.hidden = true;
  view.innerHTML = `<h2>日志转发</h2>
    <label style="display:flex;align-items:center;gap:8px"><input id="fw-enabled" type="checkbox" style="width:auto">启用日志转发</label>
    <fieldset id="fw-fields" style="border:0;padding:16px 0;min-width:0"><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;max-width:1000px">
    <label>接收服务器 IP / 主机名<input id="fw-host" style="display:block;width:100%" placeholder="例如 192.168.17.127"></label>
    <label>接收端口<input id="fw-port" type="number" min="1" max="65535" style="display:block;width:100%"></label>
    <label>传输方式<select id="fw-protocol" style="display:block;width:100%;padding:10px"><option value="udp">UDP</option><option value="tcp">TCP</option></select></label>
    <label>数据格式<select id="fw-format" style="display:block;width:100%;padding:10px"><option value="json">JSON</option><option value="syslog">Syslog（RFC 5424）</option><option value="custom">自定义</option></select></label>
    </div><label style="display:flex;align-items:center;gap:8px;margin-top:16px"><input id="fw-body" type="checkbox" style="width:auto">转发已采集的请求正文</label>
    <div id="fw-custom" hidden><p>自定义模板</p><textarea id="fw-template" rows="3" style="width:100%;max-width:1000px"></textarea><p>字段：{id} {time} {source_ip} {peer_ip} {method} {path} {host} {severity} {rule} {status} {request_id} {scenario} {findings} {simulation_run} {body_text}</p></div></fieldset>
    <div class="toolbar"><button id="fw-save">保存配置</button><button id="fw-test">发送测试</button><button id="fw-refresh">刷新状态</button></div>
    <p id="fw-notice" role="status"></p><p id="fw-status"></p>
    <p>启用后转发新增采集记录（含模拟流量）；历史记录不补发。关闭后暂停发送，队列保留。修改接收地址后，待发送日志发往新地址。</p>
    <p>TCP 使用换行分帧。UDP 单条上限 60000 字节；发送成功不代表接收或入库成功。队列最多保留 10000 条，超出部分仅保存在本地。正文可能含敏感内容，请按需启用。</p>`;
  document.getElementById('events-view').before(view);
  const el = name => document.getElementById('fw-' + name);
  function update() {
    el('fields').disabled = !el('enabled').checked;
    el('test').disabled = !el('enabled').checked;
    el('custom').hidden = el('format').value !== 'custom';
  }
  async function request(path, method, data) {
    const response = await fetch('/api/forwarding' + path, {method, headers: {'Content-Type': 'application/json', 'X-Suishi-Action': 'forwarding'}, ...(data ? {body: JSON.stringify(data)} : {})});
    checkSession(response);
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : JSON.stringify(result.detail));
    return result;
  }
  async function status() {
    const s = await request('/status', 'GET');
    el('status').textContent = `待发送：${s.pending}　已发送：${s.sent}　队列溢出：${s.dropped}　最近发送：${s.last_sent || '无'}　最近错误：${s.last_error || '无'}`;
  }
  async function attempt(action) {
    try { await action(); } catch (error) { el('notice').textContent = error.message; }
  }
  button.onclick = () => attempt(async () => {
    for (const id of ['events-view', 'extra', 'simulation-view']) document.getElementById(id).hidden = true;
    view.hidden = false;
    const config = await request('', 'GET');
    for (const name of ['host', 'port', 'protocol', 'format', 'template']) el(name).value = config[name];
    el('enabled').checked = config.enabled; el('body').checked = config.include_body;
    el('notice').textContent = ''; update(); await status();
  });
  document.querySelectorAll('[data-tab],#simulation-tab').forEach(b => b.addEventListener('click', () => { view.hidden = true; }));
  el('enabled').onchange = update; el('format').onchange = update;
  el('save').onclick = () => attempt(async () => {
    await request('', 'PUT', {enabled: el('enabled').checked, host: el('host').value, port: Number(el('port').value), protocol: el('protocol').value, format: el('format').value, template: el('template').value, include_body: el('body').checked});
    el('notice').textContent = '配置已保存'; await status();
  });
  el('test').onclick = () => attempt(async () => { el('notice').textContent = (await request('/test', 'POST')).message; });
  el('refresh').onclick = () => attempt(status);
})();
