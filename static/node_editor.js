(function(){
'use strict';
const colors=['#8b5cf6','#0ea5e9','#10b981','#f59e0b','#ec4899','#6366f1','#14b8a6'];
function injectStyle(){
 if(document.getElementById('rp-node-editor-style'))return;
 const st=document.createElement('style');st.id='rp-node-editor-style';st.textContent=
 '.rp-node-dialog{position:fixed!important;inset:0!important;width:100vw!important;max-width:none!important;height:100dvh!important;max-height:none!important;margin:0!important;padding:14px!important;box-sizing:border-box;overflow:hidden!important;border:0!important;border-radius:0!important}'+
 '.rp-node-dialog #rp-dialog-content{height:calc(100% - 58px);min-height:0}.rp-node-editor{display:grid;grid-template-rows:auto 1fr;gap:10px;min-height:0;height:100%}'+
 '.rp-node-toolbar{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.rp-node-toolbar .btn{padding:6px 10px}'+
 '.rp-node-main{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:10px;min-height:0}'+
 '.rp-node-viewport{position:relative;overflow:hidden;border:1px solid var(--border-color);border-radius:10px;background-color:#0c0d12;background-image:radial-gradient(#343746 1px,transparent 1px);background-size:20px 20px;min-height:0}'+
 '.rp-node-world{position:absolute;inset:0;transform-origin:0 0}.rp-node-links{position:absolute;left:0;top:0;width:2400px;height:1600px;overflow:visible;pointer-events:none}'+
 '.rp-node{position:absolute;width:220px;background:#1d202a;border:1px solid #45495a;border-radius:10px;box-shadow:0 8px 22px #0008;color:#e8eaf2;overflow:hidden}'+
 '.rp-node.selected{border-color:#a78bfa;box-shadow:0 0 0 2px #8b5cf655,0 8px 22px #0008}.rp-node-head{padding:8px 10px;background:#292d3a;cursor:grab;font-weight:700;font-size:12px;border-left:5px solid var(--node-color)}'+
 '.rp-node.path-ok{box-shadow:0 0 0 2px #22c55e88,0 8px 22px #0008}.rp-path-result{display:grid;gap:8px}.rp-path-card{padding:9px;border:1px solid #3b4050;border-radius:8px;background:#1d202a}.rp-path-card.ok{border-color:#22c55e}.rp-path-card.bad{border-color:#ef4444}.rp-path-route{font-size:10px;color:#93c5fd;word-break:break-all;margin-top:5px}.rp-path-value{font-size:10px;color:#b8bfce;word-break:break-word}'+
 '.rp-node-id{float:right;color:#9299aa;font-weight:400}.rp-node-body{padding:7px 9px;font-size:11px}.rp-node-port{position:relative;white-space:nowrap;overflow:visible;text-overflow:ellipsis;padding:4px 10px;color:#bac1d0}.rp-input-socket,.rp-output-socket{position:absolute;width:13px;height:13px;border:2px solid #dbeafe;border-radius:50%;background:var(--node-color);cursor:crosshair;z-index:3}.rp-input-socket{left:-8px;top:6px}.rp-output-socket{right:-7px;top:12px}.rp-output-label{position:relative;padding:5px 12px 8px;text-align:right;color:#aab2c3;border-top:1px solid #303442}.rp-node-port.connected .rp-input-socket{box-shadow:0 0 0 3px #60a5fa55}.rp-node-port:hover,.rp-output-label:hover{color:#fff}'+
 '.rp-node-inspector{overflow:auto;border:1px solid var(--border-color);border-radius:10px;background:#15171e;padding:12px}.rp-node-inspector h3{margin:0 0 8px}.rp-node-field{display:block;margin:9px 0;font-size:11px;color:#aeb5c4}.rp-node-field input,.rp-node-field textarea,.rp-node-field select{margin-top:4px;width:100%}.rp-node-field textarea{min-height:74px;resize:vertical}.rp-link-label{color:#93c5fd;font-size:10px}'+
 '.rp-node-status{margin-left:auto;font-size:11px;color:#9ca3af}.rp-node-raw{width:100%;height:100%;resize:none;font:11px monospace;background:#0d0f14;color:#d6dae5;border:1px solid #3b4050;border-radius:8px;padding:10px}'+
 '@media(max-width:720px){.rp-node-dialog{inset:2px!important;width:auto!important;min-width:0!important;height:auto!important;max-height:none!important;resize:none}.rp-node-main{grid-template-columns:1fr;grid-template-rows:minmax(340px,1fr) 260px}.rp-node-editor{height:calc(100dvh - 82px)}.rp-node-inspector{max-height:260px}}';
 document.head.appendChild(st);
}
function clone(v){return JSON.parse(JSON.stringify(v));}
function edgeInputs(graph){
 const out=[];Object.entries(graph).forEach(function(pair){const to=pair[0],node=pair[1];Object.entries(node.inputs||{}).forEach(function(kv){const v=kv[1];if(Array.isArray(v)&&v.length===2&&String(v[0]) in graph)out.push({from:String(v[0]),output:Number(v[1])||0,to:to,input:kv[0]});});});return out;
}
function defaultLayout(graph){
 const ids=Object.keys(graph),level={};let changed=true;
 ids.forEach(function(id){level[id]=0;});
 for(let pass=0;pass<ids.length&&changed;pass++){changed=false;edgeInputs(graph).forEach(function(e){const next=(level[e.from]||0)+1;if(next>level[e.to]){level[e.to]=next;changed=true;}});}
 const rows={};ids.forEach(function(id){const l=Math.min(level[id]||0,8);rows[l]=(rows[l]||0);graph[id]._meta=graph[id]._meta||{};graph[id]._meta.rp_position=[40+l*280,40+rows[l]*190];rows[l]++;});
}
function nodeColor(type){let n=0;for(const c of type)n=(n+c.charCodeAt(0))%colors.length;return colors[n];}
function primitive(v){return !(Array.isArray(v)&&v.length===2)&&v!==null&&typeof v!=='object';}
window.openWorkflowNodeEditor=async function(){
 injectStyle();
 const name=document.getElementById('rp-workflow').value;if(!name)throw Error('เลือก workflow ก่อน');
 const original=await rpApi('/api/comfy/workflows/'+encodeURIComponent(name));const graph=clone(original);
 if(!Object.values(graph).some(function(n){return n._meta&&Array.isArray(n._meta.rp_position);})){defaultLayout(graph);}
 const content=rpDialog('Node Editor · '+name),dialog=document.getElementById('rp-dialog');dialog.classList.add('rp-node-dialog');content.replaceChildren();
 const editor=document.createElement('div');editor.className='rp-node-editor';const toolbar=document.createElement('div');toolbar.className='rp-node-toolbar';const main=document.createElement('div');main.className='rp-node-main';
 const viewport=document.createElement('div');viewport.className='rp-node-viewport';const world=document.createElement('div');world.className='rp-node-world';const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.classList.add('rp-node-links');world.append(svg);viewport.append(world);
 const inspector=document.createElement('div');inspector.className='rp-node-inspector';main.append(viewport,inspector);editor.append(toolbar,main);content.append(editor);
 let selected=null,scale=0.78,panX=10,panY=10,rawMode=false,rawArea=null,linkDrag=null;
 function button(text,title,fn,cls){const b=document.createElement('button');b.className='btn '+(cls||'btn-secondary');b.textContent=text;b.title=title;b.onclick=fn;return b;}
 const status=document.createElement('span');status.className='rp-node-status';
 const zoom=document.createElement('input');zoom.type='range';zoom.min='.25';zoom.max='2';zoom.step='.05';zoom.value=scale;zoom.title='Zoom';zoom.oninput=function(){zoomAt(Number(zoom.value));};
 toolbar.append(button('＋','Add node',addNode),button('⌗','Auto layout',function(){defaultLayout(graph);render();}),button('⤢','Fit all nodes',fit),button('−','Zoom out',function(){zoomAt(scale-.1);}),button('＋','Zoom in',function(){zoomAt(scale+.1);}),button('⌁','Test parameter paths',testPaths),button('{}','Raw JSON',toggleRaw),button('⇩','Export',exportGraph),button('⇧','Import',importGraph),button('✓','Validate',validateGraph),button('💾','Save',saveGraph,''));
 toolbar.append(zoom,status);
 function transform(){world.style.transform='translate('+panX+'px,'+panY+'px) scale('+scale+')';}
 function zoomAt(next,clientX,clientY){next=Math.max(.25,Math.min(2,Number(next)));const rect=viewport.getBoundingClientRect(),x=(clientX==null?rect.width/2:clientX-rect.left),y=(clientY==null?rect.height/2:clientY-rect.top),wx=(x-panX)/scale,wy=(y-panY)/scale;panX=x-wx*next;panY=y-wy*next;scale=next;zoom.value=scale;transform();}
 function position(id){const p=graph[id]._meta&&graph[id]._meta.rp_position;return Array.isArray(p)?p:[40,40];}
 function render(){
  rawMode=false;world.style.display='block';if(rawArea)rawArea.remove();[...world.querySelectorAll('.rp-node')].forEach(function(x){x.remove();});
  Object.entries(graph).forEach(function(pair){const id=pair[0],node=pair[1],pos=position(id),el=document.createElement('div');el.className='rp-node'+(id===selected?' selected':'');el.style.left=pos[0]+'px';el.style.top=pos[1]+'px';el.style.setProperty('--node-color',nodeColor(node.class_type));el.dataset.id=id;
   const head=document.createElement('div');head.className='rp-node-head';head.textContent=(node._meta&&node._meta.title)||node.class_type;const tag=document.createElement('span');tag.className='rp-node-id';tag.textContent='#'+id;head.append(tag);
   const body=document.createElement('div');body.className='rp-node-body';Object.entries(node.inputs||{}).slice(0,12).forEach(function(kv){const line=document.createElement('div'),socket=document.createElement('i');line.className='rp-node-port'+(Array.isArray(kv[1])?' connected':'');line.dataset.input=kv[0];line.textContent=kv[0]+': '+(Array.isArray(kv[1])?'← #'+kv[1][0]+':'+kv[1][1]:String(kv[1]).slice(0,30));socket.className='rp-input-socket';socket.title='Drop connection here · right click to disconnect';socket.onpointerup=function(e){finishLink(id,kv[0],e);};socket.oncontextmenu=function(e){e.preventDefault();e.stopPropagation();if(Array.isArray(node.inputs[kv[0]])){node.inputs[kv[0]]='';render();}};line.append(socket);body.append(line);});
   const output=document.createElement('div'),outSocket=document.createElement('i');output.className='rp-output-label';output.textContent='OUTPUT 0';outSocket.className='rp-output-socket';outSocket.title='Drag to an input port';outSocket.onpointerdown=function(e){startLink(id,0,e);};output.append(outSocket);
   el.append(head,body,output);el.onclick=function(e){e.stopPropagation();selected=id;render();};dragNode(head,el,id);world.append(el);
  });drawLinks();renderInspector();transform();status.textContent=Object.keys(graph).length+' nodes · '+edgeInputs(graph).length+' links';
 }
 function socketPoint(id,input){const el=world.querySelector('.rp-node[data-id="'+CSS.escape(id)+'"]');if(!el)return position(id);const pos=position(id);if(input==null)return [pos[0]+el.offsetWidth,pos[1]+el.offsetHeight-20];const line=[...el.querySelectorAll('.rp-node-port')].find(function(x){return x.dataset.input===input;});return [pos[0],pos[1]+(line?line.offsetTop+line.offsetHeight/2:44)];}
 function curve(x1,y1,x2,y2,color,dashed){const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d','M'+x1+' '+y1+' C'+(x1+Math.max(70,Math.abs(x2-x1)*.45))+' '+y1+' '+(x2-Math.max(70,Math.abs(x2-x1)*.45))+' '+y2+' '+x2+' '+y2);path.setAttribute('fill','none');path.setAttribute('stroke',color);path.setAttribute('stroke-width','3');path.setAttribute('opacity','.82');if(dashed)path.setAttribute('stroke-dasharray','7 5');svg.append(path);return path;}
 function drawLinks(){svg.replaceChildren();edgeInputs(graph).forEach(function(e){const a=socketPoint(e.from,null),b=socketPoint(e.to,e.input);curve(a[0],a[1],b[0],b[1],nodeColor(graph[e.from].class_type));});if(linkDrag){const a=socketPoint(linkDrag.from,null);linkDrag.path=curve(a[0],a[1],linkDrag.x,linkDrag.y,nodeColor(graph[linkDrag.from].class_type),true);}}
 function worldPoint(e){const rect=viewport.getBoundingClientRect();return [(e.clientX-rect.left-panX)/scale,(e.clientY-rect.top-panY)/scale];}
 function startLink(from,output,e){e.preventDefault();e.stopPropagation();const pt=worldPoint(e);linkDrag={from:String(from),output:Number(output)||0,x:pt[0],y:pt[1]};window.addEventListener('pointermove',moveLink);window.addEventListener('pointerup',cancelLink,{once:true});drawLinks();}
 function moveLink(e){if(!linkDrag)return;const pt=worldPoint(e);linkDrag.x=pt[0];linkDrag.y=pt[1];drawLinks();}
 function finishLink(to,input,e){if(!linkDrag)return;e.preventDefault();e.stopPropagation();graph[to].inputs[input]=[linkDrag.from,linkDrag.output];linkDrag=null;window.removeEventListener('pointermove',moveLink);drawLinks();render();}
 function cancelLink(){setTimeout(function(){if(linkDrag){linkDrag=null;window.removeEventListener('pointermove',moveLink);drawLinks();}},0);}
 function dragNode(handle,el,id){handle.onpointerdown=function(e){e.stopPropagation();handle.setPointerCapture(e.pointerId);const start=[e.clientX,e.clientY],base=position(id).slice();handle.onpointermove=function(m){graph[id]._meta.rp_position=[base[0]+(m.clientX-start[0])/scale,base[1]+(m.clientY-start[1])/scale];el.style.left=graph[id]._meta.rp_position[0]+'px';el.style.top=graph[id]._meta.rp_position[1]+'px';drawLinks();};handle.onpointerup=function(){handle.onpointermove=null;};};}
 function field(label,value,onchange,multiline){const wrap=document.createElement('label');wrap.className='rp-node-field';wrap.textContent=label;const input=document.createElement(multiline?'textarea':'input');input.className='form-input';input.value=value==null?'':value;input.onchange=function(){onchange(input.value);render();};wrap.append(input);return wrap;}
 function renderInspector(){inspector.replaceChildren();if(!selected||!graph[selected]){inspector.textContent='เลือก node เพื่อแก้ไข inputs และ connections';return;}const node=graph[selected],h=document.createElement('h3');h.textContent=node.class_type+' #'+selected;inspector.append(h);
  inspector.append(field('Title',(node._meta&&node._meta.title)||'',function(v){node._meta=node._meta||{};node._meta.title=v;}));
   Object.entries(node.inputs||{}).forEach(function(kv){const key=kv[0],v=kv[1];if(Array.isArray(v)&&v.length===2&&String(v[0]) in graph){const group=document.createElement('div');group.className='rp-node-field';group.innerHTML='<span class="rp-link-label">'+key+' · connection</span>';const src=document.createElement('select');src.className='form-input';Object.keys(graph).forEach(function(id){src.append(new Option('#'+id+' '+graph[id].class_type,id));});src.value=String(v[0]);const output=document.createElement('input');output.className='form-input';output.type='number';output.min='0';output.value=v[1];src.onchange=function(){node.inputs[key]=[src.value,Number(output.value)||0];render();};output.onchange=src.onchange;group.append(src,output);inspector.append(group);}
   else if(primitive(v)){inspector.append(field(key,String(v),function(raw){if(typeof v==='number')node.inputs[key]=Number(raw);else if(typeof v==='boolean')node.inputs[key]=raw==='true';else node.inputs[key]=raw;},typeof v==='string'&&v.length>70));}
   else if(v!==null&&typeof v==='object'){inspector.append(field(key,JSON.stringify(v),function(raw){try{node.inputs[key]=JSON.parse(raw);}catch(e){node.inputs[key]=raw;}},true));}
   });
  inspector.append(button('＋ Input','Add input',function(){const key=prompt('Input name');if(key&&!Object.hasOwn(node.inputs,key)){node.inputs[key]='';render();}}),button('🗑 Node','Delete node',function(){if(confirm('Delete node #'+selected+'?')){delete graph[selected];Object.values(graph).forEach(function(n){Object.keys(n.inputs||{}).forEach(function(k){const v=n.inputs[k];if(Array.isArray(v)&&String(v[0])===selected)delete n.inputs[k];});});selected=null;render();}},'btn-danger'));
 }
 function addNode(){const type=prompt('ComfyUI class_type');if(!type)return;let id=prompt('Node ID',String(Math.max(0,...Object.keys(graph).map(Number).filter(Number.isFinite))+1));if(!id||graph[id])return alert('Node ID exists');graph[id]={inputs:{},class_type:type,_meta:{title:type,rp_position:[80,80]}};selected=id;render();}
 function fit(){const ps=Object.keys(graph).map(position);if(!ps.length)return;const minX=Math.min(...ps.map(p=>p[0])),minY=Math.min(...ps.map(p=>p[1])),maxX=Math.max(...ps.map(p=>p[0]+240)),maxY=Math.max(...ps.map(p=>p[1]+170));scale=Math.min(.95,(viewport.clientWidth-30)/(maxX-minX),(viewport.clientHeight-30)/(maxY-minY));panX=15-minX*scale;panY=15-minY*scale;zoom.value=scale;transform();}
 function toggleRaw(){if(!rawMode){rawMode=true;world.style.display='none';rawArea=document.createElement('textarea');rawArea.className='rp-node-raw';rawArea.value=JSON.stringify(graph,null,2);viewport.append(rawArea);}else{try{const parsed=JSON.parse(rawArea.value);Object.keys(graph).forEach(k=>delete graph[k]);Object.assign(graph,parsed);render();}catch(e){alert('JSON invalid: '+e.message);}}}
 function cleanForSave(){const data=clone(graph);Object.values(data).forEach(function(n){if(n._meta&&n._meta.rp_position&&!n._meta.title)delete n._meta.title;});return data;}
 async function testPaths(){
  if(rawMode)toggleRaw();
  await rpApi('/api/comfy/workflows/'+encodeURIComponent(name),cleanForSave());
  const report=await rpApi('/api/comfy/path-test?workflow='+encodeURIComponent(name));
  world.querySelectorAll('.rp-node').forEach(function(el){el.classList.remove('path-ok');});
  inspector.replaceChildren();const title=document.createElement('h3');title.textContent='Parameter Path Test';inspector.append(title);
  const summary=document.createElement('div');summary.className='rp-path-value';summary.textContent=(report.comfy_online?'ComfyUI online':'ComfyUI offline')+' · Output nodes: '+(report.output_nodes.join(', ')||'none')+' · No image was queued';inspector.append(summary);
  const list=document.createElement('div');list.className='rp-path-result';
  report.checks.forEach(function(check){const card=document.createElement('div');card.className='rp-path-card '+(check.connected&&check.reaches_output?'ok':'bad');const head=document.createElement('strong');head.textContent=(check.connected&&check.reaches_output?'✓ ':'✕ ')+check.parameter+' = '+String(check.configured||'(empty)');card.append(head);
   if(!check.targets.length){const msg=document.createElement('div');msg.className='rp-path-value';msg.textContent='No mapping or placeholder. This setting is not sent to the workflow.';card.append(msg);}
   check.targets.forEach(function(target){const line=document.createElement('div');line.className='rp-path-route';line.textContent='#'+target.node_id+' '+(target.title||target.node_type||'')+' · '+target.input+' · '+target.method+' · '+(target.reaches_output?'reaches output':'no route to output');card.append(line);const value=document.createElement('div');value.className='rp-path-value';value.textContent='workflow: '+JSON.stringify(target.current)+' → configured: '+JSON.stringify(target.configured);card.append(value);const nodeEl=world.querySelector('.rp-node[data-id="'+CSS.escape(String(target.node_id))+'"]');if(nodeEl&&target.valid)nodeEl.classList.add('path-ok');});list.append(card);
  });
  if(report.unknown_node_types.length){const warn=document.createElement('div');warn.className='rp-path-card bad';warn.textContent='Unknown node types: '+report.unknown_node_types.join(', ');list.append(warn);}
  inspector.append(list);status.textContent='Path test complete';
 }
 async function validateGraph(){await rpApi('/api/comfy/workflows/'+encodeURIComponent(name),cleanForSave());status.textContent='Valid ✓ (saved)';}
 async function saveGraph(){if(rawMode)toggleRaw();await rpApi('/api/comfy/workflows/'+encodeURIComponent(name),cleanForSave());status.textContent='Saved ✓';if(typeof showNotice==='function')showNotice('บันทึก workflow แล้ว');}
 function exportGraph(){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(cleanForSave(),null,2)],{type:'application/json'}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
 function importGraph(){const input=document.createElement('input');input.type='file';input.accept='.json';input.onchange=async function(){try{const parsed=JSON.parse(await input.files[0].text());Object.keys(graph).forEach(k=>delete graph[k]);Object.assign(graph,parsed);if(!Object.values(graph).some(n=>n._meta&&n._meta.rp_position))defaultLayout(graph);selected=null;render();}catch(e){alert('Import failed: '+e.message);}};input.click();}
 let panning=false,startPan=null;basePan=null;
 viewport.onpointerdown=function(e){if(e.target!==viewport&&e.target!==world&&e.target!==svg)return;panning=true;startPan=[e.clientX,e.clientY];basePan=[panX,panY];viewport.setPointerCapture(e.pointerId);};
 viewport.onpointermove=function(e){if(panning){panX=basePan[0]+e.clientX-startPan[0];panY=basePan[1]+e.clientY-startPan[1];transform();}};
 viewport.onpointerup=function(){panning=false;};viewport.onwheel=function(e){e.preventDefault();zoomAt(scale+(e.deltaY<0?.08:-.08),e.clientX,e.clientY);};
 new ResizeObserver(function(){drawLinks();}).observe(viewport);
 render();setTimeout(fit,30);
};
window.editWorkflow=function(){return openWorkflowNodeEditor();};
})();
