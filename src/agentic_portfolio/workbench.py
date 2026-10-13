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

PAGE='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Execution | Evidence Workbench</title><style>
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui;background:#090d16;color:#e6eaf2}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 60% -15%,#1b2949 0%,#0a0e17 45%)}
header{padding:22px 32px;border-bottom:1px solid #263045;display:flex;align-items:center;justify-content:space-between}
h1{font-size:19px;margin:0;letter-spacing:-.4px}small,.muted{color:#91a0bb}
.pill{border:1px solid #39445c;border-radius:30px;padding:6px 12px;font-size:12px}
main{padding:24px 32px;max-width:1700px;margin:auto}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:20px}
.metric,.panel{border:1px solid #263249;background:#11192aee;border-radius:12px}
.metric{padding:17px}.metric strong{display:block;font-size:21px;margin-top:9px}.label{font-size:11px;letter-spacing:1px;color:#93a4c0;text-transform:uppercase}
.layout{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(300px,1fr);gap:16px}
.panel{padding:20px;min-width:0}h2{font-size:14px;font-weight:600;margin:0 0 18px}
.canvas{display:grid;grid-template-columns:1fr 45px 1fr 45px 1fr;align-items:center;gap:0}
.node{padding:18px 12px;border:1px solid #35435b;background:#161f31;border-radius:9px;min-height:120px;cursor:pointer;text-align:left;color:inherit;width:100%}
.node:hover,.node:focus{border-color:#7eabff;background:#1e2a43;outline:0}.node strong{display:block;font-size:13px;margin:9px 0}.node span{font-size:12px;color:#96a6c4}
.line{height:2px;background:#426183;position:relative}.line:after{content:"";position:absolute;right:0;top:-4px;border-left:7px solid #638abb;border-top:5px solid transparent;border-bottom:5px solid transparent}
.ok{color:#67dfb0}.blocked{color:#f5c979}.failed{color:#ff899b}
.timeline{margin:0;padding:0;list-style:none}.timeline li{border-left:2px solid #304768;padding:0 0 18px 18px;margin-left:5px;position:relative}.timeline li:before{content:"";position:absolute;width:9px;height:9px;border-radius:50%;background:#5d99ed;left:-5px;top:3px}.timeline button{background:none;border:0;color:#e2e9f7;text-align:left;font:inherit;cursor:pointer;padding:0}
pre{font-size:12px;line-height:1.6;overflow:auto;max-height:560px;white-space:pre-wrap;overflow-wrap:anywhere;color:#c8d7ec}
#details{background:#0b1220;padding:16px;border:1px solid #253552;border-radius:8px;min-height:210px}
footer{padding:22px 32px;font-size:11px;color:#8393ad}
@media(max-width:1050px){.layout{grid-template-columns:1fr}}@media(max-width:650px){.metrics{grid-template-columns:1fr 1fr}.canvas{grid-template-columns:1fr;gap:10px}.line{width:2px;height:20px;justify-self:center}.line:after{top:15px;right:-4px;transform:rotate(90deg)}header,main{padding:16px}}
</style></head><body>
<header><div><div class="label">Evidence-backed orchestration</div><h1>Agent Execution Workbench</h1></div><span class="pill" id="state"></span></header>
<main><section class="metrics" id="metrics"></section><div class="layout">
<section class="panel"><h2>Execution dependency graph</h2><div class="canvas" id="dag"></div><h2 style="margin-top:30px">Observed stages</h2><ol class="timeline" id="timeline"></ol></section>
<section class="panel"><h2>Evidence inspector <small>· select a stage</small></h2><pre id="details" tabindex="0"></pre></section>
</div></main><footer>Source: immutable exported run JSON · Read-only · No inferred, fabricated or simulated events · Not a control plane</footer>
<script type="application/json" id="run-evidence">__EVIDENCE__</script>
<script>
"use strict";
const data=JSON.parse(document.getElementById("run-evidence").textContent);
const status=String(data.state||"UNKNOWN");
document.getElementById("state").textContent=status;
const entries=[["RUN ID",data.run_id||"UNAVAILABLE"],["EXECUTION STATE",status],
["ENGINEERING",data.engineering?.status||"UNOBSERVED"],
["CATALOG",data.catalog?.status||(data.catalog?.verified===true?"VERIFIED":"UNOBSERVED")]];
const metrics=document.getElementById("metrics");
for(const [name,value] of entries){const e=document.createElement("div");e.className="metric";const l=document.createElement("div");l.className="label";l.textContent=name;const v=document.createElement("strong");v.textContent=value;e.append(l,v);metrics.append(e)}
function show(x){document.getElementById("details").textContent=JSON.stringify(x,null,2)}
const engineering=data.engineering||null,catalog=data.catalog||null;
const nodes=(data.execution_graph?.nodes||[]).map(n=>({name:n.label,detail:n.observation,edge:n.edge_type,identity:n.id}));
const dag=document.getElementById("dag");dag.style.display="flex";dag.style.flexDirection="column";dag.style.alignItems="stretch";dag.style.gap="6px";
nodes.forEach((n,i)=>{if(i){const line=document.createElement("div");line.className="line";dag.append(line)}
const b=document.createElement("button");b.className="node";b.style.minHeight="70px";const type=document.createElement("div");type.className="label";type.textContent=n.edge||"RUN ROOT";
const title=document.createElement("strong");title.textContent=n.name;const status=document.createElement("span");status.textContent=n.identity||"NOT OBSERVED";
b.append(type,title,status);b.addEventListener("click",()=>show(n.detail||{status:"NOT_OBSERVED"}));dag.append(b)});
const timeline=document.getElementById("timeline");
const events=(data.stages||[]).map(x=>({name:x.name,stage:x}));for(const x of engineering?.events||[]){events.push({name:"Engineering / "+x.stage,stage:x})}
for(const item of events){const li=document.createElement("li"),b=document.createElement("button");b.textContent=item.name+" · "+(item.stage.elapsed_ms??item.stage.result?.exit_code??"")+" "+(item.stage.elapsed_ms!==undefined?"ms":"");b.addEventListener("click",()=>show(item.stage));li.append(b);timeline.append(li)}
show({run_id:data.run_id,state:data.state,started_at:data.started_at,finished_at:data.finished_at,stages:data.stages});
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
