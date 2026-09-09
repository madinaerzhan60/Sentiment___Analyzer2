"use strict";
const $ = s => document.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const state = {data:null, view:"dashboard", page:1, query:"", source:"", sentiment:"", busy:false, report:"Executive Reputation Summary", config:null};
const topics = {response_time:"Response time",staff_behavior:"Staff conduct",service_quality:"Service quality",product_quality:"Product quality",pricing:"Pricing",communication:"Communication",waiting_time:"Waiting time",other:"Other feedback"};
const colors = {positive:"#20A464",neutral:"#D99A22",negative:"#D64545"};
const names = {Google:"Google Maps",Yandex:"Yandex Maps",CSV:"CSV Import"};
const nav = {dashboard:"Dashboard",reviews:"Reviews",analytics:"Analytics",insights:"AI Insights",sources:"Sources",reports:"Reports",settings:"Settings"};
const paths = {
dashboard:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
reviews:'<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/><path d="M8 9h8M8 13h5"/>',
analytics:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
insights:'<path d="M12 3a7 7 0 0 0-4 12.74V19h8v-3.26A7 7 0 0 0 12 3zM9 22h6M9 11h6M12 8v6"/>',
sources:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 4 16 4 16 0V5M4 11v6c0 4 16 4 16 0v-6"/>',
reports:'<path d="M14 2H4v20h16V8zM14 2v6h6M8 12h8M8 16h8"/>',
settings:'<circle cx="12" cy="12" r="3"/><path d="m9 3-1 3-3 1-2 4 2 3v4l4 3 3-1 3 1 4-3v-4l2-3-2-4-3-1-1-3z"/>',
refresh:'<path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-2l2 3M4 16l2 3a7 7 0 0 0 12-2"/>',
close:'<path d="m6 6 12 12M6 18 18 6"/>',menu:'<path d="M3 6h18M3 12h18M3 18h18"/>',
arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',chevron:'<path d="m9 5 7 7-7 7"/>',
};
function icon(name){return '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+(paths[name]||paths.reviews)+'</svg>'}
function platform(source){
 const assets={Google:"googlemaps",Instagram:"instagram",Facebook:"facebook","2GIS":"2gis",Yandex:"yandexmaps"};
 if(assets[source])return '<img class="platform '+assets[source]+'" src="/static/icons/'+assets[source]+'.svg" alt="'+esc(names[source]||source)+'">';
 return '<svg class="platform" role="img" aria-label="CSV Import" viewBox="0 0 24 24"><path d="M14 2H4v20h16V8zM14 2v6h6M7 13h10M7 17h10M11 10v10" fill="none" stroke="#667085" stroke-width="1.6"/></svg>';
}
const fmt = v => v && !isNaN(new Date(v)) ? new Date(v).toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"}) : "Date unavailable";
const sentiment = r => r.analysis_status==="done" && colors[r.sentiment] ? r.sentiment : "pending";
const urgent = r => sentiment(r)!=="pending" && (r.severity==="critical" || r.risk_score>=85);
const attention = r => sentiment(r)!=="pending" && (r.sentiment==="negative" || ["high","critical"].includes(r.severity) || r.risk_score>=85);
const badge = r => '<span class="badge '+sentiment(r)+'">'+({positive:"Positive",neutral:"Neutral",negative:"Negative",pending:"Not analyzed"}[sentiment(r)])+'</span>';
function safeURL(v){try{const u=new URL(v);return ["https:","http:"].includes(u.protocol)?u.href:null}catch{return null}}
function empty(title,sub="Try another period or import feedback from Sources."){return '<div class="empty"><strong>'+esc(title)+'</strong><p>'+esc(sub)+'</p></div>'}
function head(title,sub){return '<div class="page-head"><p class="eyebrow">GRATA INTERNATIONAL · KAZAKHSTAN</p><h1>'+title+'</h1><p>'+sub+'</p></div>'}
function card(title,body,sub=""){return '<section class="card"><h2>'+title+'</h2>'+(sub?'<p class="muted">'+sub+'</p>':"")+body+'</section>'}
function rows(items){return items.length?items.map(r=>'<button class="review-row" data-review="'+esc(r.id)+'">'+platform(r.source)+'<span class="review-copy"><span class="author">'+esc(r.author||"Anonymous")+' <span class="date">'+esc(fmt(r.published_at))+'</span></span><span class="preview">'+esc(r.review_text)+'</span></span>'+badge(r)+icon("chevron")+'</button>').join(""):empty("No reviews found");}
function bars(items,color="#0D123F"){
 const max=Math.max(1,...items.map(x=>x.reviews??x.count));
 return items.length?items.map(x=>'<div class="bar"><div><span>'+esc(x.issue||names[x.name]||x.name||x.source)+'</span><b>'+(x.reviews??x.count)+'</b></div><div class="track"><span style="width:'+((x.reviews??x.count)/max*100)+'%;background:'+color+'"></span></div></div>').join(""):empty("No matching feedback","There is not enough data for this chart.");
}
function summary(){
 const d=state.data, m=d.metrics, top=d.issues[0];
 if(!m.analyzed)return "No analyzed reviews are available for this period.";
 if(top)return top.reviews+" negative review"+(top.reviews===1?"":"s")+" mention "+top.issue.toLowerCase()+". This is the most frequent concern in the selected period.";
 return "No negative feedback was detected among "+m.analyzed+" analyzed reviews in this period.";
}
function dashboard(){
 const d=state.data,m=d.metrics,total=m.analyzed;
 const metric=(label,value,note,hero=false)=>'<article class="metric '+(hero?"hero":"")+'"><span>'+label+'</span><strong>'+value+'</strong><small>'+note+'</small></article>';
 const scoreNote=m.health===null?"Awaiting analysis":m.health>=80?"Strong overall feedback":m.health>=60?"Mixed feedback":"Review client concerns";
 const delta=m.health_delta===null?"Comparison unavailable":(m.health_delta>0?"+":"")+m.health_delta+" pts · last 30 vs previous 30 days";
 const pos=total?d.sentiments.positive/total*100:0,neu=total?d.sentiments.neutral/total*100:0;
 const donut='<div class="sentiment"><div class="donut" style="background:conic-gradient(#20A464 0 '+pos+'%,#D99A22 '+pos+'% '+(pos+neu)+'%,#D64545 '+(pos+neu)+'% 100%)"><div><strong>'+total+'</strong><span>analyzed</span></div></div><div class="legend">'+Object.entries(d.sentiments).map(([k,v])=>'<div><i style="background:'+colors[k]+'"></i><span>'+k[0].toUpperCase()+k.slice(1)+'</span><b>'+v+' <small>'+ (total?Math.round(v/total*100):0)+'%</small></b></div>').join("")+'</div></div>';
 return head("Reputation overview","Understand client feedback. Focus on what matters.")+
 '<div class="metrics">'+metric('Reputation Score <span title="100 − 45 × negative share − 25 × critical share − 30 × average risk / 100. Based on analyzed reviews only." tabindex="0" class="info">ⓘ</span>',m.health===null?"—":m.health+'<em> / 100</em>',scoreNote,true)+metric("Total Reviews",m.total,m.analyzed+" analyzed")+metric("Needs Attention",m.attention,m.critical+" critical · includes negative feedback")+metric("Active Sources",m.active_sources,"Sources with feedback this period")+'</div><p class="comparison">'+esc(delta)+'</p>'+
 '<div class="grid two">'+card("Sentiment overview",total?donut:empty("Analysis is pending"),"Based on successfully analyzed reviews")+card("Top client concerns",bars(d.issues.slice(0,5),"#D64545"),"Negative reviews by topic")+'</div>'+
 '<section class="insight"><div>'+icon("insights")+'</div><div><p class="eyebrow">EXECUTIVE INSIGHT</p><h2>'+esc(summary())+'</h2><p>Calculated from saved review classifications; not a new AI audit.</p></div><button data-go="insights">View analysis '+icon("arrow")+'</button></section>'+
 '<div class="grid two">'+card("Source overview",bars(d.sources.filter(s=>s.count)), "Reviews in the selected period")+card("Recent reviews",rows(d.items.slice(0,4))+'<button class="text-button" data-go="reviews">View all reviews '+icon("arrow")+'</button>')+'</div>';
}
function filtered(){
 return state.data.items.filter(r=>(!state.source||r.source===state.source)&&(!state.sentiment||(state.sentiment==="attention"?attention(r):sentiment(r)===state.sentiment))&&[r.author,r.review_text].some(v=>String(v||"").toLowerCase().includes(state.query.toLowerCase())));
}
function reviews(){
 const list=filtered().sort((a,b)=>Number(urgent(b))-Number(urgent(a))||((Date.parse(b.published_at)||0)-(Date.parse(a.published_at)||0)));
 const pages=Math.max(1,Math.ceil(list.length/10));state.page=Math.min(state.page,pages);
 return head("All reviews","Read original feedback and open a review for its analysis.")+
 '<div class="filters"><label>Search reviews<input id="search" placeholder="Author or review text" value="'+esc(state.query)+'"></label><label>Source<select id="source-filter"><option value="">All sources</option>'+state.data.sources.map(s=>'<option '+(s.name===state.source?"selected":"")+' value="'+esc(s.name)+'">'+esc(names[s.name]||s.name)+'</option>').join("")+'</select></label><label>Sentiment<select id="sentiment-filter">'+Object.entries({"":"All sentiments",positive:"Positive",neutral:"Neutral",negative:"Negative",pending:"Not analyzed",attention:"Needs attention"}).map(([v,t])=>'<option '+(v===state.sentiment?"selected":"")+' value="'+v+'">'+t+'</option>').join("")+'</select></label></div><section class="card list-card"><div class="list-caption">'+list.length+' reviews · critical issues first</div>'+rows(list.slice((state.page-1)*10,state.page*10))+'<div class="pagination"><span>Page '+state.page+' of '+pages+'</span><div><button data-page="-1" '+(state.page===1?"disabled":"")+'>Previous</button><button data-page="1" '+(state.page>=pages?"disabled":"")+'>Next</button></div></div></section>';
}
function detail(id){
 const r=state.data.items.find(x=>String(x.id)===id);if(!r)return;
 const s=sentiment(r), topic=topics[r.category]||"Other feedback";
 const stored=String(r.summary||"");
 const english=stored && !/[^\u0000-\u024f\s\p{P}]/u.test(stored);
 const text=s==="pending"?"Analysis is not available yet.":english?stored.split(/\s+/).slice(0,8).join(" "):(s==="positive"?"Positive feedback recorded.":s==="negative"?"Negative feedback about "+topic.toLowerCase()+".":"No clear positive or negative signal.");
 const action=s==="pending"?"Analyze this review":urgent(r)?"Escalate for management review":attention(r)?"Review internally and consider a response":s==="positive"?"No action needed":"Monitor";
 const url=safeURL(r.source_url);
 $("#detail").innerHTML='<button id="close-detail" class="icon-button close-detail" aria-label="Close review details">'+icon("close")+'</button><div class="detail-author">'+platform(r.source)+'<div><h2 id="detail-title">'+esc(r.author||"Anonymous")+'</h2><p>'+esc(names[r.source]||r.source)+' · '+fmt(r.published_at)+'</p></div></div>'+badge(r)+'<blockquote>'+esc(r.review_text)+'</blockquote><div class="detail-section"><h3>AI Summary</h3><p>'+esc(text)+'</p></div><div class="detail-section"><h3>Main Topic</h3><p>'+esc(s==="pending"?"Awaiting analysis":topic)+'</p></div><div class="detail-section"><h3>Recommended Action</h3><p>'+esc(action)+'</p></div>'+(!english&&s!=="pending"?'<p class="muted">English overview based on saved classification. Original analysis remains unchanged.</p>':"")+'<dl><dt>Source</dt><dd>'+esc(names[r.source]||r.source)+'</dd><dt>Date</dt><dd>'+fmt(r.published_at)+'</dd></dl>'+(url?'<a class="source-link" href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Open source reference '+icon("arrow")+'</a>':'<p class="muted">Original URL unavailable</p>')+'<div class="business-status '+(attention(r)?"negative":s)+'"><strong>'+(s==="pending"?"Awaiting analysis":urgent(r)?"Urgent":attention(r)?"Needs attention":s==="positive"?"Positive feedback":"Worth monitoring")+'</strong><p>'+esc(action)+'.</p></div>';
 $("#detail").showModal();$("#close-detail").onclick=()=>$("#detail").close();
}
function volumeChart(){return bars((state.data.volume||[]).map(x=>({issue:x.month,reviews:x.reviews})));}
function timeline(){
 const entries=state.data.trend; if(!entries.length)return empty("No dated analysis available");
 const bins={};entries.forEach(r=>{const month=r.date.slice(0,7);bins[month]??={positive:0,neutral:0,negative:0};bins[month][r.sentiment]+=r.reviews;});
 const rows=Object.entries(bins).sort();const max=Math.max(...rows.map(([,x])=>Object.values(x).reduce((a,b)=>a+b,0)));
 return '<div class="chart-legend">'+Object.keys(colors).map(s=>'<span><i style="background:'+colors[s]+'"></i>'+s+'</span>').join("")+'</div><div class="timeline">'+rows.map(([date,x])=>'<div class="time-row"><span>'+date+'</span><div class="stack">'+Object.entries(x).map(([s,v])=>'<span title="'+date+' · '+s+': '+v+'" style="width:'+v/max*100+'%;background:'+colors[s]+'"></span>').join("")+'</div><b>'+Object.values(x).reduce((a,b)=>a+b,0)+'</b></div>').join("")+'</div><p class="muted">Monthly review counts · only dated, analyzed feedback.</p>';
}
function analytics(){
 return head("Analytics","See where feedback comes from and which themes stand out.")+'<div class="grid two">'+card("Sentiment over time",timeline())+card("Feedback by source",bars(state.data.sources.filter(s=>s.count)))+card("Top complaint topics",bars(state.data.issues,"#D64545"))+card("Positive themes",bars(state.data.positive_themes,"#20A464"))+card("Review volume",volumeChart(),"Monthly count of all dated reviews, including pending analysis")+'</div>';
}
function insights(){
 const items=state.data.items, pending=items.filter(r=>["pending","failed"].includes(r.analysis_status)).length;
 const critical=items.filter(urgent), needs=items.filter(r=>attention(r)&&!urgent(r)), positive=items.filter(r=>sentiment(r)==="positive"&&!attention(r));
 const mainIssue=state.data.issues[0], strength=state.data.positive_themes[0];
 const negativeSource=[...state.data.platforms].sort((a,b)=>(b.negative_pct||0)-(a.negative_pct||0))[0];
 const positiveSource=[...positive.reduce((counts,row)=>counts.set(row.source,(counts.get(row.source)||0)+1),new Map())].sort((a,b)=>b[1]-a[1])[0];
 const assessment=critical.length
   ? critical.length+' critical review'+(critical.length===1?' requires':'s require')+' leadership review. '+summary()
   : needs.length
     ? needs.length+' review'+(needs.length===1?' needs':'s need')+' attention. '+summary()
     : 'No urgent client concerns were detected in this period. '+(positive.length?positive.length+' positive reviews are supporting the brand.':'');
 const good=positive.length
   ? positive.length+' positive review'+(positive.length===1?' was':'s were')+' recorded.'+(strength?' The most common positive theme is '+strength.issue.toLowerCase()+' ('+strength.reviews+').':'')+(positiveSource?' Most positive feedback came from '+positiveSource[0]+'.':'')
   : 'No positive feedback has been classified in this period.';
 const bad=(critical.length+needs.length)
   ? (critical.length+needs.length)+' review'+(critical.length+needs.length===1?' needs':'s need')+' attention.'+(mainIssue?' The main issue is '+mainIssue.issue.toLowerCase()+' ('+mainIssue.reviews+' negative reviews).':'')+(negativeSource?' The highest negative share is on '+negativeSource.source+' ('+Math.round(negativeSource.negative_pct||0)+'%).':'')
   : 'No negative or high-priority feedback was detected in this period.';
 const focus=(critical.length+needs.length)
   ? 'Management focus: review '+(mainIssue?mainIssue.issue.toLowerCase():'the flagged feedback')+', establish ownership, and decide whether each client requires a response.'
   : 'Management focus: maintain the service strengths clients mention and continue monitoring new feedback.';
 const group=(title,subset,action)=>card(title,'<p>'+subset.length+' related reviews · '+esc([...new Set(subset.map(r=>r.source))].join(", "))+'</p><p class="action">'+action+'</p>'+rows(subset.slice(0,3)));
 const groups=[
   critical.length?group("Critical issues",critical,"Escalate for leadership review."):"",
   needs.length?group("Needs attention",needs,"Review internally and consider a response."):"",
   positive.length?group("Positive highlights",positive,"Maintain the strengths clients value."):"",
   card("What to watch",'<p>'+esc(mainIssue?mainIssue.reviews+' negative reviews mention '+mainIssue.issue.toLowerCase()+'.':"No negative feedback was detected in this period.")+'</p><p>Compare periods in Analytics before concluding a trend is increasing.</p><button data-go="analytics">View analytics</button>')
 ].join("");
 return head("AI Insights","Clear management signals from saved review analysis.")+'<section class="executive-insight"><p class="eyebrow">MANAGEMENT INSIGHT</p><h2>'+esc(assessment)+'</h2><p>Generated from stored AI classifications and original reviews. It does not re-run AI.</p></section><section class="insight-summary"><article><span class="insight-label good">WHAT IS GOING WELL</span><p>'+esc(good)+'</p></article><article><span class="insight-label bad">WHAT NEEDS ATTENTION</span><p>'+esc(bad)+'</p></article><article><span class="insight-label focus">MANAGEMENT FOCUS</span><p>'+esc(focus)+'</p></article></section><section class="analysis-coverage"><strong>'+state.data.metrics.analyzed+' of '+state.data.metrics.total+' reviews analyzed</strong><span>'+ (pending ? pending+' review'+(pending===1?'':'s')+' waiting for AI analysis.' : 'Everything in this period has already been analyzed.') +'</span></section><button class="primary" id="analyze" '+(!pending?'disabled':'')+'>Analyze '+(pending?'pending reviews':'up to date')+'</button><p class="muted">Processes up to 50 pending or failed reviews. Completed analysis is never repeated.</p><div class="grid two">'+groups+'</div>';
}
function sources(){
 return head("Sources","Your feedback channels. Import authorized exports; no automatic platform connection is implied.")+'<div class="grid three">'+state.data.sources.map(s=>card(platform(s.name)+' '+esc(names[s.name]||s.name),'<span class="badge pending">Manual Import</span><p><strong class="large">'+s.count+'</strong> reviews this period</p><p class="muted">'+s.total+' all time · Last stored: '+fmt(s.latest)+'</p><button data-source="'+esc(s.name)+'">View reviews</button>')).join("")+'</div>'+card("Import feedback",'<p>Import only feedback you are authorized to use. Confirm it belongs to GRATA, not a post caption. Existing reviews are kept unchanged.</p><form id="import-form"><label>CSV file (UTF-8, up to 1,000 rows / 2 MB)<input id="csv-file" type="file" accept=".csv,text/csv" required></label><details><summary>CSV format</summary><p>Required: source, review_text. Optional: author, published_at (ISO date), rating (0–5; 0 means unavailable), external_id, source_url. Missing dates remain unknown.</p><button type="button" id="template">Download column template</button></details><label class="check"><input type="checkbox" id="after-analysis" '+(state.data.config.ai?"checked":"disabled")+'> Analyze pending reviews after import (up to 50)</label><button class="primary" type="submit">Import reviews</button></form><p id="import-result" role="status"></p><p class="muted">Refresh reloads saved database records. Scheduled collection and official platform authorization are not configured.</p>');
}
const reportTypes=["Executive Reputation Summary","Review Trends Report","Source Performance Report","Issue Summary","Monthly Reputation Report"];
function reportBody(){
 const d=state.data;
 if(state.report==="Review Trends Report"||state.report==="Monthly Reputation Report")return timeline();
 if(state.report==="Source Performance Report")return bars(d.sources.filter(s=>s.count));
 if(state.report==="Issue Summary")return bars(d.issues,"#D64545");
 return '<p>'+esc(summary())+'</p><p>'+d.metrics.total+' reviews · '+d.metrics.attention+' need attention · '+d.metrics.critical+' critical.</p><p>Reputation Score: '+(d.metrics.health??"Unavailable")+'</p>';
}
function reports(){return head("Reports","Share an evidence-based snapshot with management.")+'<label>Report type<select id="report-type">'+reportTypes.map(t=>'<option '+(t===state.report?"selected":"")+'>'+t+'</option>').join("")+'</select></label><article class="card report"><p class="eyebrow">GRATA INTERNATIONAL · '+esc($("#period").selectedOptions[0].textContent)+'</p><h2>'+esc(state.report)+'</h2><p>Generated '+fmt(new Date())+'</p>'+reportBody()+'<p class="muted">Based on the selected period. AI classifications may require human review. Missing dates are excluded from dated charts.</p></article><div class="report-actions"><button id="print">Print / Save as PDF</button><button id="export">Export period reviews (CSV)</button></div><p class="muted">PDF uses your browser’s print dialog. Reports are generated on demand, not stored.</p>'}
function settings(){return head("Settings","Organization preferences and honest connection status.")+'<div class="grid two">'+card("General","<p>GRATA International · Kazakhstan</p><p>Interface: English · Original feedback is preserved.</p>")+card("Users & roles","<p>User accounts are not configured.</p><p>Keep this internal app behind your organization’s authenticated gateway before public deployment.</p>")+card("Notifications","<p>Automatic alerts are not enabled. Refresh to check stored reviews.</p>")+card("Sources",'<p>Database: '+((state.data?.config||state.config)?.supabase?"Credentials configured":"Needs setup")+'</p><p>Platform connections: manual import only.</p><button data-go="sources">Manage sources</button>')+card("AI rules",'<p>'+((state.data?.config||state.config)?.ai?"AI credentials configured; availability checked on analysis.":"AI provider needs setup on the server.")+'</p><p>Gemini first, then Groq. Clear social reactions use a local rule. Only pending or failed reviews are processed.</p>')+card("Appearance","<p>GRATA navy, restrained gold, and semantic sentiment colors.</p><p>TT Norms Pro · Responsive desktop and mobile layout.</p>")+'</div>'}
function render(){
 if(!state.data && state.view!=="settings"){$("#page").innerHTML=head(nav[state.view],"Connect your database to see real feedback.")+empty("Reviews unavailable","No sample data has been substituted. Open Settings or retry Refresh.");return;}
 $("#page").innerHTML=({dashboard,reviews,analytics,insights,sources,reports,settings}[state.view])();
}
function go(view){
 if($("#detail").open)$("#detail").close();
 state.view=nav[view]?view:"dashboard";location.hash=state.view;
 document.querySelectorAll("[data-view]").forEach(b=>{b.classList.toggle("active",b.dataset.view===state.view);b.setAttribute("aria-current",b.dataset.view===state.view?"page":"false");});
 $("#sidebar").classList.remove("open");$("#scrim").hidden=true;$("#menu").setAttribute("aria-expanded","false");
 render();window.scrollTo(0,0);
}
let toastTimer;
function toast(message){clearTimeout(toastTimer);$("#toast").textContent=message;$("#toast").hidden=false;toastTimer=setTimeout(()=>$("#toast").hidden=true,6000)}
async function api(url,options={}){
 const r=await fetch(url,options),body=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(typeof body.detail==="string"?body.detail:"The request could not be completed. Check your input and try again.");
 return body;
}
function query(){
 const p=new URLSearchParams(),value=$("#period").value;
 if(value==="custom"){if(!$("#start").value||!$("#end").value||$("#start").value>$("#end").value)throw new Error("Choose a valid start and end date.");p.set("start",$("#start").value);p.set("end",$("#end").value);}
 else if(value)p.set("days",value);
 return p.toString();
}
async function load(){
 if(state.busy)return false;let q;try{q=query()}catch(e){toast(e.message);return false}
 state.busy=true;$("#refresh").disabled=true;$("#period").disabled=true;$("#apply-dates").disabled=true;if($("#detail").open)$("#detail").close();$("#error").hidden=true;$("#data-status summary").textContent="Checking data";
 $("#page").innerHTML='<div class="skeleton" aria-label="Loading reviews" role="status"><div></div><div></div><div></div></div>';
 try{
 const d=await api("/api/dashboard?"+q);state.data=d;state.config=d.config;state.page=1;
 $("#data-status summary").textContent="Database updated";
 $("#status-content").textContent="Supabase connected. Last checked: "+new Date(d.meta.checked_at).toLocaleTimeString("en-GB")+". Platform collection: manual import. Latest dated review: "+fmt(d.meta.latest)+".";
 $("#date-note").textContent=[d.meta.unknown_dates?d.meta.unknown_dates+" reviews have no date. Select All time to include them.":"",d.meta.excluded_unverified?d.meta.excluded_unverified+" unverified 2GIS records are excluded; originals remain in the database.":""].filter(Boolean).join(" ");
 render();return true;
 }catch(e){state.data=null;state.config=await api("/api/config").catch(()=>null);$("#data-status summary").textContent="Data unavailable";$("#status-content").textContent="Database could not be reached. No example data is shown.";$("#error").textContent=e.message;$("#error").hidden=false;render();return false}
 finally{state.busy=false;$("#refresh").disabled=false;$("#period").disabled=false;$("#apply-dates").disabled=false}
}
function download(name,text){const url=URL.createObjectURL(new Blob(["\ufeff"+text],{type:"text/csv;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function exportCSV(){
 const keys=["source","author","published_at","review_text","sentiment","source_url"];
 const cell=v=>{let s=String(v??"");if(/^[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"'};
 download("grata-reviews.csv",[keys.join(","),...state.data.items.map(r=>keys.map(k=>cell(r[k])).join(","))].join("\r\n"));
}
let writing=false;
async function analyze(){
 if(writing)return;writing=true;const b=$("#analyze");if(b)b.disabled=true;
 try{toast("Analyzing pending feedback. This may take a few minutes.");const r=await api("/api/analyze",{method:"POST"});await load();toast(r.total===0?"No new reviews need AI analysis. Existing analysis was kept unchanged.":r.done+" analyzed; "+r.failed+" could not be analyzed.")}
 catch(e){toast(e.message)}finally{writing=false;if(b)b.disabled=false}
}
document.addEventListener("click",e=>{
 const b=e.target.closest("button");if(!b)return;
 if(b.dataset.view)go(b.dataset.view);
 if(b.dataset.go)go(b.dataset.go);
 if(b.dataset.review)detail(b.dataset.review);
 if(b.dataset.source){state.source=b.dataset.source;state.sentiment="";state.query="";state.page=1;go("reviews")}
 if(b.dataset.page){state.page+=Number(b.dataset.page);render()}
 if(b.id==="print")window.print();
 if(b.id==="export")exportCSV();
 if(b.id==="template")download("review-columns.csv","source,author,review_text,published_at,rating,external_id,source_url\r\n");
 if(b.id==="analyze")analyze();
});
document.addEventListener("input",e=>{if(e.target.id==="search"){const pos=e.target.selectionStart;state.query=e.target.value;state.page=1;render();$("#search").focus();$("#search").setSelectionRange(pos,pos)}});
document.addEventListener("change",e=>{
 if(e.target.id==="source-filter"){state.source=e.target.value;state.page=1;render()}
 if(e.target.id==="sentiment-filter"){state.sentiment=e.target.value;state.page=1;render()}
 if(e.target.id==="report-type"){state.report=e.target.value;render()}
});
document.addEventListener("submit",async e=>{
 if(e.target.id!=="import-form")return;e.preventDefault();if(writing)return;
 const file=$("#csv-file").files[0];if(!file)return;if(file.size>2_000_000){toast("Choose a file smaller than 2 MB.");return}
 writing=true;const button=e.target.querySelector('[type="submit"]');button.disabled=true;const runAI=$("#after-analysis").checked;
 try{const r=await api("/api/import",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({content:await file.text()})});let msg=r.saved+" new reviews imported; "+r.duplicates+" duplicates skipped.";
 if(runAI&&r.saved){toast(msg+" Analyzing pending reviews…");try{const a=await api("/api/analyze",{method:"POST"});msg+=" "+a.done+" analyzed; "+a.failed+" failed."}catch{msg+=" Reviews saved. Analysis unavailable; retry from AI Insights."}}
 await load();toast(msg);if($("#import-result"))$("#import-result").textContent=msg;
 }catch(e){toast(e.message)}finally{writing=false;button.disabled=false}
});
$("#nav").innerHTML=Object.entries(nav).map(([k,v])=>'<button data-view="'+k+'">'+icon(k)+'<span>'+v+'</span></button>').join("");
$("#refresh").innerHTML=icon("refresh");$("#menu").innerHTML=icon("menu");
$("#refresh").onclick=async()=>{if(await load())toast("Database updated. Platform collection is manual.")};
$("#period").onchange=()=>{$("#custom-dates").hidden=$("#period").value!=="custom";if($("#period").value!=="custom")load()};
$("#apply-dates").onclick=()=>load();$("#profile").onclick=()=>go("settings");
$("#menu").onclick=()=>{$("#sidebar").classList.toggle("open");const open=$("#sidebar").classList.contains("open");$("#scrim").hidden=!open;$("#menu").setAttribute("aria-expanded",String(open))};
$("#scrim").onclick=()=>{$("#sidebar").classList.remove("open");$("#scrim").hidden=true;$("#menu").setAttribute("aria-expanded","false")};
document.addEventListener("keydown",e=>{if(e.key==="Escape")$("#scrim").click()});
window.addEventListener("hashchange",()=>{if(location.hash.slice(1)!==state.view)go(location.hash.slice(1))});
go(location.hash.slice(1));load();
