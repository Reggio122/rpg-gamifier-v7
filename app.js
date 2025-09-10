// v8 core logic — clean rewrite
const STORAGE_KEY = "rpg_v8_state";
function genId(){ return 'id'+Math.random().toString(36).slice(2,9) }
const fmtDate = (iso)=> iso? new Date(iso).toLocaleString() : '';

const defaultState = {
  xp:0, level:1, xpToLevel:100,
  stats:{STR:0, INT:0, CHA:0},
  avatar:"hero1.png",
  tasks:{inbox:[], short:[], mid:[], long:[], boss:[], archive:[]},
  rewards:[{id:genId(), title:"🍫 Сладость", cost:20, bought:false},{id:genId(), title:"☕ Час отдыха", cost:30, bought:false},{id:genId(), title:"🎮 Игровая сессия", cost:120, bought:false}],
  achievements:[{id:genId(), title:"Добро пожаловать!"}],
  xpLog:[]
};

let state = load() || seedDefault();

function load(){ try{ return JSON.parse(localStorage.getItem(STORAGE_KEY)); }catch(e){ return null; } }
function save(){ localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }

function seedDefault(){
  const s = JSON.parse(JSON.stringify(defaultState));
  s.tasks.short = [
    {id:genId(), title:"Читать 15 минут", XP:10, stat:"INT", when:null, done:false},
    {id:genId(), title:"Написать 200 слов", XP:10, stat:"INT", when:null, done:false},
    {id:genId(), title:"Пройти 1км", XP:10, stat:"STR", when:null, done:false},
    {id:genId(), title:"Написать 1 пост", XP:10, stat:"CHA", when:null, done:false}
  ];
  s.tasks.mid = [
    {id:genId(), title:"Записать подкаст", XP:30, stat:"CHA", when:null, done:false},
    {id:genId(), title:"Смонтировать видео", XP:30, stat:"INT", when:null, done:false},
    {id:genId(), title:"Смонтировать подкаст", XP:30, stat:"INT", when:null, done:false}
  ];
  s.tasks.long = [
    {id:genId(), title:"Выложить видео по Героям Энвелла", XP:100, stat:"CHA", when:null, done:false},
    {id:genId(), title:"Выложить подкаст", XP:100, stat:"CHA", when:null, done:false}
  ];
  s.tasks.boss = [{id:genId(), title:"Первое миллионое видео", XP:1000, stat:"CHA", when:null, done:false}];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); return s;
}

// API helper
async function api(path, body){
  const status = document.getElementById('apiStatus');
  if(!window.BOT_API_BASE || String(window.BOT_API_BASE).includes("REPLACE")){ status.textContent='API: offline'; return null; }
  status.textContent = 'API: online';
  try{
    const res = await fetch(window.BOT_API_BASE + path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body||{})});
    return res.ok? res.json() : null;
  }catch(e){ console.warn(e); return null; }
}

// Rendering
function el(tag, cls, html){ const d=document.createElement(tag); if(cls) d.className=cls; if(html!==undefined) d.innerHTML = html; return d; }

function taskRow(t, bucket){
  const row = el('div','item'+(t.done?' done':''));
  row.draggable = true; row.dataset.id = t.id; row.dataset.bucket = bucket;
  row.innerHTML = `
    <div>
      <input type="checkbox" class="chk" ${t.done?'checked':''}>
      <strong>${t.title}</strong>
      <span class="meta">+${t.XP} XP • ${t.stat}${t.when? ' • ⏰ '+fmtDate(t.when): ''}</span>
    </div>
    <div>
      <button class="btn" data-arc="${t.id}">📦</button>
      <button class="btn" data-del="${t.id}">🗑</button>
    </div>`;
  row.querySelector('.chk').addEventListener('change', ()=> toggleDone(t.id, bucket));
  row.querySelector('[data-arc]').addEventListener('click', ()=> archiveTask(t.id, bucket));
  row.querySelector('[data-del]').addEventListener('click', ()=> deleteTask(t.id, bucket));
  row.addEventListener('dragstart', e=>{ row.classList.add('drag'); e.dataTransfer.setData('text/plain', JSON.stringify({id:t.id, bucket})); });
  row.addEventListener('dragend', ()=> row.classList.remove('drag'));
  return row;
}

function render(){
  // hud
  document.getElementById('avatarImg').src = 'assets/'+state.avatar;
  document.getElementById('statSTR').textContent = state.stats.STR;
  document.getElementById('statINT').textContent = state.stats.INT;
  document.getElementById('statCHA').textContent = state.stats.CHA;
  document.getElementById('levelNum').textContent = state.level;
  document.getElementById('currentXP').textContent = getBalanceXP();
  const pct = Math.min(100, Math.round((state.xp/state.xpToLevel)*100));
  document.getElementById('xpFill').style.width = pct+'%';
  // inbox
  const inbox = document.getElementById('inboxList'); inbox.innerHTML='';
  state.tasks.inbox.forEach(t=> inbox.appendChild(taskRow(t,'inbox')));
  // buckets
  ['short','mid','long','boss'].forEach(b=>{
    const list = document.getElementById(b+'List'); list.innerHTML='';
    state.tasks[b].forEach(t=> list.appendChild(taskRow(t,b)));
  });
  // shop
  const shop = document.getElementById('shopList'); shop.innerHTML='';
  state.rewards.forEach(r=>{
    const can = getBalanceXP() >= r.cost && !r.bought;
    const row = el('div','item',`<div><strong>${r.title}</strong> <span class="meta">(${r.cost} XP)</span></div>
      <div><button class="btn primary" ${can?'':'disabled'} data-buy="${r.id}">${r.bought?'✓':'Купить'}</button> <button class="btn" data-del="${r.id}">🗑</button></div>`);
    row.querySelector('[data-buy]').addEventListener('click', ()=> buyReward(r.id));
    row.querySelector('[data-del]').addEventListener('click', ()=> deleteReward(r.id));
    shop.appendChild(row);
  });
  // achievements
  const ach = document.getElementById('achList'); ach.innerHTML='';
  state.achievements.forEach(a=> ach.appendChild(el('div','badge', a.title)));
}

// Actions
function addInboxTask(title, XP, stat, when){
  state.tasks.inbox.unshift({id:genId(), title, XP, stat, when, done:false}); save(); render();
  api('/register_reminder', {chat_id:'default', task:{title, XP, when}});
}
function moveTask(id, from, to){
  const src = state.tasks[from]; const idx = src.findIndex(x=>x.id===id); if(idx===-1) return;
  const [it] = src.splice(idx,1); state.tasks[to].unshift(it); save(); render();
}
function toggleDone(id, bucket){
  const list = state.tasks[bucket]; const t = list.find(x=>x.id===id); if(!t) return;
  if(t.done){ t.done=false; save(); render(); return; }
  t.done=true;
  state.xp += t.XP;
  const k = t.stat||'STR'; state.stats[k] = (state.stats[k]||0) + Math.max(1, Math.round(t.XP/10));
  state.xpLog.unshift({ts:Date.now(), amount:t.XP, note:'Task: '+t.title});
  // level up
  while(state.xp >= state.xpToLevel){
    state.xp -= state.xpToLevel; state.level++; state.xpToLevel = Math.round(state.xpToLevel*1.12);
    state.achievements.unshift({id:genId(), title:'Новый уровень: '+state.level});
  }
  save(); render(); api('/task_completed', {chat_id:'default', task:{title:t.title, XP:t.XP}});
}
function archiveTask(id, bucket){ const list=state.tasks[bucket]; const idx=list.findIndex(x=>x.id===id); if(idx===-1) return; const [it]=list.splice(idx,1); state.tasks.archive.unshift(it); save(); render(); }
function deleteTask(id, bucket){ const list=state.tasks[bucket]; const idx=list.findIndex(x=>x.id===id); if(idx>-1){ list.splice(idx,1); save(); render(); } }

// Shop
function buyReward(id){
  const r = state.rewards.find(x=>x.id===id); if(!r) return;
  const bal = getBalanceXP();
  if(bal >= r.cost && !r.bought){ r.bought=true; state.xpLog.unshift({ts:Date.now(), amount:-r.cost, note:'Buy: '+r.title}); save(); render(); alert('Куплено: '+r.title); }
  else alert('Недостаточно XP');
}
function deleteReward(id){ const i=state.rewards.findIndex(x=>x.id===id); if(i>-1){ state.rewards.splice(i,1); save(); render(); } }

// Helpers
function getBalanceXP(){ const pos=state.xpLog.filter(l=>l.amount>0).reduce((s,l)=>s+l.amount,0); const neg=state.xpLog.filter(l=>l.amount<0).reduce((s,l)=>s+Math.abs(l.amount),0); return pos-neg; }

// UI bindings
document.getElementById('inboxAdd').addEventListener('click', ()=>{
  const t = document.getElementById('inboxText').value.trim(); if(!t) return;
  const xp = Number(document.getElementById('inboxXP').value)||10;
  const stat = document.getElementById('inboxStat').value||'STR';
  const when = document.getElementById('inboxDate').value? new Date(document.getElementById('inboxDate').value).toISOString(): null;
  addInboxTask(t,xp,stat,when);
  document.getElementById('inboxText').value=''; document.getElementById('inboxXP').value='10'; document.getElementById('inboxDate').value='';
});

document.querySelectorAll('.col .list, #inboxList').forEach(list=>{
  list.addEventListener('dragover', e=> e.preventDefault());
  list.addEventListener('drop', e=>{
    e.preventDefault();
    try{ const data = JSON.parse(e.dataTransfer.getData('text/plain')); const target = list.id.replace('List',''); moveTask(data.id, data.bucket, target); }catch(err){}
  });
});

document.getElementById('saveAvatar').addEventListener('click', async ()=>{
  const sel = document.getElementById('avatarSelect').value;
  state.avatar = sel; save(); render(); await api('/set_avatar', {chat_id:'default', avatar: sel});
});
document.getElementById('avatarSelect').addEventListener('change', e=>{ document.getElementById('avatarImg').src = 'assets/'+e.target.value; });

document.getElementById('askCoach').addEventListener('click', async ()=>{
  const box = document.getElementById('coachIdeas'); box.innerHTML = '<div class="idea">Мудрец размышляет…</div>';
  const resp = await api('/coach', {chat_id:'default', level: state.level, stats: state.stats, backlog: state.tasks.inbox.slice(0,5)});
  let ideas = [];
  if(resp && resp.ideas) ideas = resp.ideas;
  else ideas = ["⚡ 15 минут чтения", "✍️ 200 слов черновика", "🎥 30 минут монтажа", "📣 Запланировать пост"];
  box.innerHTML=''; ideas.forEach(text=>{ const b=el('div','idea',text); b.addEventListener('click', ()=> addInboxTask(text, 10, 'INT', null)); box.appendChild(b); });
});

render();
