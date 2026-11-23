// ============================================================
// 文件名称：simulation.js
// 生成日期：2026-11-21
// 修改日期：2026-11-21
// 版本信息：v0.261115
// 作者：JUN
// 备注：本程序由AI辅助完成。
// 文件功能用途：提供攻击模拟场景选择、回放验证及结果展示。
// 注意事项：固定样例仅供本机内部验证，不支持任意外部攻击目标。
// ============================================================
let simulationBusy = false;
const simulationView = document.getElementById('simulation-view');
document.querySelectorAll('[data-tab]').forEach(button => {
  button.addEventListener('click', () => { simulationView.hidden = true; });
});

document.getElementById('simulation-tab').onclick = async () => {
  document.getElementById('events-view').hidden = true;
  document.getElementById('extra').hidden = true;
  simulationView.hidden = false;
  if (!document.querySelector('[name="simulation-case"]')) {
    try {
      const catalog = await api('/api/simulations/cases');
      const list = document.getElementById('case-list');
      for (const item of catalog.items) {
        const block = document.createElement('details');
        block.className = 'card';
        block.style.marginBottom = '10px';
        const heading = document.createElement('summary');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox'; checkbox.name = 'simulation-case'; checkbox.value = item.id;
        checkbox.style.width = 'auto'; checkbox.checked = true;
        checkbox.setAttribute('aria-label', item.name);
        heading.append(checkbox, document.createTextNode(' ' + item.name));
        const preview = document.createElement('pre');
        preview.textContent = item.method + ' ' + item.path + '\n' + (item.body || '') +
          '\n预期识别：' + (item.expected || '无攻击特征（对照组）');
        block.append(heading, preview); list.append(block);
      }
    } catch (error) { simulationNotice(error.message); }
  }
  refreshSimulationHistory();
};

function simulationNotice(message) { document.getElementById('simulation-notice').textContent = message; }
function renderSimulation(run, container) {
  container.replaceChildren();
  const summary = document.createElement('p');
  const passed = run.results.filter(item => item.passed).length;
  summary.textContent = `任务 ${run.id} ｜ 状态 ${run.status} ｜ 通过 ${passed}/${run.results.length}`;
  container.append(summary);
  for (const result of run.results) {
    const line = document.createElement('p');
    line.textContent = `${result.passed ? '通过' : '未通过'} · ${result.name} · HTTP ${result.status} · 实际识别：${result.detected.join('、') || '无'}　`;
    const button = document.createElement('button'); button.textContent = '请求详情';
    button.onclick = () => show(result.event_id);
    line.append(button); container.append(line);
  }
}
async function refreshSimulationHistory() {
  try {
    const data = await api('/api/simulations/runs');
    const list = document.getElementById('simulation-runs'); list.replaceChildren();
    for (const run of data.items) {
      const block = document.createElement('details'), heading = document.createElement('summary');
      heading.textContent = new Date(run.time).toLocaleString() + ' · ' + run.status + ' · ' + run.id;
      const report = document.createElement('div'); renderSimulation(run, report);
      block.append(heading, report); list.append(block);
    }
  } catch (error) { simulationNotice(error.message); }
}
document.getElementById('select-cases').onclick = () => {
  const boxes = [...document.querySelectorAll('[name="simulation-case"]')];
  const checked = !boxes.every(box => box.checked); boxes.forEach(box => { box.checked = checked; });
};
document.getElementById('simulation-history').onclick = refreshSimulationHistory;
document.getElementById('run-cases').onclick = async () => {
  if (simulationBusy) return;
  const ids = [...document.querySelectorAll('[name="simulation-case"]:checked')].map(box => box.value);
  if (!ids.length) { simulationNotice('请至少选择一个场景'); return; }
  simulationBusy = true;
  const button = document.getElementById('run-cases'); button.disabled = true;
  simulationNotice('正在执行模拟，请稍候……');
  try {
    const run = await write('/api/simulations/run', 'POST', 'simulation', {case_ids: ids});
    renderSimulation(run, document.getElementById('simulation-result'));
    simulationNotice(run.status === 'completed' ? '模拟完成。采集记录已标记为模拟流量。' : '模拟任务失败，已保存部分结果，请检查服务日志。');
    await refreshSimulationHistory();
  } catch (error) { simulationNotice(error.message); }
  finally { simulationBusy = false; button.disabled = false; }
};
