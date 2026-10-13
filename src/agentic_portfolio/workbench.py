"""Offline, read-only operational workbench generated from actual run evidence.

No synthetic agent states: every displayed node comes from the supplied JSON.
The output is a standalone HTML artifact with no CDN or network dependency.
"""
import argparse
import html
import json
from pathlib import Path
from .causal_graph import normalize, native_graph
from .event_journal import EventJournal

PAGE='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Execution Control | Agentic Systems</title>
<style>
:root{font:14px/1.45 Inter,Segoe UI,system-ui,sans-serif;color:#dce5f4;background:#0a101b}
*{box-sizing:border-box}body{margin:0}button,input,select{font:inherit}
button{cursor:pointer}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #8db9ff;outline-offset:2px}
.shell{min-height:100vh;display:grid;grid-template-rows:auto auto 1fr}
.topbar{padding:16px 24px;border-bottom:1px solid #2c3850;display:flex;align-items:center;justify-content:space-between;gap:16px;background:#101827}
.eyebrow{font-size:11px;letter-spacing:.11em;color:#84a3cd;text-transform:uppercase}
h1{font-size:20px;letter-spacing:-.03em;margin:2px 0 0}h2{font-size:14px;margin:0}
.state{border:1px solid #3d586f;border-radius:8px;padding:8px 13px;font-weight:650}
.state.pass{border-color:#26765c;color:#66dfb3}.state.failed{border-color:#963e55;color:#ffa2b1}
.summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:18px 24px;background:#0b1220}
.metric{background:#151f30;border:1px solid #293b54;border-radius:10px;padding:14px 16px;min-width:0}
.metric label{display:block;font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:#92a9c6;margin-bottom:7px}
.metric strong{font-size:15px;overflow-wrap:anywhere}
.main{padding:0 24px 24px;display:grid;grid-template-columns:minmax(0,1.7fr) minmax(340px,1fr);gap:14px;min-height:0}
.panel{background:#121b2a;border:1px solid #2a3950;border-radius:10px;overflow:hidden;min-width:0}
.panelhead{padding:17px 18px;border-bottom:1px solid #2a3950;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.muted{color:#94a6be;font-size:12px}.lanes{padding:18px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.lane{background:#0e1725;border:1px solid #2d405a;border-radius:9px;padding:14px;min-width:0}
.lane{cursor:pointer;text-align:left;color:inherit}.lane:hover,.lane:focus-visible{border-color:#6e9bd0;background:#192a40}.lane.active{border-color:#78b6ff;box-shadow:inset 0 0 0 1px #78b6ff}.lane h3{font-size:12px;color:#9bbbe6;margin:0 0 10px;text-transform:uppercase;letter-spacing:.08em}
.lane .value{font-size:15px;font-weight:650;overflow-wrap:anywhere}.lane small{display:block;color:#91a3be;margin-top:8px}
.arrow{display:none}.tools{display:flex;gap:9px;align-items:center;flex-wrap:wrap;padding:12px 18px;border-top:1px solid #26364b}
input,select{background:#0c1522;border:1px solid #3a4b65;color:#e5ecf8;padding:9px 10px;border-radius:7px}
input{min-width:180px;flex:1}
.eventwrap{max-height:540px;overflow:auto}
table{border-collapse:collapse;width:100%;table-layout:fixed}th{text-align:left;color:#9aacc4;background:#172438;position:sticky;top:0;font-size:11px;letter-spacing:.05em;padding:11px 12px}
td{border-top:1px solid #223148;padding:11px 12px;font-size:12px;vertical-align:top;overflow-wrap:anywhere}
th:nth-child(1){width:54px}th:nth-child(2){width:88px}th:nth-child(3){width:30%}th:nth-child(4){width:24%}
tr.event{cursor:pointer}tr.event:hover{background:#1b2c42}tr.event.selected{background:#1e3c58}
.tag{font-size:10px;color:#b9d5fc;text-transform:uppercase}.time{font-variant-numeric:tabular-nums;color:#a8bad1}
.details{padding:20px}.details dl{margin:14px 0;display:grid;grid-template-columns:110px 1fr;gap:9px;font-size:12px}
dt{color:#95a9c4}dd{margin:0;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;background:#09111e;border:1px solid #2a3b54;padding:15px;border-radius:8px;font-size:12px;color:#c1d5f0}
.btn{background:#223b5b;border:1px solid #395d88;color:#e2efff;border-radius:7px;padding:7px 12px}
.stageflow{padding:12px 18px 18px;display:flex;flex-wrap:wrap;align-items:stretch;gap:8px;border-bottom:1px solid #26364b}
.stagebutton{border:1px solid #355070;background:#14273c;color:#dbeafa;padding:10px 13px;min-width:160px;max-width:260px;text-align:left;border-radius:8px}
.stagebutton:hover,.stagebutton.selected{border-color:#85b8fc;background:#233b58}
.stagebutton strong{display:block;font-size:12px;overflow-wrap:anywhere}
.stagebutton small{color:#98b3d2;display:block;margin-top:5px}
.flowconnector{align-self:center;color:#8caccb}
.detail-summary{margin:14px 0;padding:12px;border:1px solid #304765;border-radius:8px;background:#101e30}
.detail-summary div{font-size:12px;margin-bottom:6px;overflow-wrap:anywhere}
.raw-toggle{margin:10px 0}
.foot{padding:12px 24px;color:#859ab7;font-size:11px}
@media(max-width:1100px){.main{grid-template-columns:1fr}.details{min-height:200px}}
@media(max-width:640px){.summary{grid-template-columns:repeat(2,minmax(0,1fr));padding:12px}.main{padding:0 12px 12px}.lanes{grid-template-columns:1fr}.topbar{padding:14px}}
</style></head><body><div class="shell">
<header class="topbar"><div><div class="eyebrow">Recorded execution · read-only evidence</div><h1>Agent Execution Workbench</h1></div><div class="state" id="state"></div></header>
<section class="summary" id="summary"></section>
<main class="main">
<section class="panel"><div class="panelhead"><div><h2>Execution overview</h2><div class="muted">Agent stages and journal-backed tool activity</div></div><span class="muted" id="count"></span></div>
<div class="lanes" id="lanes"></div><div class="stageflow" id="stageflow" aria-label="Recorded stage flow"></div>
<div class="tools"><input aria-label="Search recorded events" id="search" placeholder="Search event name, ID or payload"><select aria-label="Filter activity" id="filter"><option value="all">All activity</option><option value="engineering">Engineering</option><option value="catalog">Catalog</option><option value="system">Orchestration</option></select><button class="btn" id="clear">Clear</button></div>
<div class="eventwrap"><table><thead><tr><th>#</th><th>Lane</th><th>Observed event</th><th>Parent event</th><th>Time</th></tr></thead><tbody id="events"></tbody></table></div>
</section>
<section class="panel"><div class="panelhead"><div><h2>Evidence inspector</h2><div class="muted">Select an actual journal event</div></div><button class="btn" id="copy">Copy JSON</button></div>
<div class="details"><h2 id="detail-title">Run overview</h2><div class="detail-summary" id="detail-summary"></div><dl id="metadata"></dl><button class="btn raw-toggle" id="raw-toggle" aria-expanded="false">Show raw evidence JSON</button><pre id="details" tabindex="0" hidden></pre></div></section>
</main><footer class="foot">Read-only snapshot generated from the local run report and verified append-only journal. Event ordering and recorded parent IDs are evidence; no synthetic agent actions or external service state are implied.</footer>
</div><script type="application/json" id="run-evidence">__EVIDENCE__</script>
<script>
"use strict";
const data=JSON.parse(document.getElementById("run-evidence").textContent);
const nodes=data.execution_graph?.nodes||[];
const status=String(data.state||"UNKNOWN");
const stateEl=document.getElementById("state");stateEl.textContent=status;stateEl.classList.add(status==="PASS"?"pass":status==="FAILED"?"failed":"");
const summary=[["Run ID",data.run_id||"UNAVAILABLE"],["Execution",status],["Engineering",data.engineering?.status||"UNOBSERVED"],["Catalog",data.catalog?.status||(data.catalog?.verified?"VERIFIED":"UNOBSERVED")]];
for(const [name,value] of summary){const el=document.createElement("div");el.className="metric";const label=document.createElement("label");label.textContent=name;const strong=document.createElement("strong");strong.textContent=value;el.append(label,strong);document.getElementById("summary").append(el)}
const stages=data.stages||[];
const byId=new Map(nodes.map(n=>[n.id,n]));
function ancestorStage(n){let current=n,seen=new Set();while(current&&!seen.has(current.id)){seen.add(current.id);if(current.kind==="stage_started")return current;current=byId.get(current.parent_id)}return null}
function lane(n){const stage=ancestorStage(n);const name=String(stage?.observation?.name||n?.observation?.name||"").toLowerCase();if(name.includes("engineering"))return "engineering";if(name.includes("catalog"))return "catalog";return "system"}
const lanes=[["Engineering",data.engineering?.status||"UNOBSERVED","engineering"],["Catalog",data.catalog?.status||(data.catalog?.verified?"VERIFIED":"UNOBSERVED"),"catalog"],["Orchestration",status,"system"]];
let laneFilter="all",stageFilter=null,activeId=null,shown=data;
const stageNodes=nodes.filter(n=>n.kind==="stage_started");
const stageFlow=document.getElementById("stageflow");
const laneRoot=document.getElementById("lanes");
for(const [name,value,key] of lanes){const el=document.createElement("button");el.type="button";el.className="lane";el.dataset.lane=key;const title=document.createElement("h3");title.textContent=name;const body=document.createElement("div");body.className="value";body.textContent=value;const sub=document.createElement("small");sub.textContent=nodes.filter(n=>lane(n)===key).length+" journal event(s)";el.append(title,body,sub);el.addEventListener("click",()=>{laneFilter=laneFilter===key?"all":key;stageFilter=null;document.getElementById("filter").value=laneFilter;render();renderStageFlow()});laneRoot.append(el)}
function descendants(stage){return nodes.filter(n=>ancestorStage(n)?.id===stage.id)}
function renderStageFlow(){stageFlow.replaceChildren();if(!stageNodes.length){const x=document.createElement("span");x.className="muted";x.textContent="No journal stage boundaries recorded";stageFlow.append(x);return}stageNodes.forEach((stage,i)=>{const children=descendants(stage);const finished=nodes.find(n=>n.kind==="stage_completed"&&n.observation?.name===stage.observation?.name&&n.sequence>stage.sequence);const failed=nodes.find(n=>n.kind==="stage_failed"&&n.observation?.name===stage.observation?.name&&n.sequence>stage.sequence);const button=document.createElement("button");button.type="button";button.className="stagebutton";if(stageFilter===stage.id)button.classList.add("selected");const head=document.createElement("strong");head.textContent=stage.observation?.name||"Unnamed observed stage";const info=document.createElement("small");info.textContent=children.length+" child event(s) · "+(failed?"FAILED":finished?"COMPLETED":"STARTED");button.append(head,info);button.addEventListener("click",()=>{stageFilter=stageFilter===stage.id?null:stage.id;laneFilter="all";document.getElementById("filter").value="all";inspect(stage);render();renderStageFlow()});stageFlow.append(button);if(i<stageNodes.length-1){const arrow=document.createElement("span");arrow.className="flowconnector";arrow.textContent="→";arrow.title="Journal sequence only; not an inferred dependency";stageFlow.append(arrow)}})}
const inspector=document.getElementById("detail-summary"),raw=document.getElementById("details"),toggle=document.getElementById("raw-toggle");
function inspect(n){activeId=n?.id||null;shown=n||data;document.getElementById("detail-title").textContent=n?.label||"Run overview";const dl=document.getElementById("metadata");dl.replaceChildren();inspector.replaceChildren();const observation=n?.observation||{};const pairs=n?[["Event ID",n.id],["Parent event",n.parent_id||"Root"],["Observed lane",lane(n)],["Sequence",n.sequence],["Event kind",n.kind]]:[["Run ID",data.run_id],["Result",status],["Journal events",nodes.length]];for(const [k,v] of pairs){const dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=k;dd.textContent=String(v??"");dl.append(dt,dd)}const values=n?Object.entries(observation).filter(([k,v])=>v===null||["string","number","boolean"].includes(typeof v)).slice(0,10):[["Engineering",data.engineering?.status||"UNOBSERVED"],["Catalog",data.catalog?.status||(data.catalog?.verified?"VERIFIED":"UNOBSERVED")],["Stages",stages.length]];for(const [key,value] of values){const el=document.createElement("div");el.textContent=key.replaceAll("_"," ")+"  ·  "+String(value);inspector.append(el)}if(!values.length)inspector.textContent="No scalar observation fields recorded; open raw evidence for details.";raw.textContent=JSON.stringify(n?.observation||data,null,2);document.querySelectorAll("tr.event").forEach(tr=>tr.classList.toggle("selected",tr.dataset.id===activeId))}
function render(){const q=document.getElementById("search").value.toLowerCase(),f=document.getElementById("filter").value;const target=document.getElementById("events");target.replaceChildren();let total=0;for(const n of nodes){const l=lane(n);if(f!=="all"&&l!==f)continue;if(stageFilter&&ancestorStage(n)?.id!==stageFilter&&n.id!==stageFilter)continue;if(q&&!JSON.stringify(n).toLowerCase().includes(q))continue;total++;const tr=document.createElement("tr");tr.className="event";tr.dataset.id=n.id;const parent=byId.get(n.parent_id);const fields=[n.sequence,l,n.label,n.parent_id?((parent?.label||"Parent")+" · "+n.parent_id.slice(0,8)):"Root",n.created_ns?new Date(n.created_ns/1e6).toLocaleTimeString():"Recorded"];fields.forEach((v,i)=>{const td=document.createElement("td");td.textContent=String(v);if(i===1)td.className="tag";if(i===4)td.className="time";if(i===3&&parent){td.title="Select recorded causal parent";td.style.cursor="pointer";td.addEventListener("click",e=>{e.stopPropagation();stageFilter=null;document.getElementById("filter").value="all";inspect(parent);render();renderStageFlow();document.querySelector('tr.event.selected')?.scrollIntoView({block:"nearest"})})}tr.append(td)});tr.tabIndex=0;tr.addEventListener("click",()=>inspect(n));tr.addEventListener("keydown",e=>{if(e.key==="Enter")inspect(n)});target.append(tr)}document.getElementById("count").textContent=total+" of "+nodes.length+" recorded events";document.querySelectorAll(".lane").forEach(el=>el.classList.toggle("active",el.dataset.lane===f));if(activeId)document.querySelectorAll("tr.event").forEach(tr=>tr.classList.toggle("selected",tr.dataset.id===activeId))}
toggle.addEventListener("click",()=>{raw.hidden=!raw.hidden;toggle.setAttribute("aria-expanded",String(!raw.hidden));toggle.textContent=raw.hidden?"Show raw evidence JSON":"Hide raw evidence JSON"});
document.getElementById("search").addEventListener("input",render);document.getElementById("filter").addEventListener("change",render);document.getElementById("clear").addEventListener("click",()=>{document.getElementById("search").value="";document.getElementById("filter").value="all";render()});
document.getElementById("copy").addEventListener("click",()=>{const value=JSON.stringify(shown?.observation||shown,null,2);if(navigator.clipboard?.writeText)navigator.clipboard.writeText(value).catch(()=>{});else{const t=document.createElement("textarea");t.value=value;document.body.append(t);t.select();document.execCommand("copy");t.remove()}});
inspect(null);renderStageFlow();render();
</script></body></html>'''

def build(report, output):
    evidence=json.loads(Path(report).read_text(encoding="utf-8"))
    if not isinstance(evidence,dict) or not evidence.get("run_id"):
        raise ValueError("run report lacks run_id")
    journal_path=Path(report).with_suffix(".events.sqlite3")
    if journal_path.is_file():
        journal=EventJournal(journal_path)
        journal.verify()
        evidence["execution_graph"]=native_graph(evidence["run_id"],journal.read(evidence["run_id"]))
    else:
        evidence["execution_graph"]=normalize(evidence)
    # Escape HTML-special characters inside a script raw-text element.
    payload=json.dumps(evidence,ensure_ascii=True).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    destination=Path(output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(PAGE.replace("__EVIDENCE__",payload),encoding="utf-8")
    return destination

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=build(args.report,args.output)
    print(json.dumps({"workbench":str(result),"input":args.report}))

if __name__=="__main__":
    main()
