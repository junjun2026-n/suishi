// 文件名称：settings.js | 生成/修改日期：2026-11-21 | 版本：v0.261115 | 作者：JUN
// 备注：本程序由AI辅助完成。蜜罐配置表单及保存反馈；清理操作需单独确认。
(() => {
  const previousTab = tab;
  tab = async function(name) {
    // Show exactly one sheet, including when switching back from forwarding.
    document.querySelectorAll('main section').forEach(section => {
      if (section.id !== 'extra' && !section.closest('#events-view')) section.hidden = true;
    });
    if (name !== 'settings') return previousTab(name);
    $('events-view').hidden = true;
    $('extra').hidden = false;
    $('global-notice').textContent = '';
    $('extra').innerHTML = `<div class="toolbar" style="justify-content:space-between"><h2 style="margin:0">蜜罐配置</h2><div><button id="save" type="submit" form="honeypot-settings">保存配置</button> <button id="settings-reload" type="button">重新加载</button></div></div>
      <form id="honeypot-settings"><fieldset id="settings-fields" style="border:0;padding:0;min-width:0"><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px;max-width:1100px">
      <label>响应模式<select id="profile" style="display:block;width:100%;padding:10px"><option value="adaptive">自适应场景</option><option value="portal">统一门户</option></select></label>
      <label>正文采集上限（字节）<input id="limit" type="number" required min="1024" max="1048576" style="display:block;width:100%"></label>
      <label>读取超时（秒）<input id="timeout" type="number" required min="1" max="30" style="display:block;width:100%"></label>
      </div></fieldset></form><p id="settings-notice" role="status" aria-live="polite"></p>
      <p>自适应场景按路径返回模拟页面；统一门户使用固定门户。正文上限为 1 KB～1 MB，读取超时为 1～30 秒。保存后对新请求生效。</p>
      <p>请求内容仅保存分析，不执行。正文哈希对应已采集字节，截断记录不代表完整请求。</p>
      <hr><h3>历史记录清理</h3><div class="toolbar"><label>删除此时间之前的记录 <input id="before" type="datetime-local"></label><button id="purge" type="button">清理历史记录</button></div><p>清理不可恢复，请先备份当前数据库。</p>`;
    const notice = $('settings-notice');
    async function reload() {
      $('save').disabled = true;
      try {
        const data = await api('/api/settings');
        $('profile').value = data.profile; $('limit').value = data.body_limit; $('timeout').value = data.read_timeout;
        notice.textContent = '已加载当前数据库中的配置';
        notice.style.color = '#475569';
      } catch (e) { notice.textContent = e.message; notice.style.color = '#b42318'; }
      finally { $('save').disabled = false; }
    }
    $('settings-reload').onclick = reload;
    $('honeypot-settings').onsubmit = async event => {
      event.preventDefault();
      $('save').disabled = true;
      try {
        await write('/api/settings', 'PUT', 'settings', {profile: $('profile').value, body_limit: Number($('limit').value), read_timeout: Number($('timeout').value)});
        notice.textContent = '配置已保存至数据库，对下一条请求生效'; notice.style.color = '#15803d';
      } catch(e) { notice.textContent = e.message; notice.style.color = '#b42318'; }
      finally { $('save').disabled = false; }
    };
    $('purge').onclick = async () => {
      if (!$('before').value) { notice.textContent = '请先选择清理截止时间'; return; }
      if (!confirm('确定删除所选时间之前的记录？此操作不可恢复，请确认已经备份。')) return;
      try {
        const result = await write('/api/retention', 'POST', 'retention', {before: new Date($('before').value).toISOString()});
        notice.textContent = '已清理 ' + result.deleted + ' 条记录';
      } catch(e) { notice.textContent = e.message; }
    };
    await reload();
  };
})();
