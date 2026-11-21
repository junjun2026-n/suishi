// 文件名称：administration.js | 生成/修改日期：2026-11-21 | 版本：v0.261115 | 作者：JUN
// 备注：本程序由AI辅助完成。数据库与用户管理；密码不写入浏览器本地存储。
(() => {
  const panel = document.createElement('section'); panel.hidden = true;
  document.getElementById('events-view').before(panel);
  const menu = document.getElementById('simulation-tab').parentElement;
  const dbButton = document.createElement('button'), usersButton = document.createElement('button'), logout = document.createElement('button');
  dbButton.textContent='数据库配置'; usersButton.textContent='用户管理'; logout.textContent='退出登录';
  menu.append(dbButton, usersButton, logout);
  const notice = document.createElement('p'); notice.setAttribute('role','status');
  async function call(path, method='GET', data) {
    const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-Suishi-Action':'administration'},...(data?{body:JSON.stringify(data)}:{})});
    if(r.status===401){location.replace('/login');throw new Error('请重新登录')}
    const result=await r.json(); if(!r.ok)throw new Error(typeof result.detail==='string'?result.detail:JSON.stringify(result.detail));return result;
  }
  async function attempt(fn){try{await fn()}catch(e){notice.textContent=e.message}}
  function open(html){
    for(const id of ['events-view','extra','simulation-view'])document.getElementById(id).hidden=true;
    // Hide the independent forwarding sheet when opening administration.
    const fw=document.getElementById('fw-host');if(fw)fw.closest('section').hidden=true;
    panel.innerHTML=html;panel.hidden=false;notice.textContent='';panel.append(notice);
  }
  menu.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{if(b!==dbButton&&b!==usersButton)panel.hidden=true}));
  const style=document.createElement('style');style.textContent='.admin-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;max-width:1100px}.admin-grid input,.admin-grid select{display:block;width:100%;padding:10px}.admin-actions{display:flex;gap:10px;align-items:center;margin-top:20px;flex-wrap:wrap}.password-row{display:flex;align-items:center;gap:8px}.password-row input{min-width:0;flex:1}.password-row button{flex:none}';document.head.append(style);
  function eye(input){const row=document.createElement('div');row.className='password-row';input.before(row);row.append(input);const b=document.createElement('button');b.textContent='◉';b.type='button';b.title='显示/隐藏密码';b.setAttribute('aria-label','显示/隐藏密码');b.onclick=()=>input.type=input.type==='password'?'text':'password';row.append(b)}
  dbButton.onclick=()=>attempt(async()=>{
    const cfg=await call('/api/database');
    open(`<h2>数据库配置</h2><div class="admin-grid"><label>数据库类型<select id="db-type"><option value="sqlite">SQLite</option><option value="postgresql">PostgreSQL（PQ）</option><option value="mysql">MySQL / MariaDB</option></select></label><label id="db-file-label">数据库文件<input id="db-file"></label><label class="db-remote">服务器地址<input id="db-host"></label><label class="db-remote">端口<input id="db-port" type="number" min="1" max="65535"></label><label class="db-remote">数据库名称<input id="db-database"></label><label class="db-remote">用户名<input id="db-username" autocomplete="off"></label><label class="db-remote">密码<input id="db-password" type="password" autocomplete="new-password"></label></div><div class="admin-actions"><button id="db-test">测试连接</button><button id="db-save">初始化、迁移并保存</button></div><p>初始化保留当前数据；切换到空目标库时迁移采集记录、用户、配置、转发队列及模拟记录。目标数据库需已创建，并授予建表权限。已有平台数据的目标库禁止覆盖。迁移期间采集请求可能短暂等待。</p>`);
    const el=k=>document.getElementById('db-'+k);for(const k of ['type','file','host','port','database','username','password'])el(k).value=cfg[k];eye(el('password'));
    const update=()=>{const remote=el('type').value!=='sqlite';el('file-label').hidden=remote;panel.querySelectorAll('.db-remote').forEach(x=>x.hidden=!remote)};
    el('type').onchange=()=>{el('port').value=el('type').value==='mysql'?3306:5432;update()};update();
    function value(){const v={};for(const k of ['type','file','host','port','database','username','password'])v[k]=el(k).value;v.port=Number(v.port);return v}
    el('test').onclick=()=>attempt(async()=>{notice.textContent=(await call('/api/database/test','POST',value())).message});
    el('save').onclick=()=>attempt(async()=>{el('save').disabled=true;notice.textContent='正在初始化及迁移……';try{const r=await call('/api/database/initialize','POST',value());notice.textContent=r.message+' '+JSON.stringify(r.migrated)}finally{el('save').disabled=false}});
  });
  usersButton.onclick=()=>attempt(async()=>{
    const data=await call('/api/users');
    open(`<h2>用户管理</h2><div class="admin-grid"><label>用户名<input id="user-name" maxlength="64"></label><label>密码（编辑时留空保留）<input id="user-password" type="password" autocomplete="new-password"></label><label>角色<select id="user-role"><option value="viewer">只读用户</option><option value="admin">管理员</option></select></label><label style="display:flex;align-items:center;gap:8px"><input id="user-enabled" type="checkbox" checked style="width:auto">启用用户</label></div><div class="admin-actions"><button id="user-save">新增用户</button><button id="user-clear">取消编辑</button></div><p>默认 admin 不可删除、禁用或降权。只读用户可查看采集记录与分析结果。密码至少 8 位。</p><div class="table"><table><thead><tr><th>用户名</th><th>角色</th><th>状态</th><th>操作</th></tr></thead><tbody id="user-rows"></tbody></table></div>`);
    const el=k=>document.getElementById('user-'+k);eye(el('password'));let editing=false;
    el('clear').onclick=()=>{editing=false;el('name').disabled=false;el('name').value='';el('password').value='';el('role').disabled=false;el('role').value='viewer';el('enabled').disabled=false;el('enabled').checked=true;el('save').textContent='新增用户'};
    for(const user of data.items){const tr=document.createElement('tr');for(const text of [user.username,user.role==='admin'?'管理员':'只读用户',user.enabled?'启用':'禁用']){const td=document.createElement('td');td.textContent=text;tr.append(td)}
      const td=document.createElement('td');td.className='admin-actions';const edit=document.createElement('button');edit.textContent='编辑';edit.onclick=()=>{editing=true;el('name').value=user.username;el('name').disabled=true;el('password').value='';el('role').value=user.role;el('enabled').checked=!!user.enabled;el('role').disabled=el('enabled').disabled=user.username==='admin';el('save').textContent='保存修改'};td.append(edit);
      const del=document.createElement('button');del.textContent='删除';del.disabled=user.username==='admin';del.onclick=()=>attempt(async()=>{if(!confirm('确定删除用户 '+user.username+'？'))return;await call('/api/users/'+encodeURIComponent(user.username),'DELETE');usersButton.click()});td.append(del);tr.append(td);el('rows').append(tr)}
    el('save').onclick=()=>attempt(async()=>{const username=el('name').value;await call('/api/users'+(editing?'/'+encodeURIComponent(username):''),editing?'PUT':'POST',{username,password:el('password').value,role:el('role').value,enabled:el('enabled').checked});usersButton.click()});
  });
  logout.onclick=async()=>{await fetch('/api/logout',{method:'POST',headers:{'X-Suishi-Action':'logout'}});location.replace('/login')};
  attempt(async()=>{const me=await call('/api/me');logout.textContent=me.username+' · 退出登录';if(me.role!=='admin'){dbButton.hidden=usersButton.hidden=true;document.querySelector('[data-tab="settings"]').hidden=true;document.getElementById('simulation-tab').hidden=true;document.getElementById('fw-host').closest('section').hidden=true;menu.querySelectorAll('button').forEach(b=>{if(b.textContent==='日志转发')b.hidden=true})}});
})();
