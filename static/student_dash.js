// ── Section switcher ─────────────────────────────────────────────────────────
function showSection(name) {
  document.querySelectorAll('.sd-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.sd-sidebar .nav-item').forEach(n => n.classList.remove('active'));
  const sec = document.getElementById('section-' + name);
  const nav = document.getElementById('nav-' + name);
  if (sec) sec.classList.add('active');
  if (nav) nav.classList.add('active');
  if (name === 'notifications') markRead();
}

function markRead() {
  fetch('/student/notifications/read', {method:'POST'})
    .then(() => {
      document.querySelectorAll('[id^="nav-notifications"] span').forEach(e => e.remove());
    });
}

// ── Applications tab switcher ─────────────────────────────────────────────────
function switchTab(name) {
  ['applied','interviews','offers','drives'].forEach(t => {
    document.getElementById('apptab-' + t).style.display = (t === name) ? 'block' : 'none';
    const btn = document.getElementById('tab-' + t);
    if (btn) btn.classList.toggle('active', t === name);
  });
}

// ── Drive search + filter ─────────────────────────────────────────────────────
function filterDrives() {
  const q = document.getElementById('drive-search').value.toLowerCase();
  const status = document.getElementById('drive-filter-status').value;
  const cards = document.querySelectorAll('.drive-card');
  let visible = 0;
  cards.forEach(c => {
    const textMatch = !q || c.dataset.company.includes(q) || c.dataset.role.includes(q) || c.dataset.location.includes(q);
    const statusMatch = !status || c.dataset.applied === status;
    const show = textMatch && statusMatch;
    c.style.display = show ? 'block' : 'none';
    if (show) visible++;
  });
  document.getElementById('drives-empty').style.display = visible === 0 ? 'block' : 'none';
}

// ── URL param auto-open ───────────────────────────────────────────────────────
(function () {
  const p = new URLSearchParams(window.location.search).get('section');
  if (p) showSection(p);
})();

// ── Photo / Resume upload relay ───────────────────────────────────────────────
function submitPhotoForm(input) {
  const dt = new DataTransfer();
  dt.items.add(input.files[0]);
  document.getElementById('photo-form-input').files = dt.files;
  document.getElementById('photo-form').submit();
}
function submitResumeForm(input) {
  const dt = new DataTransfer();
  dt.items.add(input.files[0]);
  document.getElementById('resume-form-input').files = dt.files;
  document.getElementById('resume-form').submit();
}

// ── Demo Tests navigation ─────────────────────────────────────────────────────
const TEST_NAMES = { resume:'Resume Matching', aptitude:'Aptitude Test', coding:'Coding Test', mock:'Mock Interviews', feedback:'Feedback' };
const STUDENT_ID = window._studentId || '0';

function getTestCounts() { try { return JSON.parse(localStorage.getItem('tc_' + STUDENT_ID) || '{}'); } catch(e) { return {}; } }
function incTestCount(name) {
  const c = getTestCounts(); c[name] = (c[name] || 0) + 1;
  localStorage.setItem('tc_' + STUDENT_ID, JSON.stringify(c));
  refreshCountBadges();
}
function refreshCountBadges() {
  const c = getTestCounts();
  ['resume','aptitude','coding','mock'].forEach(n => {
    const el = document.getElementById('cnt-' + n);
    if (!el) return;
    if (c[n]) { el.textContent = c[n] + ' taken'; el.style.display = 'inline-flex'; }
    else el.style.display = 'none';
  });
}

function openTestPage(name) {
  document.getElementById('tests-home').style.display = 'none';
  document.getElementById('tests-page').style.display = 'block';
  document.getElementById('breadcrumb-label').textContent = TEST_NAMES[name] || name;
  ['resume','aptitude','coding','mock','feedback'].forEach(t => {
    document.getElementById('tp-' + t).style.display = (t === name) ? 'block' : 'none';
  });
  if (name === 'feedback') loadFeedbackDashboard();
  document.getElementById('section-tests').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeTestPage() {
  document.getElementById('tests-page').style.display = 'none';
  document.getElementById('tests-home').style.display = 'block';
  refreshCountBadges();
}

document.addEventListener('DOMContentLoaded', refreshCountBadges);

// ── Resume Matching ───────────────────────────────────────────────────────────
let rmResumeText = '';

function rmLoadFile(input) {
  const file = input.files[0];
  if (!file) return;
  document.getElementById('rm-file-name').textContent = file.name;
  document.getElementById('rm-file-status').style.display = 'block';
  const reader = new FileReader();
  reader.onload = e => { rmResumeText = e.target.result; };
  reader.readAsText(file);
}

function rmAnalyze() {
  const jd = document.getElementById('rm-jd-text').value.trim();
  if (!jd) { alert('Please paste a job description.'); return; }
  document.getElementById('rm-result-empty').style.display = 'none';
  document.getElementById('rm-result-output').style.display = 'none';
  document.getElementById('rm-loading').style.display = 'block';
  document.getElementById('rm-analyze-btn').disabled = true;

  const fileInput = document.getElementById('rm-resume-input');
  const file = fileInput.files[0];

  const formData = new FormData();
  formData.append('jd', jd);
  if (file) {
    formData.append('resume', file);
  }

  fetch('/ai/resume_match', { method: 'POST', body: formData })
    .then(r => r.json()).then(data => {
      if (data.error) {
        throw new Error(data.error);
      }
      const pct = data.score;

      document.getElementById('rm-loading').style.display = 'none';
      document.getElementById('rm-result-output').style.display = 'block';

      const circumference = 352;
      const circle = document.getElementById('rm-score-circle');
      circle.style.strokeDashoffset = circumference - (circumference * pct / 100);
      circle.style.stroke = pct >= 70 ? '#4f46e5' : pct >= 45 ? '#d97706' : '#dc2626';
      document.getElementById('rm-score-pct').textContent = pct + '%';

      const verdict = data.verdict;
      const summary = data.summary;
      document.getElementById('rm-verdict-text').textContent = verdict;
      document.getElementById('rm-verdict-summary').textContent = summary;

      document.getElementById('rm-skills-list').innerHTML = data.skills.map(s => {
        return `<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f3f4f6;">
          <span style="font-size:0.85rem;color:#374151;">${s.name}</span>
          <span style="font-size:0.82rem;font-weight:700;color:${s.matched ? '#059669' : '#dc2626'};">${s.score}%</span>
        </div>`;
      }).join('');

      document.getElementById('rm-analyze-btn').disabled = false;
      incTestCount('resume');
    }).catch(err => {
      document.getElementById('rm-loading').style.display = 'none';
      document.getElementById('rm-result-empty').style.display = 'block';
      const errMsg = err.message || 'Error analyzing. Please try again.';
      document.getElementById('rm-result-empty').innerHTML = `<p style="color:#dc2626;font-size:0.85rem;">${errMsg}</p>`;
      document.getElementById('rm-analyze-btn').disabled = false;
    });
}

// ── Aptitude Test ─────────────────────────────────────────────────────────────
const APT_Q = [
  {id:1,cat:'Quantitative',q:'If 8 workers complete a task in 12 days, how many workers finish it in 6 days?',opts:['12','16','14','10'],ans:1,exp:'8×12=96; 96÷6=16 workers.'},
  {id:2,cat:'Quantitative',q:'A train travels 360 km at 90 km/h. How long does the journey take?',opts:['3 hrs','4 hrs','5 hrs','2 hrs'],ans:1,exp:'360÷90=4 hours.'},
  {id:3,cat:'Quantitative',q:'What is 15% of 240?',opts:['32','36','40','38'],ans:1,exp:'0.15×240=36.'},
  {id:4,cat:'Quantitative',q:'If x+y=10 and x-y=4, what is x?',opts:['5','6','7','8'],ans:2,exp:'Add both: 2x=14 → x=7.'},
  {id:5,cat:'Quantitative',q:'A car depreciates 20% per year from $25,000. Value after 2 years?',opts:['$15,000','$16,000','$17,500','$18,000'],ans:1,exp:'25000×0.8×0.8=16,000.'},
  {id:6,cat:'Verbal',q:'Choose the word closest in meaning to EPHEMERAL:',opts:['Permanent','Fleeting','Substantial','Ancient'],ans:1,exp:'Ephemeral = short-lived.'},
  {id:7,cat:'Verbal',q:"Select the grammatically correct sentence:",opts:["He don't know","She goes to school daily","They was late","We is ready"],ans:1,exp:'B is correct.'},
  {id:8,cat:'Verbal',q:'Antonym of LUCID:',opts:['Clear','Obvious','Obscure','Vivid'],ans:2,exp:'Lucid = clear; antonym = obscure.'},
  {id:9,cat:'Verbal',q:'Fill the blank: Despite the rain, she _____ came to the party.',opts:['never','still','barely','hardly'],ans:1,exp:'"still" fits the contrast.'},
  {id:10,cat:'Verbal',q:'BENEVOLENT means:',opts:['Hostile','Kind-hearted','Greedy','Lazy'],ans:1,exp:'Benevolent = well-meaning.'},
  {id:11,cat:'Reasoning',q:'Odd one out: 2, 3, 5, 7, 9, 11',opts:['9','3','7','11'],ans:0,exp:'9 is not prime (3×3).'},
  {id:12,cat:'Reasoning',q:'If CODING = DPEJOH, what is MANGO?',opts:['NBMHP','NBNHP','NANHP','NBOHP'],ans:3,exp:'Each letter +1: NBOHP.'},
  {id:13,cat:'Reasoning',q:'A>B>C>D. Who is youngest?',opts:['A','B','C','D'],ans:3,exp:'D is youngest.'},
  {id:14,cat:'Reasoning',q:'What comes next: 1, 4, 9, 16, 25, ?',opts:['30','36','42','49'],ans:1,exp:'Squares: 6²=36.'},
  {id:15,cat:'Reasoning',q:'All A are B. No B is C. Conclusion?',opts:['Some A are C','No A is C','All C are A','All A are C'],ans:1,exp:'No A is C follows logically.'}
];
const aptS = { answers:{}, cur:0, qSec:60, tSec:900, qInt:null, tInt:null };

function aptStart() {
  document.getElementById('apt-start-screen').style.display = 'none';
  document.getElementById('apt-loading-screen').style.display = 'block';
  aptS.answers = {}; aptS.cur = 0; aptS.qSec = 60; aptS.tSec = 900;
  setTimeout(() => {
    document.getElementById('apt-loading-screen').style.display = 'none';
    document.getElementById('apt-test-screen').style.display = 'block';
    aptPalette(); aptRender(); aptTimers();
  }, 700);
}

function aptFmt(s) { const m = Math.floor(s/60), sec = s%60; return m + ':' + (sec<10?'0':'') + sec; }

function aptTimers() {
  clearInterval(aptS.qInt); clearInterval(aptS.tInt);
  aptS.qInt = setInterval(() => {
    aptS.qSec--;
    const el = document.getElementById('apt-q-timer');
    el.textContent = aptFmt(aptS.qSec);
    el.style.color = aptS.qSec<=15?'#dc2626':aptS.qSec<=30?'#d97706':'#111827';
    el.style.borderColor = aptS.qSec<=15?'#dc2626':aptS.qSec<=30?'#d97706':'#e2e5f0';
    if (aptS.qSec <= 0) { aptS.qSec = 60; aptS.cur < 14 ? (aptS.cur++, aptRender()) : aptSubmit(); }
  }, 1000);
  aptS.tInt = setInterval(() => {
    aptS.tSec--;
    const el = document.getElementById('apt-t-timer');
    el.textContent = aptFmt(aptS.tSec);
    el.style.color = aptS.tSec<=120?'#dc2626':aptS.tSec<=300?'#d97706':'#111827';
    if (aptS.tSec <= 0) aptSubmit();
  }, 1000);
}

function aptPalette() {
  document.getElementById('apt-palette').innerHTML = APT_Q.map((_,i) => {
    const isCur = i===aptS.cur, isAns = aptS.answers[i]!==undefined;
    return `<button onclick="aptJump(${i})" style="width:30px;height:30px;border-radius:6px;border:1.5px solid ${isCur?'#4f46e5':isAns?'#059669':'#e2e5f0'};background:${isCur?'#eef2ff':isAns?'#d1fae5':'#f8f9ff'};color:${isCur?'#4f46e5':isAns?'#059669':'#6b7280'};font-size:0.72rem;font-weight:700;cursor:pointer;">${i+1}</button>`;
  }).join('');
}

function aptRender() {
  const q = APT_Q[aptS.cur], sel = aptS.answers[aptS.cur];
  document.getElementById('apt-q-cat').textContent = q.cat;
  document.getElementById('apt-q-num').textContent = aptS.cur + 1;
  document.getElementById('apt-q-text').textContent = q.q;
  document.getElementById('apt-options').innerHTML = q.opts.map((opt,i) =>
    `<div onclick="aptSel(${i})" style="display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:9px;border:1.5px solid ${sel===i?'#4f46e5':'#e2e5f0'};background:${sel===i?'rgba(79,70,229,.06)':'#f8f9ff'};cursor:pointer;margin-bottom:8px;">
      <div style="width:26px;height:26px;border-radius:50%;border:1.5px solid ${sel===i?'#4f46e5':'#d1d5db'};display:flex;align-items:center;justify-content:center;font-size:0.72rem;font-weight:700;color:${sel===i?'#4f46e5':'#6b7280'};flex-shrink:0;">${String.fromCharCode(65+i)}</div>
      <span style="font-size:0.875rem;color:#374151;">${opt}</span>
    </div>`
  ).join('');
  document.getElementById('apt-prev-btn').style.opacity = aptS.cur===0?'0.4':'1';
  document.getElementById('apt-next-btn').style.display = aptS.cur===14?'none':'inline-flex';
  document.getElementById('apt-submit-btn').style.display = aptS.cur===14?'inline-flex':'none';
  aptPalette();
}

function aptSel(i) { aptS.answers[aptS.cur]=i; aptRender(); }
function aptJump(i) { aptS.cur=i; aptS.qSec=60; aptRender(); }
function aptPrev() { if(aptS.cur>0){aptS.cur--;aptS.qSec=60;aptRender();} }
function aptNext() { if(aptS.cur<14){aptS.cur++;aptS.qSec=60;aptRender();} }

function aptSubmit() {
  clearInterval(aptS.qInt); clearInterval(aptS.tInt);
  document.getElementById('apt-test-screen').style.display = 'none';
  document.getElementById('apt-result-screen').style.display = 'block';
  let correct = 0;
  const cats = {Quantitative:{c:0,t:0},Verbal:{c:0,t:0},Reasoning:{c:0,t:0}};
  APT_Q.forEach((q,i) => { cats[q.cat].t++; if(aptS.answers[i]===q.ans){correct++;cats[q.cat].c++;} });
  const pct = Math.round((correct/15)*100);
  document.getElementById('apt-score-num').textContent = correct;
  document.getElementById('apt-score-num').style.color = pct>=70?'#059669':pct>=45?'#d97706':'#dc2626';
  document.getElementById('apt-score-pct').textContent = pct+'%';
  document.getElementById('apt-cat-breakdown').innerHTML = Object.entries(cats).map(([c,s])=>`${c}: ${s.c}/${s.t} ✓`).join('<br>');
  document.getElementById('apt-review-list').innerHTML = APT_Q.map((q,i) => {
    const ok = aptS.answers[i]===q.ans;
    return `<div style="margin-bottom:10px;padding:12px;background:#f8f9ff;border:1px solid ${ok?'rgba(5,150,105,.2)':'rgba(220,38,38,.2)'};border-radius:9px;">
      <div style="font-size:0.72rem;font-weight:700;color:${ok?'#059669':'#dc2626'};margin-bottom:4px;">${ok?'✅':'❌'} Q${i+1} · ${q.cat}</div>
      <div style="font-size:0.82rem;color:#374151;margin-bottom:4px;">${q.q}</div>
      <div style="font-size:0.75rem;color:#6b7280;">Your: ${aptS.answers[i]!==undefined?q.opts[aptS.answers[i]]:'—'} | Correct: ${q.opts[q.ans]}</div>
      <div style="font-size:0.72rem;color:#9ca3af;margin-top:3px;">${q.exp}</div>
    </div>`;
  }).join('');
  incTestCount('aptitude');
}

// ── Coding Test ───────────────────────────────────────────────────────────────
const CODING_PROB = {
  title:'Two Sum', difficulty:'Medium',
  description:'Given an array of integers nums and an integer target, return indices of the two numbers that add up to target.\n\nExample: nums=[2,7,11,15], target=9 → [0,1]',
  test_cases:[{input:'[2,7,11,15], target=9',expected_output:'[0,1]'},{input:'[3,2,4], target=6',expected_output:'[1,2]'},{input:'[3,3], target=6',expected_output:'[0,1]'}],
  model_solution:'def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        comp = target - n\n        if comp in seen:\n            return [seen[comp], i]\n        seen[n] = i\n    return []'
};

function codingStart() {
  document.getElementById('coding-start-screen').style.display = 'none';
  document.getElementById('coding-loading-screen').style.display = 'block';
  setTimeout(() => {
    document.getElementById('coding-loading-screen').style.display = 'none';
    document.getElementById('coding-problem-screen').style.display = 'block';
    document.getElementById('coding-prob-title').textContent = CODING_PROB.title;
    document.getElementById('coding-prob-desc').textContent = CODING_PROB.description;
    document.getElementById('coding-difficulty').textContent = CODING_PROB.difficulty;
    document.getElementById('coding-test-cases').innerHTML = CODING_PROB.test_cases.map((tc,i) =>
      `<div style="background:#f8f9ff;border:1px solid #e2e5f0;border-radius:8px;padding:10px 12px;margin-bottom:6px;font-size:0.78rem;font-family:monospace;">
        <div style="font-size:0.68rem;color:#9ca3af;margin-bottom:3px;">Test ${i+1}</div>
        <div>Input: <span style="color:#059669;">${tc.input}</span></div>
        <div>Expected: <span style="color:#d97706;">${tc.expected_output}</span></div>
      </div>`
    ).join('');
    document.getElementById('coding-code-input').value = '# Write your solution here\ndef solution():\n    pass';
  }, 900);
}

function codingGrade() {
  const code = document.getElementById('coding-code-input').value.trim();
  document.getElementById('coding-problem-screen').style.display = 'none';
  document.getElementById('coding-result-screen').style.display = 'block';
  document.getElementById('coding-result-loading').style.display = 'block';
  document.getElementById('coding-result-output').style.display = 'none';
  setTimeout(() => {
    const hasLogic = code.length > 50 && !code.endsWith('pass');
    const score = hasLogic ? Math.floor(65 + Math.random()*30) : Math.floor(20 + Math.random()*30);
    const results = CODING_PROB.test_cases.map((_,i) => ({ passed: hasLogic && i<2, note: hasLogic&&i<2?'Correct output':'Edge case failed' }));
    document.getElementById('coding-result-loading').style.display = 'none';
    document.getElementById('coding-result-output').style.display = 'block';
    document.getElementById('coding-score-num').textContent = score;
    document.getElementById('coding-score-num').style.color = score>=70?'#059669':score>=45?'#d97706':'#dc2626';
    document.getElementById('coding-test-results').innerHTML = results.map((t,i) =>
      `<div style="padding:8px 12px;border-radius:8px;border:1px solid ${t.passed?'rgba(5,150,105,.3)':'rgba(220,38,38,.3)'};background:${t.passed?'rgba(5,150,105,.05)':'rgba(220,38,38,.05)'};margin-bottom:6px;font-size:0.78rem;">${t.passed?'✅':'❌'} Test ${i+1}: ${t.note}</div>`
    ).join('');
    document.getElementById('coding-feedback-text').textContent = hasLogic
      ? 'Good attempt! Focus on edge cases and consider time complexity. A hash map reduces complexity to O(n).'
      : 'Solution appears incomplete. Implement the logic and handle all test cases.';
    document.getElementById('coding-model-solution').value = CODING_PROB.model_solution;
    incTestCount('coding');
  }, 1500);
}

// ── Mock Interview ────────────────────────────────────────────────────────────
const HR_QS = [
  'Tell me about yourself.',
  'Where do you see yourself in 5 years?',
  'Describe a conflict you resolved in a team.',
  'What are your greatest strengths and weaknesses?',
  'Why do you want to join our company?'
];

function mockStart() {
  document.getElementById('mock-start-screen').style.display = 'none';
  document.getElementById('mock-questions-screen').style.display = 'block';
  document.getElementById('mock-q-list').innerHTML = HR_QS.map((q,i) =>
    `<div class="q-card" style="margin-bottom:12px;">
      <div class="q-num">Q${i+1}</div>
      <div style="font-weight:600;color:#111827;margin-bottom:8px;">${q}</div>
      <textarea style="width:100%;padding:10px 12px;border:1.5px solid #e2e5f0;border-radius:9px;font-size:0.85rem;font-family:'Inter',sans-serif;resize:vertical;min-height:70px;outline:none;color:#374151;" placeholder="Type your answer here…"></textarea>
    </div>`
  ).join('');
}

function mockSubmit() {
  const answers = [...document.querySelectorAll('#mock-q-list textarea')].map(t => t.value.trim());
  const filled = answers.filter(a => a.length > 0).length;
  const fb = document.getElementById('mock-feedback-output');
  if (!filled) { fb.innerHTML = '<p style="color:#dc2626;font-size:0.82rem;">Please answer at least one question.</p>'; return; }
  const tips = [
    'Use the STAR method (Situation, Task, Action, Result) for structured answers.',
    'Quantify achievements where possible — numbers make answers memorable.',
    'Keep each answer to 1–2 minutes when spoken aloud.',
    "Align your answers with the company's values and the role requirements.",
    'Practice out loud to improve fluency and reduce filler words.'
  ];
  fb.innerHTML = `<div style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:12px;padding:18px;margin-top:4px;">
    <div style="font-size:0.9rem;font-weight:700;color:#4f46e5;margin-bottom:10px;">🤖 AI Feedback</div>
    <p style="font-size:0.85rem;color:#374151;margin-bottom:10px;">You answered <strong>${filled}</strong> of 5 questions. Tips to improve:</p>
    <ul style="font-size:0.82rem;color:#374151;padding-left:18px;line-height:2.2;">
      ${tips.slice(0, Math.min(filled+1, 5)).map(t => `<li>${t}</li>`).join('')}
    </ul>
  </div>`;
  incTestCount('mock');
}

// ── Feedback Dashboard ────────────────────────────────────────────────────────
function loadFeedbackDashboard() {
  const c = getTestCounts();
  const hasAny = c.resume || c.aptitude || c.coding || c.mock;
  document.getElementById('fb-empty-state').style.display = hasAny ? 'none' : 'block';
  document.getElementById('fb-main-content').style.display = hasAny ? 'block' : 'none';
  if (!hasAny) return;

  const scores = [];
  if (c.resume)   scores.push({ label:'Resume Match',    val: c.resume   + ' run'+(c.resume>1?'s':''),   color:'#4f46e5' });
  if (c.aptitude) scores.push({ label:'Aptitude Tests',  val: c.aptitude + ' taken',                     color:'#059669' });
  if (c.coding)   scores.push({ label:'Coding Tests',    val: c.coding   + ' taken',                     color:'#d97706' });
  if (c.mock)     scores.push({ label:'Mock Interviews', val: c.mock     + ' done',                      color:'#7c3aed' });

  document.getElementById('fb-score-summary').innerHTML = scores.map(s =>
    `<div style="text-align:center;"><div style="font-size:1.4rem;font-weight:800;color:${s.color};">${s.val}</div><div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">${s.label}</div></div>`
  ).join('');

  document.getElementById('fb-loading-state').style.display = 'none';
  document.getElementById('fb-content-area').style.display = 'block';

  document.getElementById('fb-strengths-list').innerHTML = [
    'Consistent practice across multiple test types',
    'Technical skills aligned with industry requirements',
    'Strong academic foundation'
  ].map(s => `<div style="display:flex;gap:10px;align-items:flex-start;font-size:0.85rem;padding:8px 0;border-bottom:1px solid #f3f4f6;"><span style="color:#059669;font-weight:700;">✓</span><span style="color:#374151;">${s}</span></div>`).join('');

  document.getElementById('fb-improvements-list').innerHTML = [
    { area:'Aptitude Speed', priority:'High', detail:'Practice timed questions to improve speed under pressure.' },
    { area:'Coding Edge Cases', priority:'Medium', detail:'Focus on boundary conditions and null checks.' },
    { area:'Communication', priority:'Low', detail:'Structure answers using STAR method for clarity.' }
  ].map(a => `<div style="padding:10px 12px;background:#f8f9ff;border-radius:9px;border:1px solid #e2e5f0;margin-bottom:8px;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
      <span style="font-size:0.82rem;font-weight:600;color:#111827;">${a.area}</span>
      <span style="font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:20px;background:${a.priority==='High'?'#fee2e2':a.priority==='Medium'?'#fef3c7':'#d1fae5'};color:${a.priority==='High'?'#dc2626':a.priority==='Medium'?'#d97706':'#059669'};">${a.priority}</span>
    </div>
    <div style="font-size:0.78rem;color:#6b7280;">${a.detail}</div>
  </div>`).join('');

  document.getElementById('fb-study-plan').innerHTML = [
    { week:1, focus:'Quantitative Aptitude', tasks:['Practice 20 problems daily','Focus on time & work, percentages'] },
    { week:2, focus:'Verbal & Reasoning',    tasks:['Read editorials for vocabulary','Solve 15 reasoning puzzles daily'] },
    { week:3, focus:'Data Structures',       tasks:['Revise arrays, linked lists, trees','Solve 2 LeetCode problems daily'] },
    { week:4, focus:'Mock Tests & HR Prep',  tasks:['Take 2 full mock tests','Practice STAR method answers'] }
  ].map(w => `<div style="border-left:3px solid #4f46e5;padding:12px 16px;background:#f8f9ff;border-radius:0 9px 9px 0;margin-bottom:10px;">
    <div style="font-size:0.7rem;color:#4f46e5;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Week ${w.week} · ${w.focus}</div>
    ${w.tasks.map(t => `<div style="font-size:0.8rem;color:#6b7280;margin-bottom:3px;">→ <span style="color:#374151;">${t}</span></div>`).join('')}
  </div>`).join('');

  document.getElementById('fb-next-steps').innerHTML = [
    'Complete all 4 demo test types for a full assessment',
    'Apply to drives with AI match score above 70%',
    'Update your profile skills based on Resume Matching results',
    'Practice mock interviews daily for 15 minutes'
  ].map((s,i) => `<div style="display:flex;gap:12px;align-items:flex-start;padding:10px 12px;background:#f8f9ff;border-radius:9px;">
    <span style="width:24px;height:24px;border-radius:50%;background:#4f46e5;color:#fff;display:flex;align-items:center;justify-content:center;font-size:0.72rem;font-weight:700;flex-shrink:0;">${i+1}</span>
    <span style="font-size:0.82rem;color:#374151;">${s}</span>
  </div>`).join('');
}
