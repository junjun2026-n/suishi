// ============================================================
// 文件名称：settings.js
// 生成日期：2026-11-21
// 修改日期：2026-11-22
// 版本信息：v0.261115
// 作者：JUN
// 备注：本程序由AI辅助完成。
// 文件功能用途：提供蜜罐响应模式、采集上限、超时和保存反馈界面。
// 注意事项：清理记录需单独确认，配置修改需服务器端授权校验。
// ============================================================
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
      <label>响应模式<select id="profile" style="display:block;width:100%;padding:10px"><option value="adaptive">自适应场景（全部服务）</option><option value="portal">统一门户</option><option value="wordpress">WordPress / CMS</option><option value="spring">Spring 运维接口</option><option value="jenkins">Jenkins 自动化平台</option><option value="gitlab">GitLab 代码平台</option><option value="containers">Docker / Kubernetes</option><option value="data">数据服务 / Web 数据库管理</option><option value="gateway">网关 / VPN / OA 门户</option><option value="files">文件 / 备份 / 调试入口</option></select></label>
      <label>正文采集上限（字节）<input id="limit" type="number" required min="1024" max="1048576" style="display:block;width:100%"></label>
      <label>读取超时（秒）<input id="timeout" type="number" required min="1" max="30" style="display:block;width:100%"></label>
      </div></fieldset></form><p id="settings-notice" role="status" aria-live="polite"></p>
      <p>自适应场景按路径返回模拟页面；统一门户使用固定门户。正文上限为 1 KB～1 MB，读取超时为 1～30 秒。保存后对新请求生效。</p>
      <p>请求内容仅保存分析，不执行。正文哈希对应已采集字节，截断记录不代表完整请求。</p>
      <hr><h3>引流服务目录</h3><p>WAF 蜜罐目标仍填写本系统业务入口。自适应模式按请求路径匹配下列服务；选择指定模式后，未知路径返回该服务外观，已识别路径仍优先匹配。仅模拟 HTTP，不开放真实数据库或容器控制权限。</p><div id="decoy-catalog"></div>
      <hr><h3>历史记录清理</h3><div class="toolbar"><label>删除此时间之前的记录 <input id="before" type="datetime-local"></label><button id="purge" type="button">清理历史记录</button></div><p>清理不可恢复，请先备份当前数据库。</p>`;
    const notice = $('settings-notice');
    async function reload() {
      $('save').disabled = true;
      try {
        const data = await api('/api/settings');
        $('profile').value = data.profile; $('limit').value = data.body_limit; $('timeout').value = data.read_timeout;
        notice.textContent = '已加载当前数据库中的配置';
        notice.style.color = '#475569';
        $('save').disabled = false;
      } catch (e) { notice.textContent = e.message; notice.style.color = '#b42318'; }
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
    try {
      const catalog=await api('/api/decoys');
      for(const item of catalog.items){const block=document.createElement('div');block.className='card';const title=document.createElement('h4');title.textContent=item.name;const description=document.createElement('p');description.textContent=item.description;const paths=document.createElement('code');paths.textContent=item.paths.join(' · ');block.append(title,description,paths);$('decoy-catalog').append(block);}
    } catch(e) { notice.textContent='引流目录加载失败：'+e.message; }
  };
})();
