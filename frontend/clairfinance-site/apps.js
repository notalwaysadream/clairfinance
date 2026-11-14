const $=s=>document.querySelector(s), main=$('#main');
const inr=n=>'₹'+Math.abs(Math.round(n)).toLocaleString('en-IN');
const ARR='<svg class="ar" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
const NAV=[['home','Home','<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>'],
['transactions','Transaction History','<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>'],
['whatif','Tools','<path d="M4 8h8m4 0h4M4 16h4m4 0h8"/><circle cx="14" cy="8" r="2"/><circle cx="10" cy="16" r="2"/>'],
['forecast','Forecast','<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>'],
['bills','Bills','<path d="M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2zM3 10h18M8 2v4M16 2v4"/>'],
['score','Finance Score','<path d="M4 18a8 8 0 1 1 16 0M12 18l4-5"/>'],
['anomalies','Anomalies','<path d="M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20.6h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01"/>']];
$('#nav').innerHTML=NAV.map(([k,t,p])=>`<a class="nav-i" href="#/${k}" data-k="${k}"><svg viewBox="0 0 24 24">${p}</svg><span>${t}</span></a>`).join('');

/* theme */
const setTheme=t=>{document.documentElement.dataset.theme=t;localStorage.setItem('cf-theme',t);$('.tl').textContent=t==='dark'?'Dark mode':'Light mode'};
setTheme(document.documentElement.dataset.theme);
$('#theme').onclick=()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');

/* login / sign out (placeholders) */
const afterLogin=()=>location.hash=localStorage.getItem('cf-data')?'#/home':'#/upload';
$('#loginForm').onsubmit=e=>{e.preventDefault();afterLogin()};
$('#gbtn').onclick=afterLogin;
$('#pwt').onclick=e=>{const i=$('#pw'),s=i.type==='password',b=e.currentTarget;i.type=s?'text':'password';b.setAttribute('aria-pressed',s);b.setAttribute('aria-label',s?'Hide password':'Show password')};
$('#out').onclick=()=>location.hash='#/login';

/* card effects (spotlight + ripple) */
document.addEventListener('pointermove',e=>{const c=e.target.closest('.card');if(!c)return;const r=c.getBoundingClientRect();c.style.setProperty('--mx',e.clientX-r.left+'px');c.style.setProperty('--my',e.clientY-r.top+'px')});
document.addEventListener('click',e=>{const c=e.target.closest('.card');if(!c)return;const r=c.getBoundingClientRect(),s=Math.max(r.width,r.height)/2,k=e.detail===0,x=k?r.width/2:e.clientX-r.left,y=k?r.height/2:e.clientY-r.top,d=document.createElement('span');d.className='ripple';Object.assign(d.style,{width:s+'px',height:s+'px',left:x-s/2+'px',top:y-s/2+'px'});d.onanimationend=()=>d.remove();c.appendChild(d)});

/* shared bits */
const hero=(t,img,cls)=>`<div class="hero ${cls||''}" style="${img?`--img:url(assets/${img})`:''}"><h1>${t}</h1></div>`;
const page=h=>`<div class="page">${h}</div>`;
const GAUGE=s=>`<span class="gauge"><svg viewBox="0 0 100 58"><defs><linearGradient id="gg" gradientUnits="userSpaceOnUse" x1="10" x2="90"><stop offset="0" stop-color="#ef4444"/><stop offset=".5" stop-color="#f59e0b"/><stop offset="1" stop-color="#22c55e"/></linearGradient></defs><path class="gt" d="M10 52A40 40 0 0 1 90 52" pathLength="100"/><path class="gf" d="M10 52A40 40 0 0 1 90 52" pathLength="100" style="--off:${100-s}"/></svg><span class="gn"><b id="sn">0</b><small>/100</small></span></span>`;
function countUp(t){const el=$('#sn');if(!el)return;const s=performance.now()+800;(function f(n){const p=Math.min(Math.max((n-s)/1600,0),1);el.textContent=Math.round(t*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(f)})(performance.now())}

/* home */
const ALERTS={shortfall:['Shortfall risk','You may run short around the 22nd','There is a 62% chance your balance drops below ₹5,000 before the 25th.'],bill:['Upcoming bill','You have a bill due in 3 weeks: ₹3,500','Electricity, due 5 December.'],anomaly:['Unusual spending','Your dining spend is 30% above your usual pattern','Most of it came from the last two weeks.'],ok:['All clear','You are up to date on your expenditures','No shortfalls or overdue bills in the next 30 days.']};
window.renderAlert=k=>{const a=ALERTS[k]||ALERTS.ok;$('#al').innerHTML=`<small>${a[0]}</small><h2>${a[1]}</h2><p>${a[2]}</p>`};
const IC={
transactions:'<svg viewBox="0 0 64 64"><g class="rw" style="--r:0"><circle cx="12" cy="16" r="4"/><path d="M24 16h30"/></g><g class="rw" style="--r:1"><circle cx="12" cy="32" r="4"/><path d="M24 32h24"/></g><g class="rw" style="--r:2"><circle cx="12" cy="48" r="4"/><path d="M24 48h28"/></g></svg>',
whatif:'<svg viewBox="0 0 64 64"><path d="M8 22h48M8 44h48"/><circle class="kn k1" cx="20" cy="22" r="6"/><circle class="kn k2" cx="44" cy="44" r="6"/></svg>',
forecast:'<svg viewBox="0 0 64 64"><path d="M8 8v48h50"/><polygon class="ff" points="36,34 56,14 56,34"/><polyline class="fl" points="12,46 22,38 30,42 36,34"/><polyline class="fd" points="36,34 56,22"/></svg>',
bills:'<svg viewBox="0 0 64 64"><g class="cal"><rect x="8" y="14" width="48" height="42" rx="8"/><path d="M8 28h48M22 8v10M42 8v10M20 40h4M32 40h4M44 40h4"/></g><circle class="bdg" cx="54" cy="12" r="6"/></svg>'};
const CARDS=[['transactions','Transaction History','Every transaction, categorized and searchable.'],['whatif','Tools','What-if checks, EMI optimizer, loan schedules and savings goals.'],['forecast','Forecast','See your balance 30 to 90 days ahead.'],['bills','Bills','Recurring bills and due-date reminders.']];
const PAGES={
home(){main.innerHTML=`<header class="banner"><div class="br"><svg><use href="#logo"/></svg><div class="wm">Clair<span>finance</span></div></div><p>Know if you’ll run out of money, and when, before it happens</p></header>`+page(`<a class="card alert" href="#/anomalies" style="--i:-1"><div class="al-i"><svg viewBox="0 0 24 24"><path d="M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20.6h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01"/></svg></div><div id="al" style="flex:1"></div>${ARR}</a><div class="grid">${CARDS.map(([k,t,d],i)=>`<a class="card" href="#/${k}" style="--i:${i}"><span class="ct"><span class="ic">${IC[k]}</span>${ARR}</span><span><h3>${t}</h3><p>${d}</p></span></a>`).join('')}<a class="card wide" href="#/score" style="--i:4">${GAUGE(72)}<span style="flex:1"><h3>Finance Score</h3><p>Your financial health at a glance, built from five factors.</p><span class="chips"><i>Savings rate</i><i>Cash buffer</i><i>EMI ratio</i><i>Spending stability</i><i>Shortfall risk</i></span></span>${ARR}</a></div>`);renderAlert('shortfall');countUp(72)},

transactions(){const T=[['Salary credit','Income',65000,3],['Swiggy','Food',-640,2],['Uber','Transport',-310,4],['Rent','Housing',-18000,5],['Amazon','Shopping',-2499,8],['Netflix','Subscriptions',-649,10],['Electricity bill','Utilities',-1850,12],['Freelance payment','Income',12000,15],['Home loan EMI','EMI',-9800,20],['Zomato','Food',-520,22],['Mutual fund SIP','Investments',-5000,27],['Salary credit','Income',65000,33],['Apollo Pharmacy','Healthcare',-780,35],['Flipkart','Shopping',-3999,48],['Udemy course','Education',-1199,60],['Salary credit','Income',65000,63],['Goa trip','Travel',-14500,95],['Salary credit','Income',65000,123],['Car service','Transport',-6200,150],['Diwali gifts','Gifts',-4800,200],['Salary credit','Income',65000,250]];
const cols=['#6366f1','#22d3ee','#22c55e','#f59e0b','#818cf8','#ef4444'],cats=[...new Set(T.map(t=>t[1]))];
main.innerHTML=hero('TRANSACTION HISTORY','money.avif')+page(`<section class="panel glass"><h3>Viewing options</h3><div class="bar"><label>Time period <select id="per"><option value="7">Past week</option><option value="30" selected>Past month</option><option value="90">Last 3 months</option><option value="180">Last 6 months</option><option value="365">Last year</option></select></label><span class="cat" id="cnt"></span></div></section><div class="stats" id="st"></div><section class="panel glass"><table id="tb"></table></section>`);
const draw=()=>{const n=+$('#per').value,L=T.filter(t=>t[3]<=n),inc=L.reduce((a,t)=>a+(t[2]>0?t[2]:0),0),exp=L.reduce((a,t)=>a+(t[2]<0?-t[2]:0),0);
$('#cnt').textContent=L.length+' transactions';
$('#st').innerHTML=[['Income',inr(inc),'ok'],['Spent',inr(exp),'bad'],['Net',(inc-exp<0?'−':'+')+inr(inc-exp),inc>=exp?'ok':'bad']].map(([a,b,c])=>`<div class="stat glass"><small>${a}</small><b class="${c}">${b}</b></div>`).join('');
$('#tb').innerHTML=L.map((t,i)=>`<tr style="animation-delay:${i*30}ms"><td><span class="dot" style="background:${cols[cats.indexOf(t[1])%6]}"></span>${t[0]}<div class="cat">${t[1]} · ${new Date(Date.now()-t[3]*864e5).toLocaleDateString('en-IN',{day:'numeric',month:'short'})}</div></td><td class="${t[2]>0?'ok':''}">${t[2]>0?'+':'−'}${inr(t[2])}</td></tr>`).join('')};
$('#per').onchange=draw;draw()},

whatif(){main.innerHTML=hero('TOOLS','ai.png')+page(`<div class="seg" id="jmp"><button data-to="s-wi">What-if</button><button data-to="s-eo">EMI optimizer</button><button data-to="s-la">Loan amortization</button><button data-to="s-sg">Savings goal</button></div><section class="panel glass" id="s-wi"><h3>What-if: can I afford it?</h3><div class="form"><label>What do you want to buy<input class="in" id="wi" value="Royal Enfield Himalayan 450"></label><label>Estimated price (₹)<input class="in" id="wp" type="number" value="285000"></label><label>Payment method<select id="wm"><option value="emi">EMI</option><option value="one">One-time</option><option value="loan">Loan</option></select></label><label class="tr">Tenure (months)<input class="in" id="wt" type="number" value="24"></label><label class="tr">Interest rate (% per year)<input class="in" id="wr" type="number" value="12.5"></label><label>Product link (optional)<input class="in" id="wl" placeholder="https://"></label><button class="btn" id="go">Check if I can afford it</button></div></section><section class="panel glass verdict" id="res" hidden></section>
<section class="panel glass" id="s-eo"><h3>EMI Debt Optimizer</h3><div class="form"><label>Borrowing amount (₹)<input class="in" id="eP" type="number" value="300000"></label><label>Tenure (months)<input class="in" id="eN" type="number" value="24"></label><label>Rate of interest (% per year)<input class="in" id="eR" type="number" value="12"></label><label>Down payment (₹)<input class="in" id="eD" type="number" value="50000"></label><button class="btn" id="eo">Optimize debt structure</button></div><div id="eres" class="verdict"></div></section>
<section class="panel glass" id="s-la"><h3>Loan Amortization</h3><div class="form"><label>Principal (₹)<input class="in" id="lP" type="number" value="500000"></label><label>Rate of interest (% per year)<input class="in" id="lR" type="number" value="10"></label><label>Tenure (months)<input class="in" id="lN" type="number" value="36"></label><button class="btn" id="la">Show repayment schedule</button></div><div id="lres" class="verdict"></div></section>
<section class="panel glass" id="s-sg"><h3>Savings Goal</h3><div class="form"><label>How much do you want to save (₹)<input class="in" id="gG" type="number" value="300000"></label><label>How much can you save each month (₹)<input class="in" id="gM" type="number" value="15000"></label><button class="btn" id="gb">Calculate timeline</button></div><div id="gres" class="verdict"></div></section>`);
$('#wm').onchange=()=>document.querySelectorAll('.tr').forEach(l=>l.style.display=$('#wm').value==='one'?'none':'');
$('#go').onclick=()=>{const P=+$('#wp').value,n=+$('#wt').value||1,r=+$('#wr').value/1200,one=$('#wm').value==='one',emi=one?0:(r?P*r*Math.pow(1+r,n)/(Math.pow(1+r,n)-1):P/n),S=18500,B=90000,q=one?P/B:emi/S,v=q<.3?['Easily affordable','ok']:q<.6?['Affordable with caution','warn']:q<1?['Risky','warn']:['Not recommended','bad'],after=one?B-P:S-emi,w=(a,b)=>Math.max(0,Math.min(100,a/b*100));
const R=$('#res');R.hidden=false;R.innerHTML=`<h2 class="${v[1]}">${v[0]}</h2><p>${$('#wi').value}: ${one?'paid once, '+inr(P)+' from your savings buffer':'about '+inr(emi)+' a month for '+n+' months'}.</p><div class="mini"><span>${one?'Savings buffer':'Monthly savings'} now</span><span class="tk"><i style="width:0;background:var(--ok)" data-w="${w(one?B:S,one?B:S)}"></i></span><b>${inr(one?B:S)}</b></div><div class="mini"><span>After purchase</span><span class="tk"><i style="width:0;background:var(--${after<0?'bad':v[1]})" data-w="${w(after,one?B:S)}"></i></span><b>${after<0?'−':''}${inr(after)}</b></div><p class="cat">Demo figures: ₹18,500 monthly savings and ₹90,000 buffer. These will come from /api/query/ask.</p>`;
requestAnimationFrame(()=>R.querySelectorAll('i').forEach(i=>i.style.width=i.dataset.w+'%'))};toolsExtra()},

forecast(){main.innerHTML=hero('FORECAST','eye.jpg')+page(`<section class="panel glass"><div class="bar"><h3 style="margin:0">Projected balance</h3><div class="seg" id="sg">${[30,60,90].map(n=>`<button data-n="${n}">${n} days</button>`).join('')}</div></div><svg class="chart" id="ch" viewBox="0 0 800 300"></svg></section><section class="panel glass" id="fp"></section>`);
const m=d=>36000-520*d+3000*Math.sin(d/6),sp=d=>1500+190*d,Y=v=>270-Math.max(0,Math.min(45000,v))/45000*250;
const draw=n=>{const X=d=>50+d/n*730,ds=[...Array(n+1).keys()],P=f=>ds.map(d=>X(d)+','+Y(f(d))).join(' '),B=(k,c)=>`<polygon class="band" fill="${c}" points="${P(d=>m(d)+k*sp(d))} ${[...ds].reverse().map(d=>X(d)+','+Y(m(d)-k*sp(d))).join(' ')}"/>`;
$('#ch').innerHTML=[0,15000,30000,45000].map(v=>`<line x1="50" x2="780" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--bd)"/><text x="6" y="${Y(v)+4}">${v/1000}k</text>`).join('')+B(1,'#6366f1')+B(.45,'#22d3ee')+`<line x1="50" x2="780" y1="${Y(5000)}" y2="${Y(5000)}" stroke="var(--bad)" stroke-dasharray="6 5"/><text x="620" y="${Y(5000)-6}" style="fill:var(--bad)">Danger line ₹5,000</text><polyline fill="none" stroke="var(--fg)" stroke-width="3" stroke-linecap="round" points="${P(m)}"/><text x="50" y="292">Today</text><text x="760" y="292">Day ${n}</text>`;
const z=(5000-m(n))/(sp(n)/1.64),p=Math.round(100/(1+Math.exp(-1.702*z)));
$('#fp').innerHTML=`<h3>Shortfall risk</h3><p><b class="${p>50?'bad':p>20?'warn':'ok'}" style="font:600 36px var(--hd)">${p}%</b> chance your balance is below ₹5,000 by day ${n}.</p><p class="cat">Shaded bands show the likely range (50% and 90%). Illustrative data until /api/forecast/cashflow is connected.</p>`;
document.querySelectorAll('#sg button').forEach(b=>b.classList.toggle('on',+b.dataset.n===n))};
$('#sg').onclick=e=>e.target.dataset.n&&draw(+e.target.dataset.n);draw(60)},

bills(){const B=[['Electricity',1850,5,'est.'],['Water',420,9,'est.'],['Broadband',799,12],['Home loan EMI',9800,18],['Netflix',649,21],['Mobile recharge',299,26]];
main.innerHTML=hero('BILLS','bulb.jpg')+page(`<div class="stats" id="bs"></div><div id="bl" style="display:grid;gap:14px"></div>`);
const st=B.map((b,i)=>({on:i<4,paid:false})),draw=()=>{const due=B.reduce((a,b,i)=>a+(st[i].paid?0:b[1]),0);$('#bs').innerHTML=[['Total due',inr(due),''],['Due this week',B.filter((b,i)=>!st[i].paid&&b[2]<=7).length+' bills','warn'],['Paid',st.filter(s=>s.paid).length+' of '+B.length,'ok']].map(([a,b,c])=>`<div class="stat glass"><small>${a}</small><b class="${c}">${b}</b></div>`).join('');
$('#bl').innerHTML=B.map((b,i)=>`<div class="bill card${st[i].paid?' paid':''}" style="animation-delay:${i*70}ms;min-height:0;cursor:default"><div class="g"><b>${b[0]}</b><br><small>${b[3]?'Estimated ':''}${inr(b[1])}</small></div><span class="chip ${b[2]<=7?'warn':''}">Due in ${b[2]} days</span><small>Alert</small><button class="sw${st[i].on?' on':''}" data-a="${i}" aria-label="Alerts for ${b[0]}"></button><button class="sm" data-p="${i}">${st[i].paid?'Undo':'Mark paid'}</button></div>`).join('')};
$('#main').onclick=e=>{const a=e.target.dataset.a,p=e.target.dataset.p;if(a!=null)st[a].on=!st[a].on;else if(p!=null)st[p].paid=!st[p].paid;else return;draw()};draw()},

anomalies(){const A=[['Goa trip, MakeMyTrip','Travel',14500,12,'3.2× your usual travel spending',82],['Flipkart Electronics','Shopping',3999,9,'Largest shopping charge in 3 months',71],['Swiggy, 6 orders in 4 days','Food',3240,6,'Dining is 30% above your usual pattern',64],['Netflix, charged twice','Subscriptions',649,3,'Duplicate charge within 3 days',58]],tot=A.reduce((a,r)=>a+r[2],0);
main.innerHTML=hero('ANOMALIES','danger.jpg','danger')+page(`<section class="panel glass"><h3>Transactions flagged as anomalies</h3><p class="cat">These ${A.length} transactions triggered your shortfall alert. Together they add ${inr(tot)} of unusual spending in the last 30 days.</p><div style="display:grid;gap:12px;margin-top:16px">${A.map((r,i)=>`<div class="an" style="animation-delay:${i*80}ms"><div class="g"><b>${r[0]}</b><div class="cat">${r[1]} · ${new Date(Date.now()-r[3]*864e5).toLocaleDateString('en-IN',{day:'numeric',month:'short'})} · ${r[4]}</div></div><b>${inr(r[2])}</b><span class="chip ${r[5]>=75?'bad':'warn'}">${r[5]>=75?'High':'Warning'} (${r[5]}%)</span></div>`).join('')}</div><p class="cat" style="margin-top:14px">Demo data until /api/anomalies is connected.</p></section>`)},

score(){const F=[['Savings rate',14],['Cash buffer',9],['Spending stability',5],['EMI ratio',-8],['Shortfall risk',-6]];
main.innerHTML=hero('FINANCE SCORE','gauge.webp','contain')+page(`<section class="panel glass scorehead">${GAUGE(72)}<div><h3>Good, with room to improve</h3><p class="cat">Base 58 plus the impact of five factors. Demo data until /api/dashboard/health-score is connected.</p></div></section><section class="panel glass"><h3>Impact on your score</h3>${F.map(([n,v])=>`<div class="imp"><span>${n}</span><span class="ax"><i data-v="${v}" style="${v>0?'left:50%;background:var(--ok)':'right:50%;background:var(--bad)'}"></i></span><b class="${v>0?'ok':'bad'}">${v>0?'+':'−'}${Math.abs(v)}</b></div>`).join('')}<p class="cat">Green bars raise your score. Red bars lower it. Fixing the EMI ratio is the biggest opportunity.</p></section><section class="panel glass arch"><h3>Spending Archetype</h3><div class="arch-n grad">${ARCH.name}</div><p>${ARCH.desc}</p><div class="arch-g"><div class="arch-c"><b class="ok">Strength</b><p>${ARCH.strength}</p></div><div class="arch-c v"><b class="warn">Vulnerability</b><p>${ARCH.weak}</p></div></div><div class="tip"><b>Advisor tip:</b> ${ARCH.tip}</div><p class="cat" style="margin-top:14px">Placeholder values until the backend is connected.</p></section>`);
countUp(72);requestAnimationFrame(()=>document.querySelectorAll('.imp i').forEach(i=>i.style.width=Math.abs(i.dataset.v)/16*50+'%'))}};

/* Tools: EMI optimizer, loan amortization, savings goal (demo math, replace with /api/simulator/*) */
function toolsExtra(){
const E=(P,r,n)=>r?P*r*Math.pow(1+r,n)/(Math.pow(1+r,n)-1):P/n,m2=n=>'₹'+n.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}),v=id=>+$('#'+id).value,INC=65000,EX=9800;
$('#jmp').onclick=e=>{const t=e.target.dataset.to;t&&$('#'+t).scrollIntoView({behavior:'smooth',block:'start'})};
$('#eo').onclick=()=>{const P=v('eP'),n=v('eN')||1,r=v('eR')/1200,d=Math.min(v('eD'),P),b=E(P,r,n),bi=b*n-P,dti=e=>((EX+e)/INC*100).toFixed(1)+'%',rows=[['Standard Direct Financing','Add the new EMI of '+m2(b)+' to your existing obligations for '+n+' months.',b,bi,0,'Baseline','']];
 if(d>0){const e2=E(P-d,r,n),i2=e2*n-(P-d);rows.push(['Lump-Sum Down Payment ('+inr(d)+')','Pay '+inr(d)+' upfront to cut the principal to '+inr(P-d)+'.',e2,i2,bi-i2,'Highly Recommended','g'])}
 const e3=E(P,r,n+12),i3=e3*(n+12)-P;rows.push(['Tenure Extension ('+(n+12)+' Months)','Extend by 12 months to ease your monthly EMI.',e3,i3,bi-i3,'Viable Alternative','']);
 $('#eres').innerHTML=`<p>Borrowing ${inr(P)} adds ${m2(b)}/month to your existing ${inr(EX)} debt. Total obligations would be ${dti(b)} of your monthly income${d>0?'. Your '+inr(d)+' down payment saves interest and lowers DTI.':'.'}</p><div class="tw"><table><tr><th>Strategy</th><th>Monthly EMI</th><th>Total interest</th><th>Interest saved</th><th>DTI</th><th>Level</th></tr>${rows.map(r=>`<tr><td><b>${r[0]}</b><div class="cat">${r[1]}</div></td><td>${m2(r[2])}</td><td>${m2(r[3])}</td><td class="${r[4]<0?'bad':'ok'}">${r[4]<0?'−':''}${m2(Math.abs(r[4]))}</td><td>${dti(r[2])}</td><td><span class="lv ${r[6]}">${r[5]}</span></td></tr>`).join('')}</table></div><p class="cat">Demo assumptions: ₹65,000 monthly income, ${inr(EX)} existing EMI.</p>`};
$('#la').onclick=()=>{const P=v('lP'),r=v('lR')/1200,n=v('lN')||1,e=E(P,r,n),S=[];let bal=P;for(let i=1;i<=n;i++){const it=bal*r,pr=e-it;bal=Math.max(0,bal-pr);S.push([i,e,pr,it,bal])}
 const rows=a=>a.map(s=>`<tr><td>${s[0]}</td><td>${m2(s[1])}</td><td>${m2(s[2])}</td><td>${m2(s[3])}</td><td>${m2(s[4])}</td></tr>`).join(''),sh=Math.round(P/(e*n)*100);let all=false;
 $('#lres').innerHTML=`<div class="stats"><div class="stat glass"><small>Monthly EMI</small><b>${m2(e)}</b></div><div class="stat glass"><small>Total interest</small><b class="warn">${m2(e*n-P)}</b></div><div class="stat glass"><small>Total payable</small><b>${m2(e*n)}</b></div></div><div class="mini"><span>Principal share</span><span class="tk"><i style="width:${sh}%;background:var(--pri)"></i></span><b>${sh}%</b></div><div class="tw"><table><tr><th>Month</th><th>EMI</th><th>Principal</th><th>Interest</th><th>Balance</th></tr><tbody id="lb">${rows(S.slice(0,12))}</tbody></table></div>${n>12?'<button class="sm" id="lm">Show all '+n+' months</button>':''}`;
 const b=$('#lm');if(b)b.onclick=()=>{all=!all;$('#lb').innerHTML=rows(all?S:S.slice(0,12));b.textContent=all?'Show first 12 months':'Show all '+n+' months'}};
$('#gb').onclick=()=>{const G=v('gG'),M=v('gM');if(!(G>0&&M>0))return;const n=Math.ceil(G/M),S=18500,f=M<=S*.5?['Comfortably achievable','ok']:M<=S?['Achievable with budgeting','warn']:['Stretch goal','bad'],n2=Math.ceil(G/(M*1.15));
 $('#gres').innerHTML=`<p><b>Estimated timeline:</b> ${n} months (${(n/12).toFixed(1)} years) <span class="chip ${f[1]}">${f[0]}</span></p><p><b>Monthly required:</b> ${inr(M)}</p><ul class="tips"><li>Automate a transfer on salary day.</li><li>Saving 15% more each month finishes in ${n2} months instead of ${n}.</li><li>Send any bonus or tax refund straight to this goal.</li></ul><p class="cat">Demo assumption: ₹18,500 monthly surplus.</p>`}}

/* Spending archetype (placeholder values, replace with backend data) */
const ARCH={name:'Diligent Capital Builder',desc:'Maintains disciplined financial control, allocating a consistent surplus toward savings and long-term security.',strength:'Predictable surplus and robust emergency protection.',weak:'Risk of keeping surplus idle in low-yield savings accounts.',tip:'Channel idle cash reserves into systematic investment plans (SIPs) to outpace inflation.'};

/* CSV upload (first-time setup) */
const csv=$('#csv'),drop=$('#drop'),DT='Drag and drop your CSV here',DS='or click to browse. Needs date, description and amount columns.';
let upFile=null;
const fail=m=>{drop.className='drop err';$('#dt').textContent='File not accepted';$('#ds').textContent=m};
function pick(f){drop.className='drop';upFile=null;$('#cont').disabled=true;if(!f)return;
 if(!/\.csv$/i.test(f.name))return fail('That is not a CSV file. Export your statement as .csv and try again.');
 f.text().then(t=>{const L=t.split(/\r?\n/).filter(Boolean),h=(L[0]||'').split(',');
  if(L.length<2||!h.some(x=>/date/i.test(x))||!h.some(x=>/amount|debit|credit|withdrawal|deposit/i.test(x)))return fail('We could not find the columns we need. Include a date column and an amount (or debit and credit) column.');
  upFile=f;drop.className='drop ok';$('#dt').textContent=f.name;$('#ds').textContent=(L.length-1)+' transactions found, '+(f.size/1024).toFixed(1)+' KB. Click to choose a different file.';$('#cont').disabled=false})}
function resetUp(){csv.value='';pick(null);$('#dt').textContent=DT;$('#ds').textContent=DS;$('#pg').hidden=$('#pt').hidden=true;$('#pg').firstElementChild.style.width=0}
csv.onchange=()=>pick(csv.files[0]);
['dragenter','dragover'].forEach(v=>drop.addEventListener(v,e=>{e.preventDefault();drop.classList.add('over')}));
['dragleave','drop'].forEach(v=>drop.addEventListener(v,e=>{e.preventDefault();drop.classList.remove('over')}));
drop.addEventListener('drop',e=>pick(e.dataTransfer.files[0]));
const finish=k=>{localStorage.setItem('cf-data',k);location.hash='#/home'};
$('#demo').onclick=()=>finish('demo');
$('#cont').onclick=()=>{ // TODO: send upFile as FormData to POST /api/transactions/upload
 $('#cont').disabled=true;const pg=$('#pg'),pt=$('#pt'),S=['Reading your transactions…','Categorizing spending…','Finding recurring payments…','Building your forecast…'];pg.hidden=pt.hidden=false;
 S.forEach((m,i)=>setTimeout(()=>{pt.textContent=m;pg.firstElementChild.style.width=(i+1)*25+'%'},i*600));setTimeout(()=>finish('csv'),S.length*600+200)};
$('#smp').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['date,description,amount\n2026-11-01,Salary credit,65000\n2026-11-02,Swiggy,-640\n2026-11-05,Rent,-18000\n2026-11-08,Amazon,-2499\n'],{type:'text/csv'}));a.download='sample-transactions.csv';a.click()};

/* router */
function route(){const k=location.hash.slice(2)||'login';
if(k==='upload'){document.body.dataset.view='upload';resetUp();return}
if(k!=='login'&&PAGES[k]&&!localStorage.getItem('cf-data')){location.hash='#/upload';return}
document.body.dataset.view=k==='login'||!PAGES[k]?'login':k;if(document.body.dataset.view==='login')return;
document.querySelectorAll('.nav-i[data-k]').forEach(a=>a.classList.toggle('on',a.dataset.k===k));scrollTo(0,0);PAGES[k]()}
addEventListener('hashchange',route);route();
