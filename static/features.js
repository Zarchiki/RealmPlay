// RealmPlay settings and card/workflow editors. All data stays on the server.
const rp = {config:null, card:null};
const rpChatCategories=[
  ['base','ข้อความทั่วไป','ข้อความแชท'],['time','เวลา / สถานที่','D6 | Sun | 08:00'],
  ['narration','คำบรรยาย','เช้าวันนี้อากาศแจ่มใส'],['speaker','ชื่อผู้พูด','💬 Lilia |'],
  ['speech','คำพูด','“สวัสดี!”'],['action','กิริยา / การกระทำ','เธอยิ้มให้คุณ'],
  ['info','Info','Tier: SSS'],['scenario','Scenario','Hall A, morning'],
  ['ooc','OOC','((OOC: หมายเหตุ))'],['code','Code block','plain text']
];
function applyChatDisplaySettings(settings){
  const chat=document.getElementById('chat-history');if(!chat)return;
  chat.classList.remove('rp-layout-bubbles','rp-layout-clean','rp-layout-story');
  chat.classList.add('rp-layout-'+settings.layout);
  chat.style.setProperty('--rp-chat-font',settings.font==='serif'?'Georgia, serif':settings.font==='monospace'?'Consolas, monospace':'inherit');
  for(const [key] of rpChatCategories){
    const value=settings.styles[key];if(!value)continue;
    chat.style.setProperty(`--rp-${key}-color`,value.color);
    chat.style.setProperty(`--rp-${key}-size`,`${value.size}px`);
    chat.style.setProperty(`--rp-${key}-weight`,value.bold?'700':'400');
    chat.style.setProperty(`--rp-${key}-style`,value.italic?'italic':'normal');
  }
}
function renderChatDisplaySettings(settings){
  const panel=document.getElementById('rp-chatsettings-panel');if(!panel)return;
  panel.innerHTML=`<label class="rp-chat-layout">รูปแบบแชท<select id="rp-chat-layout" class="form-input" onchange="previewChatDisplaySettings()"><option value="bubbles">Bubbles</option><option value="clean">Clean</option><option value="story">Story</option></select></label><label class="rp-chat-layout">รูปแบบอักษร<select id="rp-chat-font" class="form-input" onchange="previewChatDisplaySettings()"><option value="system">System</option><option value="serif">Serif</option><option value="monospace">Monospace</option></select></label><p class="rp-chat-settings-note">ปรับแล้วเห็นผลในแชททันที กดบันทึกเพื่อใช้บนอุปกรณ์อื่น</p>${rpChatCategories.map(([key,title,sample])=>`<div class="rp-chat-style-row" data-chat-key="${key}"><strong>${title}</strong><div class="rp-chat-control-grid"><label>ขนาด<input class="form-input" data-chat-field="size" type="number" min="10" max="32" step="1" oninput="previewChatDisplaySettings()"></label><label>สี<input data-chat-field="color" type="color" oninput="previewChatDisplaySettings()"></label><label><input data-chat-field="bold" type="checkbox" onchange="previewChatDisplaySettings()"> หนา</label><label><input data-chat-field="italic" type="checkbox" onchange="previewChatDisplaySettings()"> เอียง</label></div><small class="rp-chat-sample">${sample}</small></div>`).join('')}<div class="rp-chat-settings-actions"><button class="btn" onclick="saveChatDisplaySettings()">บันทึก</button><button class="btn btn-secondary" onclick="resetChatDisplaySettings()">คืนค่าเริ่มต้น</button></div><small id="rp-chat-settings-status"></small>`;
  panel.querySelector('#rp-chat-layout').value=settings.layout;
  panel.querySelector('#rp-chat-font').value=settings.font;
  for(const [key] of rpChatCategories){
    const row=panel.querySelector(`[data-chat-key="${key}"]`),value=settings.styles[key];
    for(const field of ['size','color'])row.querySelector(`[data-chat-field="${field}"]`).value=value[field];
    for(const field of ['bold','italic'])row.querySelector(`[data-chat-field="${field}"]`).checked=value[field];
  }
  previewChatDisplaySettings(false);
}
function collectChatDisplaySettings(){
  const panel=document.getElementById('rp-chatsettings-panel');
  const settings={layout:panel.querySelector('#rp-chat-layout').value,font:panel.querySelector('#rp-chat-font').value,styles:{}};
  for(const [key] of rpChatCategories){
    const row=panel.querySelector(`[data-chat-key="${key}"]`);
    const size=Number(row.querySelector('[data-chat-field="size"]').value);
    if(!Number.isInteger(size)||size<10||size>32)throw Error(`${key}: ขนาดต้องอยู่ระหว่าง 10–32`);
    settings.styles[key]={size,color:row.querySelector('[data-chat-field="color"]').value,bold:row.querySelector('[data-chat-field="bold"]').checked,italic:row.querySelector('[data-chat-field="italic"]').checked};
  }
  return settings;
}
function previewChatDisplaySettings(markDirty=true){
  try{
    const settings=collectChatDisplaySettings();applyChatDisplaySettings(settings);
    const panel=document.getElementById('rp-chatsettings-panel');
    for(const [key] of rpChatCategories){const value=settings.styles[key],sample=panel.querySelector(`[data-chat-key="${key}"] .rp-chat-sample`);sample.style.cssText=`color:${value.color};font-size:${value.size}px;font-weight:${value.bold?'700':'400'};font-style:${value.italic?'italic':'normal'}`;}
    if(markDirty)panel.querySelector('#rp-chat-settings-status').textContent='ยังไม่บันทึก';
  }catch(error){document.getElementById('rp-chat-settings-status').textContent=error.message;}
}
async function loadChatDisplaySettings(){
  if(!token)return;
  const settings=await rpApi('/api/chat-display-settings');rp.chatSettings=settings;
  renderChatDisplaySettings(settings);applyChatDisplaySettings(settings);
}
async function saveChatDisplaySettings(){return rpRun(async()=>{
  const settings=collectChatDisplaySettings();const saved=await rpApi('/api/chat-display-settings',settings);
  rp.chatSettings=saved;applyChatDisplaySettings(saved);
  document.getElementById('rp-chat-settings-status').textContent='บันทึกแล้ว';
});}
async function resetChatDisplaySettings(){return rpRun(async()=>{
  const defaults=await rpApi('/api/chat-display-settings/defaults');
  const saved=await rpApi('/api/chat-display-settings',defaults);
  rp.chatSettings=saved;renderChatDisplaySettings(saved);applyChatDisplaySettings(saved);
  document.getElementById('rp-chat-settings-status').textContent='คืนค่าเริ่มต้นและบันทึกแล้ว';
});}
async function rpApi(path, body, method='POST') {
  const res=await fetch(path,{method:body===undefined?'GET':method,headers:{Authorization:`Bearer ${token}`,...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const data=await res.json(); if(!res.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data)); return data;
}

async function runRealmPlayAudit(){
  const target=document.getElementById('rp-audit-results');if(!target||!token)return;
  target.textContent='กำลังตรวจสอบ…';
  const request=async path=>{const response=await fetch(path,{headers:{Authorization:`Bearer ${token}`},cache:'no-store'});if(!response.ok)throw Error(`${path} (${response.status})`);return response.json();};
  const outcome=await Promise.allSettled([request('/api/auth/me'),request('/api/status/all'),request('/api/rules'),request('/api/characters'),request('/api/statistics'),request('/api/configuration')]);
  const value=i=>outcome[i].status==='fulfilled'?outcome[i].value:null;
  const auth=value(0),status=value(1),rules=value(2),characters=value(3),statistics=value(4),config=value(5);
  const items=[
    ['RealmPlay backend',!!auth,auth?`Logged in as ${auth.display_name||auth.username}`:'Authentication API unavailable'],
    ['Single-login protection',!!auth,'One active session per account; a newer login revokes the prior device session'],
    ['Built-in LLM',status?.engine?.state==='ready',status?.engine?.state==='ready'?'Model ready':`State: ${status?.engine?.state||'offline'}`],
    ['ComfyUI image generation',!!status?.comfy?.connected,status?.comfy?.connected?`Connected: ${status.comfy.address}`:`Unavailable: ${status?.comfy?.address||'not configured'}`],
    ['TTS + RVC',!!status?.voice?.tts_voice,`${status?.voice?.tts_voice||'No TTS voice'} · RVC ${status?.voice?.rvc_enabled?'enabled':'disabled'}`],
    ['Rules & boundaries',!!rules && Object.keys(rules.rules||{}).length>0,`${Object.keys(rules?.rules||{}).length} registered rules`],
    ['Image trigger',!!config?.rules?.image_trigger,config?.rules?.image_trigger?'Natural language and /image command enabled':'Disabled by rule setting'],
    ['Character library',Array.isArray(characters),Array.isArray(characters)?`${characters.length} character(s) available`:'Could not read characters'],
    ['Statistics and audit log',!!statistics,statistics?`${statistics.retained_runs||0} retained execution trace(s)`:'Statistics API unavailable']
  ];
  target.replaceChildren(...items.map(([name,pass,detail])=>{const row=document.createElement('div');row.className=`rp-audit-row ${pass?'pass':'check'}`;const icon=document.createElement('span');icon.textContent=pass?'✓':'!';const text=document.createElement('div');const strong=document.createElement('strong');strong.textContent=name;const small=document.createElement('small');small.textContent=detail;text.append(strong,small);row.append(icon,text);return row;}));
}
function rpRun(fn){return Promise.resolve().then(fn).catch(e=>typeof showNotice==='function'?showNotice(e.message,'error'):alert(e.message));}
const userImageUrls={profile:null,avatar:null};
let userImagesLoadVersion=0;
function refreshUserIcons(){
  const fallback=`https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(currentUser||'rp_user')}`;
  const top=document.getElementById('top-user-avatar');
  if(top)top.src=userImageUrls.profile||userImageUrls.avatar||fallback;
  const chatImage=userImageUrls.avatar||userImageUrls.profile||fallback;
  for(const image of document.querySelectorAll('.msg-row.user .msg-avatar-icon'))image.src=chatImage;
}
async function loadUserImages(){
  if(!token)return;
  const version=++userImagesLoadVersion;
  const requestToken=token;
  for(const kind of ['profile','avatar']){
    const response=await fetch(`/api/auth/images/${kind}`,{headers:{Authorization:`Bearer ${requestToken}`},cache:'no-store'});
    if(version!==userImagesLoadVersion||token!==requestToken)return;
    const preview=document.getElementById(kind==='profile'?'modal-profile-image':'modal-avatar');
    if(response.status===404){
      if(userImageUrls[kind])URL.revokeObjectURL(userImageUrls[kind]);
      userImageUrls[kind]=null;
      if(preview){preview.removeAttribute('src');preview.style.display='none';}
      refreshUserIcons();
      continue;
    }
    if(!response.ok)throw Error(`โหลด ${kind} ไม่สำเร็จ (${response.status})`);
    const blob=await response.blob();
    if(version!==userImagesLoadVersion||token!==requestToken)return;
    const url=URL.createObjectURL(blob);
    if(userImageUrls[kind])URL.revokeObjectURL(userImageUrls[kind]);
    userImageUrls[kind]=url;if(preview){preview.src=url;preview.style.display='block';}
    refreshUserIcons();
  }
}
const chatBubbleDisplay={user:{url:null,scale:1,x:0,y:0},character:{url:null,scale:1,x:0,y:0}};
async function bubbleImageUrl(target){
  const path=target==='user'?'/api/chat-display/user/image':`/api/chat-display/characters/${encodeURIComponent(activeCharacter)}/image`;
  const response=await fetch(path,{headers:{Authorization:`Bearer ${token}`},cache:'no-store'});
  if(response.status===404)return null;
  if(!response.ok)throw Error('Unable to load display image');
  return URL.createObjectURL(await response.blob());
}
async function loadChatBubbleDisplay(){
  if(!token||!activeCharacter)return;
  const [settings,userUrl,characterUrl]=await Promise.all([
    rpApi(`/api/chat-display/settings?character_name=${encodeURIComponent(activeCharacter)}`),bubbleImageUrl('user'),bubbleImageUrl('character')
  ]);
  for(const target of ['user','character']){
    if(chatBubbleDisplay[target].url)URL.revokeObjectURL(chatBubbleDisplay[target].url);
    Object.assign(chatBubbleDisplay[target],settings[target]||{}, {url:target==='user'?userUrl:characterUrl});
  }
  applyChatBubbleDisplay();
}
function applyBubbleImage(image,target){
  const display=chatBubbleDisplay[target];if(!display||!image)return;
  const fallback=target==='user'?(userImageUrls.avatar||userImageUrls.profile||`https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(currentUser||'rp')}`):`/api/characters/${encodeURIComponent(activeCharacter)}/avatar`;
  image.src=display.url||fallback;
  let frame=image.parentElement;
  if(!frame?.classList.contains('bubble-avatar-frame')){frame=document.createElement('button');frame.type='button';frame.className=`bubble-avatar-frame ${target}`;frame.title=`Customize ${target} display image`;frame.setAttribute('aria-label',frame.title);image.replaceWith(frame);frame.append(image);}
  setBubbleImageAdjustment(image,display);
  frame.onclick=(event)=>{event.stopPropagation();openChatBubbleDisplayEditor(target);};
}
function syncCharacterDisplayIcon(image){
  if(!image||!activeCharacter)return;
  const display=chatBubbleDisplay.character;
  image.src=display.url||`/api/characters/${encodeURIComponent(activeCharacter)}/avatar`;
  setBubbleImageAdjustment(image,display);
}
function setBubbleImageAdjustment(image,display){
  const scale=Number(display?.scale)||1;
  const x=Math.max(-100,Math.min(100,Number.isFinite(Number(display?.x))?Number(display.x):0));
  const y=Math.max(-100,Math.min(100,Number.isFinite(Number(display?.y))?Number(display.y):0));
  image._bubbleAdjustment={scale:Math.max(1,scale),x,y};
  const render=()=>{
    const frame=image.parentElement,adjustment=image._bubbleAdjustment;
    if(!frame||!adjustment||!image.naturalWidth||!image.naturalHeight)return;
    const frameWidth=frame.clientWidth,frameHeight=frame.clientHeight;
    if(!frameWidth||!frameHeight)return;
    const cover=Math.max(frameWidth/image.naturalWidth,frameHeight/image.naturalHeight);
    const width=image.naturalWidth*cover*adjustment.scale;
    const height=image.naturalHeight*cover*adjustment.scale;
    const offsetX=(adjustment.x/100)*Math.max(0,(width-frameWidth)/2);
    const offsetY=(adjustment.y/100)*Math.max(0,(height-frameHeight)/2);
    image.style.setProperty('width',`${width}px`,'important');
    image.style.setProperty('height',`${height}px`,'important');
    image.style.setProperty('position','absolute','important');
    image.style.setProperty('max-width','none','important');
    image.style.setProperty('max-height','none','important');
    image.style.setProperty('object-fit','fill','important');
    image.style.setProperty('left',`calc(50% + ${offsetX}px)`,'important');
    image.style.setProperty('top',`calc(50% + ${offsetY}px)`,'important');
    image.style.setProperty('transform','translate(-50%,-50%)','important');
  };
  image.addEventListener('load',render,{once:true});
  requestAnimationFrame(render);
  if(typeof ResizeObserver==='function'&&!image._bubbleResizeObserver){
    image._bubbleResizeObserver=new ResizeObserver(render);
    if(image.parentElement)image._bubbleResizeObserver.observe(image.parentElement);
  }
}
function applyChatBubbleDisplay(){
  document.querySelectorAll('.msg-row.user .msg-avatar-icon').forEach(image=>applyBubbleImage(image,'user'));
  document.querySelectorAll('.msg-row.bot .msg-avatar-icon').forEach(image=>applyBubbleImage(image,'character'));
  document.querySelectorAll('.rp-card-hero-display').forEach(syncCharacterDisplayIcon);
}
async function syncCharacterSelectionIcons(){
  if(!token)return;
  const images=[...document.querySelectorAll('#char-list-container .char-card-avatar[data-character-name]')];
  await Promise.all(images.map(async image=>{
    const name=image.dataset.characterName;
    if(!name)return;
    try{
      const [response,settings]=await Promise.all([
        fetch(`/api/chat-display/characters/${encodeURIComponent(name)}/image`,{headers:{Authorization:`Bearer ${token}`},cache:'no-store'}),
        rpApi(`/api/chat-display/settings?character_name=${encodeURIComponent(name)}`)
      ]);
      const adjustment=settings?.character||{scale:1,x:0,y:0};
      setBubbleImageAdjustment(image,adjustment);
      if(response.status===404){
        image.src=`/api/characters/${encodeURIComponent(name)}/avatar`;
        return;
      }
      if(!response.ok)throw Error('display icon unavailable');
      const old=image.dataset.displayObjectUrl;
      if(old)URL.revokeObjectURL(old);
      const url=URL.createObjectURL(await response.blob());
      image.dataset.displayObjectUrl=url;
      image.src=url;
    }catch(_){
      image.src=`/api/characters/${encodeURIComponent(name)}/avatar`;
    }
  }));
}
async function openChatBubbleDisplayEditor(target){return rpRun(async()=>{
  if(target==='character'&&!activeCharacter)return;
  const display=chatBubbleDisplay[target],content=rpDialog(`${target==='user'?'User':'Character'} Display Image Bubble`);
  const previewFrame=document.createElement('div');previewFrame.className='bubble-editor-preview';const preview=document.createElement('img');previewFrame.append(preview);content.append(previewFrame);
  const inputs={};
  for(const [key,label,min,max,step] of [['scale','Scale',1,3,.01],['x','Move horizontal',-100,100,1],['y','Move vertical',-100,100,1]]){
    const row=document.createElement('label');row.className='bubble-editor-control';row.textContent=label;const input=document.createElement('input');input.type='range';input.min=min;input.max=max;input.step=step;input.value=display[key]??(key==='scale'?1:0);const value=document.createElement('output');const redraw=()=>{const adjustment={scale:Number(inputs.scale?.value||1),x:Number(inputs.x?.value||0),y:Number(inputs.y?.value||0)};value.textContent=key==='scale'?`${Number(input.value).toFixed(2)}×`:`${input.value}%`;setBubbleImageAdjustment(preview,adjustment);};input.oninput=redraw;row.append(input,value);content.append(row);inputs[key]=input;redraw();}
  const setPreview=()=>{preview.src=display.url||(target==='user'?(userImageUrls.avatar||userImageUrls.profile||''): `/api/characters/${encodeURIComponent(activeCharacter)}/avatar`);};setPreview();
  const file=document.createElement('input');file.type='file';file.accept='image/*';file.hidden=true;file.onchange=()=>{const picked=file.files?.[0];if(!picked)return;preview.src=URL.createObjectURL(picked);};
  const actions=document.createElement('div');actions.className='rp-card-actions';
  const upload=rpCardButton('Upload image',()=>file.click());
  const resetImage=rpCardButton('Use default',()=>rpRun(async()=>{
    const path=target==='user'?'/api/chat-display/user/image':`/api/chat-display/characters/${encodeURIComponent(activeCharacter)}/image`;
    await rpApi(path,{},'DELETE');
    await rpApi('/api/chat-display/settings',{target,character_name:target==='character'?activeCharacter:'',scale:1,x:0,y:0});
    file.value='';
    inputs.scale.value='1';inputs.x.value='0';inputs.y.value='0';
    await loadChatBubbleDisplay();
    await syncCharacterSelectionIcons();
    setPreview();
    for(const input of Object.values(inputs))input.dispatchEvent(new Event('input'));
  }));
  const save=rpCardButton('Save',()=>rpRun(async()=>{const path=target==='user'?'/api/chat-display/user/image':`/api/chat-display/characters/${encodeURIComponent(activeCharacter)}/image`;if(file.files?.[0]){const form=new FormData();form.append('file',file.files[0]);const response=await fetch(path,{method:'POST',headers:{Authorization:`Bearer ${token}`},body:form});if(!response.ok)throw Error('Image upload failed');}await rpApi('/api/chat-display/settings',{target,character_name:target==='character'?activeCharacter:'',scale:Number(inputs.scale.value),x:Number(inputs.x.value),y:Number(inputs.y.value)});await loadChatBubbleDisplay();await syncCharacterSelectionIcons();document.getElementById('rp-dialog').close();}));save.className='btn';actions.append(upload,resetImage,save,file);content.append(actions);
});}
async function uploadUserImage(kind,input){return rpRun(async()=>{
  const file=input.files?.[0];if(!file)return;
  const form=new FormData();form.append('file',file);
  const response=await fetch(`/api/auth/images/${kind}`,{method:'POST',headers:{Authorization:`Bearer ${token}`},body:form});
  if(!response.ok){const data=await response.json();throw Error(data.detail||'อัปโหลดรูปไม่สำเร็จ');}
  input.value='';await loadUserImages();
});}
function openImagePromptDialog(title,onGenerate,defaultPositive=''){return rpRun(async()=>{
  const settings=await rpApi('/api/configuration');
  const content=rpDialog(title),dialog=document.getElementById('rp-dialog');
  const form=document.createElement('div');form.className='rp-image-prompt-dialog';
  form.innerHTML='<label>Positive</label><textarea class="form-input" data-prompt="positive" rows="5" placeholder="Describe the image to generate"></textarea><label>Negative</label><textarea class="form-input" data-prompt="negative" rows="4" placeholder="Unwanted details"></textarea><div class="rp-image-prompt-actions"></div>';
  const positive=form.querySelector('[data-prompt="positive"]'),negative=form.querySelector('[data-prompt="negative"]');
  positive.value=defaultPositive||'';
  negative.value=settings.comfy?.negative_prompt||'';
  const actions=form.querySelector('.rp-image-prompt-actions');
  const cancel=rpCardButton('Cancel',()=>dialog.close());
  const generate=rpCardButton('Generate',()=>rpRun(async()=>{
    if(!positive.value.trim())throw Error('กรอก Positive prompt ก่อน');
    generate.disabled=true;generate.textContent='Generating...';
    try{await onGenerate(positive.value.trim(),negative.value.trim());dialog.close();}
    finally{generate.disabled=false;generate.textContent='Generate';}
  }));generate.className='btn';actions.append(cancel,generate);content.append(form);positive.focus();
});}
function confirmImageDelete(label){
  if(typeof openConfirmDialog==='function'){
    return openConfirmDialog(`ลบ ${label} หรือไม่? การกระทำนี้ไม่สามารถย้อนกลับได้`,'ยืนยันการลบ');
  }
  return new Promise(resolve=>{
    const content=rpDialog('Confirm delete'),dialog=document.getElementById('rp-dialog');
    let settled=false;const finish=value=>{if(settled)return;settled=true;resolve(value);};
    const text=document.createElement('p');text.textContent=`Delete ${label}? This cannot be undone.`;
    const actions=document.createElement('div');actions.className='rp-image-prompt-actions';
    const cancel=rpCardButton('Cancel',()=>{finish(false);dialog.close();});
    const remove=rpCardButton('Delete',()=>{finish(true);dialog.close();});remove.className='btn rp-delete-button';
    dialog.addEventListener('close',()=>finish(false),{once:true});dialog.addEventListener('cancel',()=>finish(false),{once:true});actions.append(cancel,remove);content.append(text,actions);
  });
}
function openUserProfileGenerateDialog(){return openImagePromptDialog('Generate User Profile Image',async(positive,negative)=>{
  await rpApi('/api/auth/profile-image/generate',{positive,negative});await loadUserImages();
});}
async function deleteUserProfileImage(){if(!await confirmImageDelete('User Profile Image'))return;return rpRun(async()=>{
  await rpApi('/api/auth/images/profile',{},'DELETE');await loadUserImages();
});}
function rpField(key,label,value,type='text',step='1') {
  return `<label class="setting-group" style="display:block">${label}<input class="form-input" id="rp-${key}" type="${type}" step="${step}" value="${escapeHtml(String(value??''))}"></label>`;
}
function rpKvCacheField(key,label,value) {
  const selected=String(value||'q8_0');
  const options=[['q8_0','q8_0 — แนะนำ: ประหยัด VRAM, คุณภาพแทบไม่ต่าง'],['q4_0','q4_0 — ประหยัด VRAM มากขึ้น, คุณภาพลดลงเล็กน้อย'],['f16','f16 — คุณภาพสูงสุด, ใช้ VRAM มากสุด']];
  const tooltip='รูปแบบหน่วยความจำ KV cache ของ LLM ค่าที่แนะนำ: q8_0 สำหรับ 9B บน VRAM 12 GB ผลเมื่อปรับ: q4_0 ลด VRAM ได้มากกว่าแต่คุณภาพอาจลดลง; f16 ใช้ VRAM มากที่สุด';
  return `<label class="setting-group" style="display:block">${label}<button class="parameter-help" type="button" aria-label="คำอธิบาย ${label}">?<span class="parameter-tooltip" role="tooltip">${tooltip}</span></button><select class="form-input" id="rp-${key}">${options.map(([option,text])=>`<option value="${option}" ${option===selected?'selected':''}>${text}</option>`).join('')}</select></label>`;
}
const rpSamplingSpecs=[
  ['temperature','Temperature',0,5,.01],['top_p','Top-P',0,1,.01],['top_k','Top-K',0,100000,1],
  ['top_a','Top-A',0,1,.01],['min_p','Min-P',0,1,.01],['typical_p','Typical-P',0,1,.01],['tfs_z','Tail Free Sampling',0,1,.01],
  ['repetition_penalty','Repetition Penalty',0,3,.01],['repeat_last_n','Repeat Last N',0,131072,1],
  ['presence_penalty','Presence Penalty',-2,2,.01],['frequency_penalty','Frequency Penalty',-2,2,.01],
  ['max_tokens','Max Tokens',1,131072,1],['mirostat','Mirostat Mode',0,2,1],
  ['mirostat_tau','Mirostat Tau',0,20,.01],['mirostat_eta','Mirostat Eta',0,2,.01],
  ['dynatemp_range','Dynamic Temperature Range',0,5,.01],['dynatemp_exponent','Dynamic Temperature Exponent',0,5,.01],
  ['xtc_probability','XTC Probability',0,1,.01],['xtc_threshold','XTC Threshold',0,1,.01],
  ['dry_multiplier','DRY Multiplier',0,10,.01],['dry_base','DRY Base',0,10,.01],['dry_allowed_length','DRY Allowed Length',0,1000,1]
];
const rpBasicSamplingKeys=['temperature','top_p','top_k','top_a','repetition_penalty','max_tokens'];
const rpSamplingHelp={
  temperature:'ควบคุมความสุ่มของคำตอบ ค่าที่แนะนำ: 0.7 สำหรับแชตทั่วไป, 0.5 สำหรับคำตอบแม่นยำ, 0.9 สำหรับงานสร้างสรรค์ ผลเมื่อปรับ: ลดค่าจะนิ่งขึ้น; เพิ่มค่าจะหลากหลายขึ้นแต่เสี่ยงหลุดประเด็น',
  top_p:'จำกัดชุดคำที่โมเดลใช้สุ่มเลือก ค่าที่แนะนำ: 0.9 สำหรับการใช้งานส่วนใหญ่ ผลเมื่อปรับ: ลดค่าจะโฟกัสขึ้น; เพิ่มค่าจะทำให้สำนวนหลากหลายและคาดเดาได้น้อยลง',
  top_k:'จำกัดจำนวนคำที่มีโอกาสสูงสุดก่อนสุ่มเลือก ค่าที่แนะนำ: 40; ตั้งเป็น 0 เพื่อไม่จำกัด ผลเมื่อปรับ: ลดค่าจะทำให้คำตอบระมัดระวังขึ้น; เพิ่มค่าจะเปิดทางเลือกคำมากขึ้นและอาจหลากหลายกว่า',
  top_a:'คัดคำที่มีโอกาสต่ำมากออกแบบปรับตามความน่าจะเป็น ค่าที่แนะนำสำหรับระบบนี้: 0.02 ผลเมื่อปรับ: เพิ่มค่าจะตัดคำที่ไม่น่าเป็นไปได้ ลดคำตอบแปลก ๆ แต่ถ้าสูงเกินไปอาจทำให้คำตอบแคบเกินไป',
  min_p:'ตัดคำที่มีโอกาสต่ำเมื่อเทียบกับคำที่น่าจะเป็นที่สุด ค่าที่แนะนำสำหรับระบบนี้: 0.05 ผลเมื่อปรับ: เพิ่มค่าจะลดคำหลุดประเด็น แต่สูงเกินไปทำให้ภาษาแข็งหรือวนซ้ำได้',
  typical_p:'เลือกคำที่มีความคาดหมายใกล้เคียงรูปแบบปกติ ค่าที่แนะนำสำหรับระบบนี้: 1.0 (ปิด) ผลเมื่อปรับ: ลดค่าจะบังคับสำนวนมากขึ้น และอาจทำให้คำตอบแปลกหรือปนภาษา',
  tfs_z:'Tail Free Sampling ใช้ตัดหางของการกระจายคำ ค่าที่แนะนำ: 1.0 (ปิด) ผลเมื่อปรับ: ลดค่าจะตัดตัวเลือกคำมากขึ้น; ควรจูนเมื่อใช้ TFS โดยเฉพาะเท่านั้น',
  repetition_penalty:'ลดโอกาสที่โมเดลจะใช้คำหรือวลีเดิมซ้ำ ค่าที่แนะนำสำหรับระบบนี้: 1.10 ผลเมื่อปรับ: เพิ่มค่าจะลดคำซ้ำ แต่สูงเกินไปทำให้ประโยคฝืนธรรมชาติ',
  repeat_last_n:'จำนวน token ล่าสุดที่ใช้ตรวจคำซ้ำ ค่าที่แนะนำสำหรับระบบนี้: 256 ผลเมื่อปรับ: เพิ่มค่าจะกันการซ้ำในช่วงยาวขึ้น แต่สูงเกินไปอาจตัดคำปกติและทำให้ตอบแปลก',
  presence_penalty:'ลงโทษคำที่เคยปรากฏ เพื่อผลักให้เปลี่ยนหัวข้อ ค่าที่แนะนำสำหรับระบบนี้: 0.0 ผลเมื่อปรับ: เพิ่มค่าจะเปลี่ยนหัวข้อไวขึ้น แต่อาจทำให้สำนวนกระโดดหรือปนภาษา',
  frequency_penalty:'ลงโทษคำตามจำนวนครั้งที่ใช้ซ้ำ ค่าที่แนะนำสำหรับระบบนี้: 0.05 ผลเมื่อปรับ: เพิ่มค่าเล็กน้อยช่วยลดคำซ้ำ; สูงเกินไปทำให้หลีกเลี่ยงคำจำเป็นและภาษาไม่ลื่น',
  max_tokens:'จำนวน token สูงสุดต่อคำตอบ ค่าที่แนะนำสำหรับระบบนี้: 236 ผลเมื่อปรับ: ต่ำเกินไปตัดกลางประโยค; สูงเกินไปเปิดโอกาสให้คำตอบยืดเยื้อ',
  mirostat:'ควบคุมความหลากหลายแบบอัตโนมัติ ค่าที่แนะนำสำหรับระบบนี้: 0 (ปิด) ผลเมื่อปรับ: โหมด 1 หรือ 2 จะเปลี่ยนพฤติกรรมการสุ่มและใช้ Tau/Eta แต่จากการทดสอบช้าลงและภาษาฝืนกว่า',
  mirostat_tau:'เป้าหมายความหลากหลายของ Mirostat ค่าที่แนะนำ: 5.0 ผลเมื่อปรับ: ค่าสูงทำให้คำตอบหลากหลายขึ้น ค่านี้ไม่มีผลเมื่อ Mirostat Mode เป็น 0',
  mirostat_eta:'ความเร็วที่ Mirostat ปรับตัวเข้าหา Tau ค่าที่แนะนำ: 0.1 ผลเมื่อปรับ: ค่าสูงตอบสนองเร็วขึ้นแต่แกว่งง่าย ค่านี้ไม่มีผลเมื่อ Mirostat Mode เป็น 0',
  dynatemp_range:'ช่วงที่ให้ Temperature เปลี่ยนแบบไดนามิก ค่าที่แนะนำสำหรับระบบนี้: 0.0 (ปิด) ผลเมื่อปรับ: เพิ่มค่าทำให้ความสุ่มแกว่งตามบริบท แต่จากการทดสอบทำให้สำนวนไม่เสถียร',
  dynatemp_exponent:'รูปแบบการกระจายของ Dynamic Temperature ค่าที่แนะนำ: 1.0 ผลเมื่อปรับ: ค่าสูงจะเน้นช่วงอุณหภูมิสุดขั้วมากขึ้น ค่านี้ไม่มีผลเมื่อ Dynamic Temperature Range เป็น 0',
  xtc_probability:'โอกาสใช้ Exclude Top Choices เพื่อเพิ่มความแปลกใหม่ ค่าที่แนะนำสำหรับระบบนี้: 0.0 (ปิด) ผลเมื่อปรับ: เพิ่มค่าจะลดคำยอดนิยม แต่เสี่ยงให้ภาษาแปลกหรือหลุดประเด็น',
  xtc_threshold:'เกณฑ์คำที่ XTC จะนำไปตัด ค่าที่แนะนำ: 0.1 ผลเมื่อปรับ: ค่าสูงตัดคำยอดนิยมมากขึ้น ค่านี้ไม่มีผลเมื่อ XTC Probability เป็น 0',
  dry_multiplier:'ความแรงของการลงโทษลำดับคำที่ซ้ำกัน ค่าที่แนะนำสำหรับระบบนี้: 0.0 (ปิด) ผลเมื่อปรับ: เพิ่มค่าลดวลีซ้ำยาว ๆ แต่จากการทดสอบทำให้สำนวนฝืนและปนภาษา',
  dry_base:'ความชันของโทษ DRY ค่าที่แนะนำ: 1.75 ผลเมื่อปรับ: ค่าสูงเพิ่มโทษลำดับที่ซ้ำยาว ค่านี้ไม่มีผลเมื่อ DRY Multiplier เป็น 0',
  dry_allowed_length:'ความยาวลำดับคำซ้ำที่ยอมให้เกิดก่อน DRY เริ่มทำงาน ค่าที่แนะนำ: 2 ผลเมื่อปรับ: ลดค่าจะกันวลีซ้ำเร็วขึ้น ค่านี้ไม่มีผลเมื่อ DRY Multiplier เป็น 0'
};
function rpSamplingInput([key,label,min,max,step],value,prefix){const help=rpSamplingHelp[key]?`<button class="parameter-help" type="button" aria-label="คำอธิบาย ${label}">?<span class="parameter-tooltip" role="tooltip">${rpSamplingHelp[key]}</span></button>`:'';return `<label class="rp-sampling-field"><span>${label}${help}</span><input class="form-input" id="${prefix}-${key}" type="number" min="${min}" max="${max}" step="${step}" value="${escapeHtml(String(value))}"></label>`;}
function rpSamplingFromBasic(){
  const values={...rp.sampling.effective,extra:{...rp.sampling.effective.extra}};
  for(const key of rpBasicSamplingKeys)values[key]=Number(document.getElementById('rp-basic-'+key).value);
  return values;
}
function rpSyncBasicSampling(values){for(const key of rpBasicSamplingKeys){const field=document.getElementById('rp-basic-'+key);if(field)field.value=values[key];}}
function openAdvancedSampling(){return rpRun(async()=>{
  if(!rp.sampling)rp.sampling=await rpApi('/api/llm/sampling');
  const current=rpSamplingFromBasic();
  const content=rpDialog('Advanced Sampling Parameters');
  const dialog=document.getElementById('rp-dialog');dialog.classList.add('rp-sampling-dialog','rp-card-dialog');
  const intro=document.createElement('p');intro.textContent='Apply ใช้กับการตอบครั้งถัดไป · Save จดจำค่าหลังเริ่มแอปใหม่ · Reset to Default คืนค่าเริ่มต้นและบันทึก';content.append(intro);
  const grid=document.createElement('div');grid.className='rp-sampling-grid';
  grid.innerHTML=rpSamplingSpecs.map(spec=>rpSamplingInput(spec,current[spec[0]],'rp-advanced')).join('');content.append(grid);
  const label=document.createElement('label');label.className='rp-sampling-extra-label';label.textContent='Custom request parameters (JSON)';
  const extra=document.createElement('textarea');extra.id='rp-sampling-extra';extra.className='form-input';extra.rows=5;extra.value=JSON.stringify(current.extra||{},null,2);content.append(label,extra);
  const actions=document.createElement('div');actions.className='rp-card-actions';
  function collect(){
    const values={};for(const [key] of rpSamplingSpecs){const input=document.getElementById('rp-advanced-'+key);if(!input.value.trim())throw Error(`${key}: กรุณาใส่ค่า`);values[key]=Number(input.value);}
    values.extra=JSON.parse(extra.value||'{}');if(!values.extra||Array.isArray(values.extra)||typeof values.extra!=='object')throw Error('Custom parameters ต้องเป็น JSON object');
    return values;
  }
  const apply=rpCardButton('Apply',()=>rpRun(async()=>{const result=await rpApi('/api/llm/sampling/apply',collect());rp.sampling.effective=result.effective;rpSyncBasicSampling(result.effective);dialog.close();}));
  const save=rpCardButton('Save',()=>rpRun(async()=>{const result=await rpApi('/api/llm/sampling/save',collect());rp.sampling=result;rpSyncBasicSampling(result.effective);dialog.close();}));save.className='btn';
  const reset=rpCardButton('Reset to Default',()=>rpRun(async()=>{const result=await rpApi('/api/llm/sampling/reset',{});rp.sampling=result;rpSyncBasicSampling(result.effective);dialog.close();}));
  actions.append(apply,save,reset);content.append(actions);
});}
const oldSwitchSlimTab=switchSlimTab;
switchSlimTab=function(name){oldSwitchSlimTab(name);if((name==='textgen'||name==='imagegen')&&!rp.config)rpRun(loadFeatureSettings);if(name==='chatsettings'&&!rp.chatSettings)rpRun(loadChatDisplaySettings);if(name==='rules')rpRun(renderRuleEditors);};
saveEditMessage=async function(idx){
  const name=activeCharacter, input=document.getElementById(`msg-edit-input-${idx}`);
  if(!input)return;
  try{const result=await rpApi('/api/chat/edit',{character_name:name,index:idx,content:input.value});if(activeCharacter===name)renderChatHistory(result.history,false);}
  catch(e){typeof showNotice==='function'?showNotice('บันทึกไม่สำเร็จ: '+e.message,'error'):alert('บันทึกไม่สำเร็จ: '+e.message);}
};

// Small always-on execution monitor.  It is driven by the server-side rule
// trace, so it also reports work started by image/profile/TTS controls.
function installRuleProgressMonitor(){
  if(window.__rpProgressMonitor)return;window.__rpProgressMonitor=true;
  let lastFinishedId='',fadeTimer=null;
  const makePanel=()=>{const panel=document.createElement('div');panel.id='rp-rule-progress';panel.className='rp-inline-progress';panel.setAttribute('role','status');panel.innerHTML='<div class="rp-rule-progress-top"><span class="rp-rule-progress-label">⏱ 0.0s</span><button type="button" data-rp-cancel title="ยกเลิก" aria-label="ยกเลิก" disabled>■</button></div><div class="rp-rule-progress-track"><i></i></div><small aria-hidden="true"></small>';return panel;};
  const loadingHost=()=>document.querySelector('.rp-generating-row .msg-bubble-wrap')||document.querySelector('.msg-row.bot:last-of-type .msg-bubble-wrap')||document.querySelector('.msg-row.bot .msg-bubble-wrap:last-child');
  const place=(active)=>{let panel=document.getElementById('rp-rule-progress');if(!panel)panel=makePanel();const host=loadingHost();if(host&&panel.parentElement!==host)host.append(panel);return panel;};
  window.showRpGeneratingBubble=()=>{
    const container=document.getElementById('chat-history');if(!container||document.querySelector('.rp-generating-row'))return;
    const row=document.createElement('div');row.className='msg-row bot rp-generating-row';
    const avatar=activeCharacter?`/api/characters/${encodeURIComponent(activeCharacter)}/avatar`:'';
    row.innerHTML=`<img class="msg-avatar-icon" src="${avatar}" alt=""><div class="msg-bubble-wrap"><div class="msg-bubble rp-generating-bubble">… กำลังพิมพ์</div></div>`;
    container.append(row);container.scrollTop=container.scrollHeight;
  };
  const removeLoading=()=>document.querySelector('.rp-generating-row')?.remove();
  const fadeFinishedPanel=(panel)=>{if(!panel)return;clearTimeout(fadeTimer);fadeTimer=setTimeout(()=>{panel.classList.add('rp-progress-fade');setTimeout(()=>panel.remove(),500);},3200);};
  const refresh=async()=>{
    if(!token)return;
    try{
      const res=await fetch('/api/activity',{headers:{Authorization:`Bearer ${token}`},cache:'no-store'});if(!res.ok)return;
      const data=await res.json(),activeRun=data.active?.[0];
      if(!activeRun){removeLoading();clearTimeout(fadeTimer);document.getElementById('rp-rule-progress')?.remove();return;}
      const run=activeRun;
      const terminalText=`${run.status||''} ${run.stage||''} ${run.operation||''}`.toLowerCase();
      const isActive=!/\b(complete|completed|success|succeeded|done|error|failed|cancelled|canceled)\b/.test(terminalText);
      if(!isActive){removeLoading();clearTimeout(fadeTimer);document.getElementById('rp-rule-progress')?.remove();return;}
      const panel=place(true);if(!panel)return;
      const elapsed=((run.duration_ms||0)/1000).toFixed(1);
      const detail=[`${run.operation}: ${run.stage}`,...(run.rules||[]).map(rule=>`Rule: ${rule}`),run.error?`Error: ${run.error}`:''].filter(Boolean).join(' · ');
      panel.title=detail;
      panel.querySelector('.rp-rule-progress-track').title=detail;
      panel.querySelector('.rp-rule-progress-label').textContent=`⏱ ${elapsed}s`;
      panel.querySelector('.rp-rule-progress-track i').style.width=`${run.progress||0}%`;
      panel.querySelector('small').textContent=detail;
      panel.classList.toggle('rp-rule-progress-error',run.status==='error');
      const cancel=panel.querySelector('[data-rp-cancel]');
      const stopping=Boolean(run.cancel_requested);
      cancel.disabled=!isActive||stopping;cancel.textContent=stopping?'…':'■';cancel.title=stopping?'กำลังหยุด':'หยุดการทำงาน';
      cancel.onclick=()=>{if(!isActive||stopping)return;cancel.disabled=true;cancel.textContent='…';cancel.title='กำลังหยุด';if(run.operation==='tts')window.dispatchEvent(new Event('rp-stop-voice'));rpRun(()=>rpApi(`/api/activity/${encodeURIComponent(activeRun.id)}/cancel`,{}));};
      clearTimeout(fadeTimer);panel.classList.remove('rp-progress-fade');
    }catch(_e){}
  };
  setInterval(refresh,750);refresh();
}
async function openRuleInspector(){
  const data=await rpApi('/api/rules');const content=rpDialog('Rule Inspector');
  const settings=data.settings||{};const rules=Object.entries(data.rules||{});
  content.innerHTML=`<p>สถานะการทำงานและ prompt ล่าสุดจะแสดงเฉพาะบัญชีนี้</p><div class="rp-rule-grid">${rules.map(([id,r])=>`<section><strong>${escapeHtml(id)}</strong><small>${escapeHtml(r.stage||'')}</small><p>${escapeHtml(r.description||'')}</p></section>`).join('')}</div><h3>Rule settings</h3>`;
  const form=document.createElement('div');
  form.innerHTML=`<label><input id="rp-rule-proactive" type="checkbox" checked disabled> Proactive state updates (always active)</label><label><input id="rp-rule-loop" type="checkbox" ${settings.loop_guard!==false?'checked':''}> Loop and repetition guard</label><label><input id="rp-rule-prohibitions" type="checkbox" ${settings.prohibitions!==false?'checked':''}> Output prohibitions</label><label><input id="rp-rule-vocalization" type="checkbox" ${settings.expressive_vocalization!==false?'checked':''}> Expressive vocal reactions</label><label><input id="rp-rule-image" type="checkbox" ${settings.image_trigger?'checked':''}> Image trigger</label><label><input id="rp-rule-wardrobe" type="checkbox" ${settings.auto_wardrobe?'checked':''}> Auto wardrobe (canonical state block only)</label><label><input id="rp-rule-trace" type="checkbox" ${settings.trace_prompts?'checked':''}> Retain prompt traces</label><label>NSFW policy <select id="rp-rule-nsfw" class="form-input"><option value="local">Local model/workflow</option><option value="fade_to_black">Fade to black</option><option value="block">Block explicit content</option></select></label>`;
  form.querySelector('#rp-rule-nsfw').value=settings.nsfw_mode||'local';
  const save=rpCardButton('Save rule settings',()=>rpRun(async()=>{await rpApi('/api/configuration',{rules:{proactive_state:form.querySelector('#rp-rule-proactive').checked,loop_guard:form.querySelector('#rp-rule-loop').checked,prohibitions:form.querySelector('#rp-rule-prohibitions').checked,expressive_vocalization:form.querySelector('#rp-rule-vocalization').checked,image_trigger:form.querySelector('#rp-rule-image').checked,auto_wardrobe:form.querySelector('#rp-rule-wardrobe').checked,trace_prompts:form.querySelector('#rp-rule-trace').checked,nsfw_mode:form.querySelector('#rp-rule-nsfw').value}});document.getElementById('rp-dialog').close();}));form.append(save);content.append(form);
  const runs=[...(data.activity?.active||[]),...(data.activity?.recent||[])];if(runs.length){const trace=document.createElement('details');trace.innerHTML='<summary>Recent execution trace</summary>';runs.forEach(run=>{const pre=document.createElement('pre');pre.textContent=JSON.stringify(run,null,2);trace.append(pre);});content.append(trace);}
}
async function renderRuleEditors(){
  const target=document.getElementById('rp-rule-editor-list');if(!target||!token)return;
  try{
    const [ruleData,configuration]=await Promise.all([rpApi('/api/rules'),rpApi('/api/configuration')]);
    const overrides=configuration.rule_overrides||{};
    target.replaceChildren(...Object.entries(ruleData.rules||{}).map(([id,rule])=>{
      const row=document.createElement('details');row.className='rp-rule-editor-row';
      const summary=document.createElement('summary');summary.textContent=id;row.append(summary);
      const text=document.createElement('p');text.textContent=rule.description||'';row.append(text);
      const stage=document.createElement('small');stage.textContent=`Stage: ${rule.stage||'—'}${overrides[id]?' · Custom instruction active':''}`;row.append(stage);
      const edit=document.createElement('button');edit.type='button';edit.className='btn btn-secondary';edit.textContent=overrides[id]?'Edit instruction':'Customize';edit.onclick=()=>openRuleOverride(id,rule.description||'',overrides[id]||'');row.append(edit);
      return row;
    }));
  }catch(error){target.textContent='โหลด Rule instructions ไม่สำเร็จ: '+error.message;}
}
function openRuleOverride(id,description,value){return rpRun(async()=>{
  const content=rpDialog(`Customize rule: ${id}`),dialog=document.getElementById('rp-dialog');
  const help=document.createElement('p');help.textContent=description;content.append(help);
  const note=document.createElement('small');note.textContent='คำสั่งเสริมนี้ใช้กับข้อความตอบผู้ใช้ของ AI เท่านั้น ไม่เปลี่ยน Character Card, Memory, State หรือ ComfyUI workflow.';content.append(note);
  const input=document.createElement('textarea');input.className='form-input';input.rows=8;input.maxLength=2000;input.placeholder='เพิ่มข้อกำหนดเฉพาะกฎนี้ (เว้นว่างเพื่อล้าง)';input.value=value;content.append(input);
  const actions=document.createElement('div');actions.className='rp-card-actions';
  const clear=rpCardButton('Clear',()=>{input.value='';});
  const save=rpCardButton('Save',()=>rpRun(async()=>{await rpApi('/api/configuration',{rule_overrides:{[id]:input.value.trim()}});dialog.close();await renderRuleEditors();}));save.className='btn';
  actions.append(clear,save);content.append(actions);input.focus();
});}
document.addEventListener('DOMContentLoaded',()=>setTimeout(installRuleProgressMonitor,500));
const ruleProgressStyle=document.createElement('style');ruleProgressStyle.textContent='#rp-rule-progress{position:fixed;right:18px;bottom:18px;z-index:9999;width:min(360px,calc(100vw - 36px));padding:11px 12px;border:1px solid #46506b;border-radius:12px;background:#171b27eF;color:#e9edf8;box-shadow:0 12px 34px #0008;font:12px system-ui}.rp-rule-progress-top{display:flex;justify-content:space-between;gap:12px;font-weight:650}.rp-rule-progress-top button{border:0;background:transparent;color:#cbd5e1;cursor:pointer}.rp-rule-progress-top button:disabled{opacity:.35;cursor:not-allowed}.rp-rule-progress-track{height:6px;overflow:hidden;margin:9px 0 6px;border-radius:6px;background:#30384b;position:relative}.rp-rule-progress-track i{display:block;height:100%;width:0;min-width:12%;background:linear-gradient(90deg,#7c5cff,#42d3aa,#38bdf8);background-size:200% 100%;animation:rpProgressShimmer 1.6s linear infinite;transition:width .25s ease}.rp-rule-progress-error .rp-rule-progress-track i{background:#ef5c78;animation:none}#rp-rule-progress small{display:none}@keyframes rpProgressShimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}.rp-rule-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:8px}.rp-rule-grid section{border:1px solid #3d4357;border-radius:9px;padding:9px}.rp-rule-grid small{display:block;color:#aab4ca}.rp-rule-grid p{margin:6px 0 0;font-size:12px}.rp-rule-grid+ h3{margin-top:18px}#rp-dialog-content>div>label{display:block;margin:10px 0}';document.head.append(ruleProgressStyle);
const rpInlineUiStyle=document.createElement('style');rpInlineUiStyle.textContent='#rp-rule-progress.rp-inline-progress{position:static;right:auto;bottom:auto;z-index:auto;width:auto;margin:7px 0 0;padding:8px 10px;border-color:#3b4664;background:#151b2ae8;box-shadow:none;transition:opacity .45s ease,transform .45s ease}.rp-inline-progress.rp-progress-fade{opacity:0;transform:translateY(-5px);pointer-events:none}.rp-generating-bubble{color:#aab8d2;font-style:italic;display:flex;align-items:center;gap:6px}.rp-generating-bubble::after{content:"";display:inline-block;width:12px;height:12px;border:2px solid rgba(167,139,250,.3);border-top-color:#a78bfa;border-radius:50%;animation:rpSpin 0.7s linear infinite}@keyframes rpSpin{to{transform:rotate(360deg)}}.rp-rule-editor-list{display:grid;gap:6px}.rp-rule-editor-row{border:1px solid #394158;border-radius:8px;padding:8px 10px;background:#1d2230}.rp-rule-editor-row summary{cursor:pointer;font-weight:700;color:#e4e7f2}.rp-rule-editor-row p{margin:8px 0 5px;font-size:12px;line-height:1.45;color:#bec8db}.rp-rule-editor-row small{display:block;color:#9faac0;margin-bottom:8px}.rp-rule-editor-row .btn{padding:5px 8px;font-size:11px}';document.head.append(rpInlineUiStyle);
saveRightPaneAll=async function(){
  const name=activeCharacter;if(!name)return;
  const base=`/api/characters/${encodeURIComponent(name)}`;
  await rpApi(base+'/state',{character_name:name,status:document.getElementById('pane-input-status').value,scenario:document.getElementById('pane-input-situation').value,memory:document.getElementById('pane-input-memory').value,appearance:document.getElementById('pane-input-appearance').value});
  await rpApi(base+'/outfits',{outfits:currentWardrobe});
};
async function loadFeatureSettings(){
  rp.config=await rpApi('/api/configuration'); const l=rp.config.llm||{},c=rp.config.comfy||{};
  rp.sampling=await rpApi('/api/llm/sampling');
  await Promise.all([loadEngineModelsDropdown(l.model||''),loadVisionModelsDropdown(l.mmproj||'')]);
  const panel=document.getElementById('rp-llm');
  panel.innerHTML=`<label><input type="checkbox" id="rp-auto_load" ${l.auto_load?'checked':''}> Auto load model</label><h3>Basic Sampling Parameters</h3><div class="rp-sampling-grid">${rpSamplingSpecs.filter(spec=>rpBasicSamplingKeys.includes(spec[0])).map(spec=>rpSamplingInput(spec,rp.sampling.effective[spec[0]],'rp-basic')).join('')}</div><button class="btn btn-secondary" onclick="openAdvancedSampling()">Advanced Sampling Parameters</button><div class="rp-sampling-grid">${['context','gpu_layers','threads','batch_size'].map((k,i)=>rpField(k,k,l[k]??[8192,99,8,512][i],'number')).join('')}${rpKvCacheField('cache_type_k','KV Cache K',l.cache_type_k)}${rpKvCacheField('cache_type_v','KV Cache V',l.cache_type_v)}</div><button class="btn" onclick="rpRun(saveLlmConfig)">Save configuration</button>`;
  const container=document.getElementById('rp-comfy');
  container.innerHTML=`<div class="rp-preset-bar" style="margin-bottom:12px;padding:10px;background:rgba(255,255,255,0.04);border-radius:8px;border:1px solid #3b4252">
    <label style="display:flex;align-items:center;gap:8px;font-weight:600">⚡ Preset
      <select id="rp-workflow-preset" class="form-input" style="flex:1" onchange="applyWorkflowPreset(this.value)">
        <option value="">-- เลือก Preset --</option>
      </select>
    </label>
    <div style="display:flex;gap:6px;margin-top:8px">
      <button class="btn btn-secondary" style="flex:1;font-size:11px" onclick="rpRun(saveCurrentAsPreset)">💾 บันทึกเป็น Preset</button>
      <button class="btn btn-secondary" style="font-size:11px;color:#fca5a5" onclick="rpRun(deleteCurrentPreset)">🗑️ ลบ Preset</button>
    </div>
  </div>
  <label class="rp-workflow-toggle"><input type="checkbox" id="rp-workflow-enabled" ${c.enabled!==false?'checked':''} onchange="updateCustomWorkflowToggle()"> <strong>Custom Workflow</strong> <span id="rp-workflow-enabled-state"></span></label><label>Workflow <select id="rp-workflow" class="form-input"></select></label><button class="btn btn-secondary" data-custom-workflow onclick="document.getElementById('rp-workflow-file').click()">Import API workflow</button><input id="rp-workflow-file" type="file" accept=".json" hidden onchange="rpRun(()=>importWorkflow(this.files[0]))"><button class="btn btn-secondary" data-custom-workflow onclick="rpRun(editWorkflow)">Edit workflow</button><button class="btn btn-secondary" onclick="rpRun(refreshComfyOptions)">Refresh options</button>`;
  for(const k of ['checkpoint','vae','clip','sampler','scheduler']) container.innerHTML+=`<label>${k}<select class="form-input" id="rp-${k}"><option>${escapeHtml(c[k]||'')}</option></select></label>`;
  for(const [k,d] of Object.entries({width:576,height:1024,steps:25,cfg:7,seed:-1,denoise:1,clip_skip:1,timeout:300})) container.innerHTML+=rpField(k,k,c[k]??d,'number',['cfg','denoise'].includes(k)?'.01':'1');
  for(const k of ['negative_prompt','prompt_suffix','emotion']) container.innerHTML+=`<label>${k}<textarea class="form-input" id="rp-${k}">${escapeHtml(c[k]||'')}</textarea></label>`;
  container.innerHTML+='<p>ข้อมูลส่งสร้างภาพ (scene จาก Prompt มาก่อน)</p>'+['appearance','wardrobe','situation','memory','emotion'].map(k=>`<label style="display:block"><input type="checkbox" data-rp-source="${k}" ${(c.sources||['appearance','wardrobe','emotion']).includes(k)?'checked':''}>${k}</label>`).join('');
  container.innerHTML+=`<details><summary>Node mappings / custom placeholders</summary><p>Mappings เช่น {"prompt":["6.text"],"seed":["3.seed"]}; placeholders ใช้ %name% ใน workflow</p><textarea id="rp-mappings" class="form-input">${escapeHtml(JSON.stringify(c.mappings||{},null,2))}</textarea><textarea id="rp-placeholders" class="form-input">${escapeHtml(JSON.stringify(c.placeholders||{},null,2))}</textarea><label>Emotion prompt overrides (JSON)</label><textarea id="rp-emotion-prompts" class="form-input">${escapeHtml(JSON.stringify(c.emotion_prompts||{},null,2))}</textarea></details><button class="btn" onclick="rpRun(saveComfyConfig)">Save Comfy configuration</button>`;
  document.getElementById('rail-comfy-addr').value=c.address||'http://127.0.0.1:8188';
  await Promise.all([refreshWorkflowList(c.workflow), refreshPresetList()]);
  updateCustomWorkflowToggle();
}
async function saveLlmConfig(){
  const llm={model:document.getElementById('rail-engine-model').value,mmproj:document.getElementById('rail-engine-vision').value,auto_load:document.getElementById('rp-auto_load').checked};
  for(const k of ['context','gpu_layers','threads','batch_size']) llm[k]=Number(document.getElementById('rp-'+k).value);
  for(const k of ['cache_type_k','cache_type_v']) llm[k]=document.getElementById('rp-'+k).value;
  const result=await rpApi('/api/llm/sampling/save',rpSamplingFromBasic());
  await rpApi('/api/configuration',{llm});rp.sampling=result;rp.config.llm={...rp.config.llm,...llm,...result.saved};if(typeof showNotice==='function')showNotice('บันทึกการตั้งค่า LLM แล้ว');
}
async function saveComfyConfig(){
  const comfy={enabled:document.getElementById('rp-workflow-enabled').checked,address:document.getElementById('rail-comfy-addr').value,workflow:document.getElementById('rp-workflow').value};
  for(const k of ['checkpoint','vae','clip','sampler','scheduler','negative_prompt','prompt_suffix','emotion']) comfy[k]=document.getElementById('rp-'+k).value;
  for(const k of ['width','height','steps','cfg','seed','denoise','clip_skip','timeout']) comfy[k]=Number(document.getElementById('rp-'+k).value);
  for(const k of ['mappings','placeholders']){
    try{comfy[k]=JSON.parse(document.getElementById('rp-'+k).value||'{}');}
    catch(e){throw Error('รูปแบบ JSON ไม่ถูกต้องในช่อง '+k+': '+e.message);}
  }
  try{comfy.emotion_prompts=JSON.parse(document.getElementById('rp-emotion-prompts').value||'{}');}
  catch(e){throw Error('รูปแบบ JSON ไม่ถูกต้องในช่อง Emotion prompts: '+e.message);}
  comfy.sources=[...document.querySelectorAll('[data-rp-source]:checked')].map(el=>el.dataset.rpSource);
  await rpApi('/api/configuration',{comfy});rp.config.comfy=comfy;if(typeof showNotice==='function')showNotice('บันทึกการตั้งค่า ComfyUI แล้ว');
}
function updateCustomWorkflowToggle(){const enabled=document.getElementById('rp-workflow-enabled')?.checked!==false,state=document.getElementById('rp-workflow-enabled-state');if(state){state.textContent=enabled?'ON · selected workflow':'OFF · built-in default workflow';state.style.color=enabled?'#34d399':'#38bdf8';}document.querySelectorAll('#rp-comfy [data-custom-workflow],#rp-comfy #rp-workflow').forEach(el=>el.disabled=!enabled);}
async function refreshWorkflowList(selected){const list=await rpApi('/api/comfy/workflows');const sel=document.getElementById('rp-workflow');sel.replaceChildren(...list.map(name=>new Option(name,name)));if(selected)sel.value=selected;}
async function importWorkflow(file){if(!file)return;await rpApi('/api/comfy/workflows/'+encodeURIComponent(file.name),JSON.parse(await file.text()));await refreshWorkflowList(file.name);}
async function refreshComfyOptions(){
  await rpApi('/api/configuration',{comfy:{address:document.getElementById('rail-comfy-addr').value}});
  const opts=await rpApi('/api/comfy/options');for(const [key,list] of Object.entries(opts)){const sel=document.getElementById('rp-'+key),v=sel.value;sel.replaceChildren(...[...new Set([v,...list])].map(x=>new Option(x,x)));sel.value=v;}
}
let rpWorkflowPresetsCache = {};
async function refreshPresetList(selected){
  try {
    const presets = await rpApi('/api/comfy/presets');
    rpWorkflowPresetsCache = presets || {};
    const sel = document.getElementById('rp-workflow-preset');
    if(!sel) return;
    sel.innerHTML = '<option value="">-- เลือก Preset --</option>';
    for(const name of Object.keys(rpWorkflowPresetsCache)){
      sel.append(new Option(name, name));
    }
    if(selected) sel.value = selected;
  } catch(e) {
    console.error('Failed to load workflow presets:', e);
  }
}
function applyWorkflowPreset(name){
  if(!name || !rpWorkflowPresetsCache[name]) return;
  const p = rpWorkflowPresetsCache[name];
  if(p.workflow){
    const wfSel = document.getElementById('rp-workflow');
    if(wfSel){ wfSel.value = p.workflow; }
  }
  for(const k of ['checkpoint','vae','clip','sampler','scheduler']){
    const el = document.getElementById('rp-'+k);
    if(el && p[k] !== undefined){
      if(![...el.options].some(o => o.value === p[k])){
        el.append(new Option(p[k], p[k]));
      }
      el.value = p[k];
    }
  }
  for(const k of ['width','height','steps','cfg','seed','denoise','clip_skip','timeout']){
    const el = document.getElementById('rp-'+k);
    if(el && p[k] !== undefined) el.value = p[k];
  }
  for(const k of ['negative_prompt','prompt_suffix','emotion']){
    const el = document.getElementById('rp-'+k);
    if(el && p[k] !== undefined) el.value = p[k];
  }
  if(p.mappings){
    const el = document.getElementById('rp-mappings');
    if(el) el.value = JSON.stringify(p.mappings, null, 2);
  }
  if(p.placeholders){
    const el = document.getElementById('rp-placeholders');
    if(el) el.value = JSON.stringify(p.placeholders, null, 2);
  }
  if(p.emotion_prompts){
    const el = document.getElementById('rp-emotion-prompts');
    if(el) el.value = JSON.stringify(p.emotion_prompts, null, 2);
  }
  if(p.sources && Array.isArray(p.sources)){
    document.querySelectorAll('[data-rp-source]').forEach(cb => {
      cb.checked = p.sources.includes(cb.dataset.rpSource);
    });
  }
  if(typeof showNotice === 'function') showNotice(`โหลดการตั้งค่าจาก Preset: ${name} แล้ว (กด Save เพื่อบันทึก)`);
}
async function saveCurrentAsPreset(){
  const name = prompt('ตั้งชื่อ Preset:', document.getElementById('rp-workflow-preset')?.value || document.getElementById('rp-workflow')?.value?.replace('.json', '') || 'My Preset');
  if(!name || !name.trim()) return;
  const presetData = {
    workflow: document.getElementById('rp-workflow')?.value || '',
  };
  for(const k of ['checkpoint','vae','clip','sampler','scheduler','negative_prompt','prompt_suffix','emotion']){
    presetData[k] = document.getElementById('rp-'+k)?.value || '';
  }
  for(const k of ['width','height','steps','cfg','seed','denoise','clip_skip','timeout']){
    presetData[k] = Number(document.getElementById('rp-'+k)?.value || 0);
  }
  try {
    presetData.mappings = JSON.parse(document.getElementById('rp-mappings')?.value || '{}');
  } catch(e) { presetData.mappings = {}; }
  try {
    presetData.placeholders = JSON.parse(document.getElementById('rp-placeholders')?.value || '{}');
  } catch(e) { presetData.placeholders = {}; }
  try {
    presetData.emotion_prompts = JSON.parse(document.getElementById('rp-emotion-prompts')?.value || '{}');
  } catch(e) { presetData.emotion_prompts = {}; }
  presetData.sources = [...document.querySelectorAll('[data-rp-source]:checked')].map(el => el.dataset.rpSource);

  await rpApi('/api/comfy/presets/' + encodeURIComponent(name.trim()), presetData);
  await refreshPresetList(name.trim());
  if(typeof showNotice === 'function') showNotice(`บันทึก Preset "${name.trim()}" สำเร็จแล้ว`);
}
async function deleteCurrentPreset(){
  const sel = document.getElementById('rp-workflow-preset');
  const name = sel?.value;
  if(!name) { alert('กรุณาเลือก Preset ที่ต้องการลบก่อน'); return; }
  if(!confirm(`ยืนยันการลบ Preset "${name}" หรือไม่?`)) return;
  await rpApi('/api/comfy/presets/' + encodeURIComponent(name), {}, 'DELETE');
  await refreshPresetList();
  if(typeof showNotice === 'function') showNotice(`ลบ Preset "${name}" แล้ว`);
}
function rpDialog(title){const old=document.getElementById('rp-dialog');if(old)old.remove();const el=document.createElement('dialog');el.id='rp-dialog';el.style.cssText='width:min(760px,92vw);max-height:85vh;background:#181923;color:#eee;border:1px solid #555;border-radius:16px;padding:20px';el.innerHTML=`<button class="btn btn-secondary" aria-label="ปิด" title="ปิด" onclick="this.closest('dialog').close()" style="float:right">✕</button><h2></h2><div id="rp-dialog-content"></div>`;el.querySelector('h2').textContent=title;document.body.append(el);el.showModal();return el.querySelector('#rp-dialog-content');}
let characterProfileUrl=null;
let characterPaneProfileUrl=null;
async function loadCharacterPaneProfileImage(name=activeCharacter){
  const preview=document.getElementById('pane-cover-avatar');if(!preview||!name)return;
  const fallback=`/api/characters/${encodeURIComponent(name)}/avatar?v=${Date.now()}`;
  const response=await fetch(`/api/characters/${encodeURIComponent(name)}/profile-image`,{headers:{Authorization:`Bearer ${token}`},cache:'no-store'});
  if(name!==activeCharacter)return;
  if(response.status===404){if(characterPaneProfileUrl)URL.revokeObjectURL(characterPaneProfileUrl);characterPaneProfileUrl=null;preview.src=fallback;return;}
  if(!response.ok)throw Error(`โหลดรูปตัวละครไม่สำเร็จ (${response.status})`);
  const url=URL.createObjectURL(await response.blob());
  if(characterPaneProfileUrl)URL.revokeObjectURL(characterPaneProfileUrl);
  characterPaneProfileUrl=url;preview.src=url;
}
async function uploadCharacterProfileFromPane(input){return rpRun(async()=>{
  const name=activeCharacter,file=input.files?.[0];if(!name||!file)return;
  const form=new FormData();form.append('file',file);
  const response=await fetch(`/api/characters/${encodeURIComponent(name)}/profile-image`,{method:'POST',headers:{Authorization:`Bearer ${token}`},body:form});
  if(!response.ok){const data=await response.json();throw Error(data.detail||'อัปโหลดรูปตัวละครไม่สำเร็จ');}
  input.value='';if(name===activeCharacter)await loadCharacterPaneProfileImage(name);
});}
async function getCharacterProfileInitialPositive(name){
  try{
    const state=await rpApi(`/api/characters/${encodeURIComponent(name)}/state`);
    const appearance=state?.appearance?String(state.appearance).trim():'';
    const outfits=state?.outfits||{};
    const tags=[];
    let anyClothes=false;
    const clothingKeys=['outer','top','top_inner','bottom','bottom_inner'];
    for(const k of clothingKeys){
      const it=outfits[k];
      if(it&&it.active&&it.prompt&&it.prompt.trim()){anyClothes=true;break;}
    }
    if(!anyClothes){
      const nakedPrompt=outfits.naked?.prompt?outfits.naked.prompt.trim():'naked';
      if(nakedPrompt)tags.push(nakedPrompt);
    }
    for(const [k,v] of Object.entries(outfits)){
      if(k==='naked')continue;
      if(v&&v.active&&v.prompt&&v.prompt.trim()){
        const p=v.prompt.trim();
        if(!tags.includes(p))tags.push(p);
      }
    }
    const wardrobe=tags.join(', ');
    return [appearance,wardrobe].filter(Boolean).join(', ');
  }catch(_){return '';}
}

function characterProfileImagePanel(name){
  const section=document.createElement('section');section.className='rp-character-image-section';
  const heading=document.createElement('h3');heading.textContent='Character Profile Image';section.append(heading);
  const layout=document.createElement('div');layout.className='profile-image-tool-layout';
  const frame=document.createElement('div');frame.className='profile-image-frame';
  const preview=document.createElement('img');preview.className='rp-character-profile-image';preview.alt='Character Profile Image';frame.append(preview);
  const tools=document.createElement('div');tools.className='profile-image-tools';layout.append(frame,tools);section.append(layout);
  const fallback=`/api/characters/${encodeURIComponent(name)}/avatar`;
  async function refresh(){
    const response=await fetch(`/api/characters/${encodeURIComponent(name)}/profile-image`,{headers:{Authorization:`Bearer ${token}`},cache:'no-store'});
    if(response.status===404){preview.src=fallback;return;}
    if(!response.ok)throw Error(`โหลดรูปตัวละครไม่สำเร็จ (${response.status})`);
    const url=URL.createObjectURL(await response.blob());
    if(characterProfileUrl)URL.revokeObjectURL(characterProfileUrl);
    characterProfileUrl=url;preview.src=url;
  }
  rpRun(refresh);
  const picker=document.createElement('input');picker.type='file';picker.accept='image/*';picker.hidden=true;
  picker.onchange=()=>rpRun(async()=>{
    const file=picker.files?.[0];if(!file)return;
    const form=new FormData();form.append('file',file);
    const response=await fetch(`/api/characters/${encodeURIComponent(name)}/profile-image`,{method:'POST',headers:{Authorization:`Bearer ${token}`},body:form});
    if(!response.ok){const data=await response.json();throw Error(data.detail||'เปลี่ยนรูปตัวละครไม่สำเร็จ');}
    picker.value='';await refresh();
  });
  const upload=rpCardButton('⬆',()=>picker.click());upload.title='Upload';upload.classList.add('profile-image-tool-button');
  const generate=rpCardButton('🎨',()=>rpRun(async()=>{
    const defaultPos=await getCharacterProfileInitialPositive(name);
    return openImagePromptDialog('Generate Character Profile Image',async(positive,negative)=>{
      await rpApi(`/api/characters/${encodeURIComponent(name)}/profile-image/generate`,{positive,negative});await refresh();if(name===activeCharacter)await loadCharacterPaneProfileImage(name);
    },defaultPos);
  }));generate.title='Generate';generate.classList.add('profile-image-tool-button');
  const remove=rpCardButton('🗑',async()=>{if(!await confirmImageDelete('Character Profile Image'))return;return rpRun(async()=>{await rpApi(`/api/characters/${encodeURIComponent(name)}/profile-image`,{},'DELETE');await refresh();if(name===activeCharacter)await loadCharacterPaneProfileImage(name);});});remove.title='Delete';remove.classList.add('profile-image-tool-button');
  tools.append(upload,generate,remove,picker);
  return section;
}
async function editWorkflow(){const name=document.getElementById('rp-workflow').value;if(!name)throw Error('เลือก workflow ก่อน');const graph=await rpApi('/api/comfy/workflows/'+encodeURIComponent(name));const el=rpDialog(name);const text=document.createElement('textarea');text.className='form-input';text.style.height='55vh';text.value=JSON.stringify(graph,null,2);el.append(text);const btn=document.createElement('button');btn.className='btn';btn.textContent='Save workflow';btn.onclick=()=>rpRun(async()=>{await rpApi('/api/comfy/workflows/'+encodeURIComponent(name),JSON.parse(text.value));document.getElementById('rp-dialog').close();});el.append(btn);}
const rpCardFields=[
  ['name','Name / ชื่อ'],['description','Description / Story Context'],['personality','Personality / บุคลิก'],
  ['scenario','Scenario / สถานการณ์'],['first_mes','First Message / คำทักทายแรก'],
  ['mes_example','Example Dialogue / ตัวอย่างบทสนทนา'],['creatorcomment','Creator Comment / หมายเหตุ ผู้ออกแบบ'],
  ['creator_notes','Creator Notes'],['system_prompt','System Prompt'],
  ['post_history_instructions','Post-history Instructions'],['alternate_greetings','Alternate Greetings (JSON)'],
  ['creator','Creator'],['character_version','Character Version'],
  ['character_book','Character Book / Lorebook (JSON)'],['extensions','Extensions (JSON)'],
  ['avatar','Avatar / รูปลักษณ์'],['talkativeness','Talkativeness'],['fav','Favorite'],['tags','Tags']
];
function rpCardButton(label,action){const button=document.createElement('button');button.type='button';button.className='btn btn-secondary';button.textContent=label;button.onclick=action;return button;}
function rpCardField(key,label,value,editing){
  const item=document.createElement('div');item.className='rp-card-field';
  item.dataset.field=key;
  const heading=document.createElement('label');heading.textContent=label;item.append(heading);
  let control;
  if(editing){
    if(['alternate_greetings','character_book','extensions'].includes(key)){control=document.createElement('textarea');control.className='form-input';control.rows=10;control.value=value===undefined?'':JSON.stringify(value,null,2);}
    else if(key==='fav'){control=document.createElement('input');control.type='checkbox';control.checked=!!value;}
    else if(key==='talkativeness'){control=document.createElement('input');control.type='number';control.min='0';control.max='1';control.step='.01';control.value=value??.5;control.className='form-input';}
    else if(key==='tags'){control=document.createElement('input');control.type='text';control.value=(value||[]).join(', ');control.className='form-input';}
    else if(key==='name'){control=document.createElement('div');control.textContent=value;}
    else {control=document.createElement(['description','personality','scenario','first_mes','mes_example','creatorcomment','creator_notes','system_prompt','post_history_instructions'].includes(key)?'textarea':'input');control.value=value||'';control.className='form-input';if(control.tagName==='TEXTAREA')control.rows=key==='mes_example'?4:3;}
    control.dataset.cardField=key;
  } else {control=document.createElement('div');control.className='rp-card-value';control.textContent=key==='tags'?(value||[]).join(' · '):key==='fav'?(value?'★ Yes':'No'):(typeof value==='object'?JSON.stringify(value,null,2):String(value??'—'));}
  item.append(control);return item;
}
async function openCardViewer(editing=false){return rpRun(async()=>{
  if(!activeCharacter)return;
  const name=activeCharacter,card=await rpApi(`/api/characters/${encodeURIComponent(name)}/card-document`);
  if(activeCharacter!==name)return;
  rp.card=card;
  const content=rpDialog(editing?'แก้ไขการ์ดตัวละคร':'Character Card');
  document.getElementById('rp-dialog').classList.add('rp-card-dialog');
  const header=document.createElement('div');header.className='rp-card-hero';
  const avatar=document.createElement('img');avatar.alt=name;avatar.className='rp-card-hero-display';
  const avatarFrame=document.createElement('button');avatarFrame.type='button';avatarFrame.className='rp-card-hero-display-frame';avatarFrame.title='Customize Character Display Image';avatarFrame.setAttribute('aria-label',avatarFrame.title);avatarFrame.onclick=()=>openChatBubbleDisplayEditor('character');avatarFrame.append(avatar);syncCharacterDisplayIcon(avatar);
  const text=document.createElement('div');const title=document.createElement('h3');title.textContent=card.data.name;const spec=document.createElement('small');spec.textContent=`Character Card V2 · ${card.spec_version}`;text.append(title,spec);header.append(avatarFrame,text);content.append(header);
  const dialog=document.getElementById('rp-dialog');
  if(!editing){
    const edit=rpCardButton('✎',()=>openCardViewer(true));edit.classList.add('rp-card-edit-button');edit.title='Edit Character Card';edit.setAttribute('aria-label',edit.title);edit.style.cssText='float:right;margin-right:8px';dialog.insertBefore(edit,dialog.querySelector('h2'));
  }
  if(!editing){
  const imageSection=document.createElement('section');imageSection.className='rp-card-image-section';
  const cardImage=document.createElement('img');cardImage.alt='Character Card Image';cardImage.src=`/api/characters/${encodeURIComponent(name)}/avatar?v=${Date.now()}`;
  const tools=document.createElement('div');tools.className='profile-image-tools';
  const picker=document.createElement('input');picker.type='file';picker.accept='image/*';picker.hidden=true;
  const refreshCardImage=()=>{const src=`/api/characters/${encodeURIComponent(name)}/avatar?v=${Date.now()}`;cardImage.src=src;syncCharacterDisplayIcon(avatar);if(activeCharacter===name){document.getElementById('chat-header-avatar').src=src;renderCharacterList();}};
  cardImage.onerror=()=>{cardImage.removeAttribute('src');};
  picker.onchange=()=>rpRun(async()=>{const file=picker.files?.[0];if(!file)return;const body=new FormData();body.append('file',file);const response=await fetch(`/api/characters/${encodeURIComponent(name)}/avatar`,{method:'POST',headers:{Authorization:`Bearer ${token}`},body});if(!response.ok)throw Error('Upload failed');picker.value='';refreshCardImage();});
  const tool=(label,title,action)=>{const b=rpCardButton(label,action);b.classList.add('profile-image-tool-button');b.title=title;b.setAttribute('aria-label',title);return b;};
  const download=async(format)=>{const response=await fetch(`/api/characters/${encodeURIComponent(name)}/${format==='json'?'export-json':'export'}`,{headers:{Authorization:`Bearer ${token}`}});if(!response.ok)throw Error('Export failed');const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download=`${name}.${format}`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  tools.append(tool('↑','Upload Character Card Image',()=>picker.click()));
  const exportLabel=document.createElement('small');exportLabel.textContent='Export';tools.append(exportLabel);
  tools.append(tool('PNG V2','Export PNG V2',()=>rpRun(()=>download('png'))),tool('JSON','Export JSON',()=>rpRun(()=>download('json'))),tool('✕','Delete Character Card Image',()=>rpRun(async()=>{const confirmed=typeof openConfirmDialog==='function'?await openConfirmDialog('ลบรูป Character Card นี้หรือไม่?','ยืนยันการลบรูปการ์ด'):confirm('ลบรูป Character Card?');if(!confirmed)return;await rpApi(`/api/characters/${encodeURIComponent(name)}/avatar`,{},'DELETE');refreshCardImage();})));
  imageSection.append(cardImage,tools,picker);
  const overview=document.createElement('div');overview.className='rp-character-overview';overview.append(imageSection);content.append(overview);
    const analysis=card.analysis||{},side=document.createElement('section');side.className='rp-character-analysis';
    const title=document.createElement('h3');title.textContent='Character Analysis';side.append(title);
    const stats=document.createElement('div');stats.className='rp-character-metrics';
    for(const [label,value] of [['Card text tokens',analysis.total_tokens],['Summary tokens',analysis.summary_tokens]]){const tile=document.createElement('div');const number=document.createElement('strong');number.textContent=Number(value||0).toLocaleString();const caption=document.createElement('span');caption.textContent=label+' · estimated';tile.append(number,caption);stats.append(tile);}side.append(stats);
    const colors=['#a78bfa','#38bdf8','#34d399','#fbbf24','#fb7185','#c084fc','#2dd4bf','#f97316'];
    const chart=document.createElement('div');chart.className='rp-character-token-chart';chart.setAttribute('role','img');chart.setAttribute('aria-label','Estimated Character Card token distribution');
    let cursor=0;const parts=analysis.parts||[];const stops=parts.map((part,i)=>{const start=cursor;cursor+=analysis.total_tokens?part.tokens/analysis.total_tokens*100:0;return `${colors[i%colors.length]} ${start}% ${cursor}%`;});chart.style.background=stops.length?`conic-gradient(${stops.join(',')})`:'#394158';side.append(chart);
    const legend=document.createElement('div');legend.className='rp-character-token-legend';parts.forEach((part,i)=>{const row=document.createElement('div'),dot=document.createElement('i'),label=document.createElement('span'),value=document.createElement('strong');dot.style.background=colors[i%colors.length];label.textContent=part.field.replaceAll('_',' ');value.textContent=`${part.tokens.toLocaleString()} · ${part.percent}%`;row.append(dot,label,value);legend.append(row);});side.append(legend);
    const note=document.createElement('small');note.textContent='Text estimate only; excludes images and duplicate V2 fields. Actual LLM context uses Char_Summary.md and other selected context.';side.append(note);overview.append(side);
    const summary=document.createElement('section');summary.className='rp-character-summary';
    const heading=document.createElement('div');heading.className='rp-character-summary-heading';
    const headingText=document.createElement('h3');headingText.textContent='Auto Summary · Char_Summary.md';
    const editSummary=rpCardButton('📝',()=>{dialog.close();openCharacterSummaryEditor();});editSummary.classList.add('rp-character-summary-edit');editSummary.title='Edit Char_Summary.md';editSummary.setAttribute('aria-label',editSummary.title);
    heading.append(headingText,editSummary);summary.append(heading);
    const body=document.createElement('div');body.className='rp-summary-grid';
    let section=body;
    for(const line of String(analysis.summary_markdown||'No saved character summary available.').split(/\r?\n/)){
      if(!line.trim())continue;
      if(/^##\s/.test(line)){section=document.createElement('article');const h=document.createElement('h4');h.textContent=line.replace(/^##\s+/, '');section.append(h);body.append(section);continue;}
      const element=document.createElement(/^#\s/.test(line)?'h4':/^[-*]\s/.test(line)?'li':'p');
      const safe=escapeHtml(line.replace(/^#\s+|^[-*]\s+/,''));element.innerHTML=safe.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*([^*]+)\*/g,'<em>$1</em>');section.append(element);
    }
    summary.append(body);side.append(summary);
  }
  if(!editing && card.data.alternate_greetings?.length){
    const greetings=document.createElement('section');greetings.className='rp-card-field';
    const label=document.createElement('label');label.textContent='เริ่มแชทใหม่ด้วยคำทักทาย';greetings.append(label);
    const select=document.createElement('select');select.className='form-input';
    for(const [i,greeting] of [card.data.first_mes,...card.data.alternate_greetings].entries()){
      const option=document.createElement('option');option.value=String(i-1);option.textContent=(i===0?'Default: ':'Alternative '+i+': ')+greeting.slice(0,120);select.append(option);
    }
    greetings.append(select,rpCardButton('เริ่มแชทใหม่',()=>rpRun(async()=>{
      await rpApi(`/api/characters/${encodeURIComponent(name)}/chat-sessions`,{greeting_index:Number(select.value),memory_mode:'blank'});
      document.getElementById('rp-dialog').close();await selectCharacter(name);
    })));content.append(greetings);
  }
  const fields=document.createElement('div');fields.className='rp-card-fields';
  for(const [key,label] of rpCardFields)fields.append(rpCardField(key,label,card.data[key],editing));content.append(fields);
  const actions=document.createElement('div');actions.className='rp-card-actions';
  if(editing){
    actions.append(rpCardButton('ยกเลิก',()=>rpRun(()=>openCardViewer())));
    const save=rpCardButton('บันทึกการ์ด',()=>rpRun(async()=>{
      const updates={...card.data};for(const field of fields.querySelectorAll('[data-card-field]')){
        const key=field.dataset.cardField;
        if(key==='name')continue;
        if(['alternate_greetings','character_book','extensions'].includes(key)){
          if(key==='character_book'&&!field.value.trim()){updates[key]=null;continue;}
          try{updates[key]=JSON.parse(field.value);}catch(e){throw Error('Invalid JSON: '+key);}continue;
        }
        updates[key]=key==='fav'?field.checked:key==='tags'?field.value.split(',').map(s=>s.trim()).filter(Boolean):key==='talkativeness'?Number(field.value):field.value;
      }
      save.disabled=true;try{await rpApi(`/api/characters/${encodeURIComponent(name)}/card-document`,{data:updates});await selectCharacter(name);await openCardViewer();}finally{save.disabled=false;}
    }));save.className='btn';actions.append(save);
  }
  if(editing)content.append(actions);
});}

// Format display only. Keep the original text intact for editing, history and prompts.
formatRoleplayText=function(raw){
  if(!raw)return '';
  const text=String(raw).replace(/\{\{char\}\}/g,()=>activeCharacter||'').replace(/\{\{user\}\}/g,()=>currentDisplayName||currentUser||'User').replace(/\r\n/g,'\n').replace(/\\`/g,'`');
  function inline(value,allowAction=true){
    const token=allowAction?/(\(\([\s\S]*?\)\)|\[OOC:[\s\S]*?\]|"[^"\n]*"|“[^”\n]*”|「[^」\n]*」|\*[^*\n]+\*)/gi:/(\(\([\s\S]*?\)\)|\[OOC:[\s\S]*?\]|"[^"\n]*"|“[^”\n]*”|「[^」\n]*」)/gi;
    let out='',position=0;
    for(const match of value.matchAll(token)){
      out+=escapeHtml(value.slice(position,match.index));const item=match[0];
      if(item.startsWith('((')||/^\[OOC:/i.test(item))out+=`<span class="rp-ooc">${escapeHtml(item)}</span>`;
      else if(item.startsWith('*'))out+=`<span class="rp-action">${inline(item.slice(1,-1),false)}</span>`;
      else out+=`<span class="rp-dialogue">${escapeHtml(item)}</span>`;
      position=match.index+item.length;
    }
    return out+escapeHtml(value.slice(position));
  }
  function paragraph(lines){
    if(!lines.length)return '';
    const body=lines.map(line=>{
      const speaker=line.match(/^(\s*💬\s*[^|\n]{1,100})\s*\|\s*/u);
      return speaker?`<span class="rp-speaker">${escapeHtml(speaker[1].trim())} |</span> ${inline(line.slice(speaker[0].length))}`:inline(line);
    }).join('<br>');
    const narration=lines.every(line=>/^\s*\*[^*]+\*\s*$/.test(line));
    return `<p class="rp-roleplay-paragraph${narration?' rp-narration':''}">${body}</p>`;
  }
  function prose(part){
    let out='';for(const block of part.split(/\n\s*\n/g)){
      const pending=[];function flush(){if(pending.length){out+=paragraph(pending);pending.length=0;}}
      for(const line of block.split('\n')){
        if(/^\s*>\s*D\d+\s*\|/.test(line)){flush();out+=`<div class="rp-scene-line">${escapeHtml(line.replace(/^\s*>\s*/,''))}</div>`;}
        else if(line.trim())pending.push(line);
      }
      flush();
    }return out;
  }
  const fence=/```([^\n`]*)\n?([\s\S]*?)(?:```|$)/g;let result='',position=0,stateOpen=false;
  function closeState(){if(stateOpen){result+='</div></details>';stateOpen=false;}}
  for(const match of text.matchAll(fence)){
    const gap=text.slice(position,match.index);
    if(gap.trim())closeState();
    result+=prose(gap);
    const kind=match[1].trim().replace(/^\{\{|\}\}$/g,'').toLowerCase();
    const closed=match[0].endsWith('```');
    const body=escapeHtml((closed?match[2]:match[2].replace(/`{1,2}\s*$/,'')).trim());
    if(['info','status','scenario','current situation','permanent memories','emotion','scenario+info','scenario/info'].includes(kind)){
      if(!stateOpen){result+='<details class="rp-state-container" aria-label="Character state"><summary class="rp-state-heading" style="cursor:pointer;list-style:none;display:flex;align-items:center;justify-content:space-between;user-select:none;"><span>📊 Character State & Needs</span><span class="rp-state-arrow">▼</span></summary><div class="rp-state-sections">';stateOpen=true;}
      const label=({'info':'INFO','status':'STATUS','scenario':'SCENARIO','current situation':'CURRENT SITUATION','permanent memories':'PERMANENT MEMORIES','emotion':'EMOTION'})[kind]||'SCENARIO + INFO';
      result+=`<section class="rp-scenario-card rp-info-card ${kind==='info'?'rp-card-info':'rp-card-scenario'}"><div class="rp-info-header"><strong>${label}</strong><button type="button" class="rp-info-copy" title="คัดลอก" aria-label="คัดลอก">⧉</button></div><pre>${body}</pre></section>`;
    }else {closeState();result+=`<pre class="rp-code-block">${body}</pre>`;}
    position=match.index+match[0].length;
  }
  closeState();
  return result+prose(text.slice(position));
};
document.getElementById('chat-history')?.addEventListener('click',event=>{
  const button=event.target.closest('.rp-info-copy');if(!button)return;
  const content=button.closest('.rp-info-card')?.querySelector('pre')?.textContent;
  if(content!==undefined)navigator.clipboard?.writeText(content).catch(console.error);
});

// Normalize tooltips after the existing poll while preserving its tunnel UI updates.
const oldPoll=pollAllServiceStatus;
pollAllServiceStatus=async function(){await oldPoll();for(const [id,name] of [['engine','LLM'],['comfy','ComfyUI'],['voice','TTS+RVC'],['tunnel','Tunnel']]){const dot=document.getElementById('top-dot-'+id),tip=document.getElementById('tooltip-'+id);if(dot&&tip)tip.textContent=name+':'+(dot.classList.contains('green')||dot.classList.contains('blue')?'พร้อมใช้งาน':dot.classList.contains('yellow')?'กำลังโหลด':dot.classList.contains('red')?'ผิดพลาด':'ออฟไลน์');}};

startBuiltinEngine=()=>rpRun(async()=>{
  if(!rp.config)await loadFeatureSettings();
  const body={model_name:document.getElementById('rail-engine-model').value,mmproj:document.getElementById('rail-engine-vision').value||null};
  for(const k of ['context','gpu_layers','threads','batch_size'])body[k]=Number(document.getElementById('rp-'+k).value);
  for(const k of ['cache_type_k','cache_type_v'])body[k]=document.getElementById('rp-'+k)?.value||'q8_0';
  await rpApi('/api/engine/start',body);await pollAllServiceStatus();
});

const llmPanel=document.getElementById('subview-textgen');
const sampling=llmPanel.querySelectorAll('.setting-group');
// Keep model selectors, start/stop controls, and the Proactive timing controls.
// Only the three legacy sampling groups are replaced by the Feature Settings panel.
[...sampling].slice(3,6).forEach(group=>group.remove());
llmPanel.querySelector('button[onclick="saveSettingsModal()"]')?.remove();
llmPanel.insertAdjacentHTML('beforeend','<div id="rp-llm"></div>');
document.getElementById('subview-imagegen').insertAdjacentHTML('beforeend','<div id="rp-comfy"></div>');
const style=document.createElement('style');style.textContent='.naked-toggle-btn,.naked-toggle-btn.active{background:var(--bg-tertiary,#262638);color:var(--text-primary,#eee);border:1px solid #555}.status-dots-container{cursor:default}#chat-header-avatar,#pane-cover-avatar{cursor:pointer}.rp-ooc{display:inline;color:#b7bed5;font-style:normal;background:#252a39;border-radius:4px;padding:2px 4px}.rp-audit-results{display:grid;gap:7px}.rp-audit-row{display:grid;grid-template-columns:22px minmax(0,1fr);gap:8px;align-items:start;padding:8px;border:1px solid #5a4c35;border-radius:8px;background:#2a261d}.rp-audit-row.pass{border-color:#286a54;background:#172b27}.rp-audit-row>span{display:grid;place-items:center;width:20px;height:20px;border-radius:50%;background:#bc7a22;color:#18120a;font-weight:800}.rp-audit-row.pass>span{background:#37c98b;color:#08271b}.rp-audit-row strong,.rp-audit-row small{display:block}.rp-audit-row small{margin-top:2px;color:var(--text-muted);font-size:10px;line-height:1.35}';document.head.append(style);
const cardStyle=document.createElement('style');
cardStyle.textContent='.rp-card-dialog{width:min(900px,94vw)!important;max-height:min(90vh,1000px)!important;padding:24px!important;background:#191c27!important}.rp-card-dialog #rp-dialog-content{max-width:100%}.rp-card-hero{display:flex;align-items:center;gap:18px;margin:8px 0 22px;padding:16px;border:1px solid #394158;border-radius:16px;background:#23283a}.rp-card-hero img{width:96px;height:96px;flex:none;border-radius:14px;object-fit:cover}.rp-card-hero h3{margin:0 0 6px;font-size:24px}.rp-card-hero small{color:#a8b3ca}.rp-card-fields{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;align-items:stretch}.rp-card-field{grid-column:span 2;min-width:0;padding:14px 16px;border:1px solid #3a4358;border-radius:12px;background:#222735}.rp-card-field[data-field="description"],.rp-card-field[data-field="scenario"],.rp-card-field[data-field="first_mes"],.rp-card-field[data-field="mes_example"],.rp-card-field[data-field="creatorcomment"]{grid-column:1/-1}.rp-card-field[data-field="talkativeness"],.rp-card-field[data-field="fav"]{grid-column:span 1}.rp-card-field label{display:block;margin-bottom:8px;font-size:12px;font-weight:650;letter-spacing:.02em;color:#aab8d2}.rp-card-value{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6;font-size:14px;min-height:20px}.rp-card-field[data-field="description"] .rp-card-value,.rp-card-field[data-field="scenario"] .rp-card-value,.rp-card-field[data-field="first_mes"] .rp-card-value,.rp-card-field[data-field="mes_example"] .rp-card-value{min-height:54px}.rp-card-field .form-input{display:block;width:100%;box-sizing:border-box;margin:0}.rp-card-field textarea{min-height:90px;resize:vertical}.rp-card-field[data-field="mes_example"] textarea{min-height:130px}.rp-card-field input[type="checkbox"]{width:18px;height:18px;accent-color:#8e84fa}.rp-card-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;margin-top:20px;padding-top:16px;border-top:1px solid #384054}@media(max-width:700px){.rp-card-dialog{padding:16px!important}.rp-card-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.rp-card-field[data-field="talkativeness"],.rp-card-field[data-field="fav"]{grid-column:span 1}.rp-card-hero img{width:68px;height:68px}.rp-card-hero h3{font-size:19px}}@media(max-width:450px){.rp-card-fields{grid-template-columns:1fr}.rp-card-field,.rp-card-field[data-field="talkativeness"],.rp-card-field[data-field="fav"]{grid-column:1/-1}.rp-card-actions>*{flex:1 1 auto}}';
cardStyle.textContent += '.rp-card-dialog #rp-dialog-content,.rp-card-dialog .rp-card-fields{width:100%;box-sizing:border-box}.rp-card-dialog .rp-card-fields{grid-template-columns:minmax(0,1fr)}.rp-card-dialog .rp-card-field,.rp-card-dialog .rp-card-field[data-field="talkativeness"],.rp-card-dialog .rp-card-field[data-field="fav"]{grid-column:1/-1;width:100%;box-sizing:border-box}.rp-card-dialog .rp-card-value{width:100%;box-sizing:border-box}';
cardStyle.textContent += '@keyframes rpCardSlideIn{from{transform:translateX(-100%);opacity:.65}to{transform:translateX(0);opacity:1}}.rp-card-dialog{position:fixed!important;inset:0 auto 0 0!important;margin:0!important;width:min(900px,100vw)!important;height:100dvh!important;max-height:100dvh!important;box-sizing:border-box!important;border-radius:0 18px 18px 0!important;overflow-y:auto!important;animation:rpCardSlideIn .28s ease-out both}.rp-card-dialog::backdrop{background:rgba(0,0,0,.56)}.rp-character-image-section{display:grid;gap:10px;padding:16px;margin:0 0 16px;border:1px solid #3a4358;border-radius:12px;background:#222735}.rp-character-image-section h3{margin:0;font-size:16px}.rp-character-profile-image{display:block;width:100%;max-height:340px;object-fit:contain;border-radius:10px;background:#161924}.rp-character-image-section>button{justify-self:start}.rp-character-image-prompts{display:grid;gap:8px}.rp-character-image-prompts label{font-size:12px;color:#aab8d2}.rp-character-image-prompts textarea{width:100%;box-sizing:border-box;resize:vertical}.rp-character-image-prompts button{justify-self:start}.rp-character-image-prompts small{color:#aab8d2}@media(max-width:600px){.rp-card-dialog{width:100vw!important;border-radius:0!important;padding:16px!important}}';
document.head.append(cardStyle);
const profileStyle=document.createElement('style');
profileStyle.textContent='#user-profile-modal .modal-card{width:min(600px,94vw);max-height:90vh;overflow:auto;display:flex;flex-direction:column;gap:14px}#user-profile-modal label{display:block;margin-bottom:6px;color:var(--text-muted);font-size:12px;font-weight:650}.profile-image-section,.profile-avatar-section{padding:14px;border:1px solid rgba(150,160,190,.22);border-radius:12px;background:rgba(255,255,255,.025)}.profile-image-preview{display:none;width:100%;max-height:300px;object-fit:contain;border-radius:10px;background:rgba(0,0,0,.25)}.profile-image-actions{display:flex;gap:8px;margin:10px 0}.profile-image-prompts{display:grid;gap:8px}.profile-image-prompts textarea{width:100%;box-sizing:border-box;resize:vertical}.profile-image-prompts small{color:var(--text-muted)}.profile-avatar-section{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.profile-avatar-section label{width:100%}.profile-avatar-preview{display:none;width:64px;height:64px;object-fit:cover;border-radius:50%}';document.head.append(profileStyle);
const imageToolsStyle=document.createElement('style');
imageToolsStyle.textContent='.profile-image-tool-layout{display:grid;grid-template-columns:minmax(0,1fr) 46px;align-items:start;gap:10px}.profile-image-frame{width:100%;aspect-ratio:2/3;min-width:0;background:rgba(0,0,0,.2);border-radius:10px;overflow:hidden}.profile-image-frame>.profile-image-preview,.profile-image-frame>.rp-character-profile-image{width:100%!important;height:100%!important;max-height:none!important;object-fit:contain!important;margin:0!important;border-radius:0!important;background:transparent!important}.profile-image-tools{display:flex;flex-direction:column;gap:8px}.profile-image-tool-button{width:46px!important;height:46px!important;display:grid!important;place-items:center;padding:0!important;font-size:18px!important}.rp-image-prompt-dialog{display:grid;gap:10px;clear:both}.rp-image-prompt-dialog label{font-size:12px;color:#aab8d2}.rp-image-prompt-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:8px}.rp-delete-button{background:#8f2634!important;color:#fff!important}@media(max-width:420px){.profile-image-tool-layout{grid-template-columns:minmax(0,1fr) 42px;gap:8px}.profile-image-tool-button{width:42px!important;height:42px!important}}';
document.head.append(imageToolsStyle);
const paneImageStyle=document.createElement('style');
paneImageStyle.textContent='#right-tab-profile .character-profile-layout{display:block!important;position:relative;width:100%}#right-tab-profile .character-profile-layout .profile-image-frame{width:100%;aspect-ratio:2/3}#right-tab-profile .character-profile-layout #pane-cover-avatar{width:100%!important;height:100%!important;object-fit:contain}#right-tab-profile .character-profile-layout .profile-image-tools{position:absolute;top:10px;right:10px;z-index:3}#right-tab-profile .profile-image-tools[hidden]{display:none!important}.rp-card-image-section{display:grid;grid-template-columns:minmax(0,332px) 46px;gap:10px;align-items:start;margin-bottom:20px}.rp-card-image-section>img{display:block;width:100%;aspect-ratio:2/3;object-fit:contain}.rp-card-image-section .profile-image-tool-button{font-size:10px!important}.rp-card-image-section .profile-image-tools small{text-align:center;color:#aab8d2}';
document.head.append(paneImageStyle);
const analysisStyle=document.createElement('style');analysisStyle.textContent='.rp-character-overview{display:grid;grid-template-columns:minmax(0,388px) minmax(0,1fr);gap:22px;align-items:start}.rp-character-analysis{min-width:0}.rp-character-analysis h3,.rp-character-summary h3{margin:0 0 14px}.rp-character-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px}.rp-character-metrics>div{padding:12px;background:#242a3b;border-radius:12px}.rp-character-metrics strong{display:block;font-size:24px;color:#c4b5fd}.rp-character-metrics span,.rp-character-analysis small{font-size:11px;color:#aab8d2}.rp-character-token-chart{width:160px;aspect-ratio:1;border-radius:50%;margin:18px auto}.rp-character-token-legend{display:grid;gap:8px;margin-bottom:14px}.rp-character-token-legend>div{display:grid;grid-template-columns:10px 1fr auto;gap:7px;font-size:11px}.rp-character-token-legend i{width:9px;height:9px;border-radius:50%;margin-top:3px}.rp-character-summary{margin:20px 0}.rp-summary-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.rp-summary-grid>article{padding:14px;background:#222735;border:1px solid #3a4358;border-radius:12px;overflow-wrap:anywhere}.rp-summary-grid h4{margin:0 0 8px;color:#c4b5fd}.rp-summary-grid p,.rp-summary-grid li{font-size:13px;line-height:1.65;margin:5px 0;white-space:pre-wrap}.rp-summary-grid>h4,.rp-summary-grid>p{grid-column:1/-1}@media(max-width:650px){.rp-character-overview,.rp-summary-grid{grid-template-columns:1fr}}';document.head.append(analysisStyle);
const compactCardAnalysisStyle=document.createElement('style');
compactCardAnalysisStyle.textContent=`
  .rp-character-overview{align-items:stretch;margin-bottom:16px}
  .rp-character-overview>.rp-card-image-section{margin-bottom:0}
  .rp-character-analysis{height:498px;box-sizing:border-box;overflow:auto;padding:14px 16px;border:1px solid #33394c;border-radius:10px;background:#11141d;color:#dfe5f3;scrollbar-width:thin}
  .rp-character-analysis>h3{margin:0 0 10px;font-size:17px}
  .rp-character-metrics{display:flex;gap:20px;padding:0 0 10px;border-bottom:1px solid #30364a}
  .rp-character-metrics>div{min-width:0;padding:0!important;background:transparent!important;border-radius:0!important}
  .rp-character-metrics strong{font-size:18px;line-height:1.15}
  .rp-character-metrics span{display:block;margin-top:2px;font-size:9px}
  .rp-character-token-chart{width:92px;margin:12px auto}
  .rp-character-token-legend{gap:4px;margin-bottom:10px}
  .rp-character-token-legend>div{grid-template-columns:8px minmax(0,1fr) auto;gap:6px;font-size:10px}
  .rp-character-token-legend i{width:7px;height:7px}
  .rp-character-analysis>small{display:block;font-size:9px;line-height:1.45}
  .rp-character-summary{margin:12px 0 0;padding-top:12px;border-top:1px solid #30364a}
  .rp-character-summary-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 8px}
  .rp-character-summary-heading h3{margin:0;font-size:13px;color:#c4b5fd}
  .rp-character-summary-edit{min-width:28px;min-height:26px;padding:3px 6px;font-size:13px;line-height:1}
  .rp-summary-grid{display:block}
  .rp-summary-grid>article{padding:0;margin:0 0 9px;background:transparent;border:0;border-radius:0}
  .rp-summary-grid h4{margin:0 0 3px;font-size:11px}
  .rp-summary-grid p,.rp-summary-grid li{margin:2px 0;font-size:10px;line-height:1.45}
  @media(max-width:650px){.rp-character-analysis{height:auto;max-height:520px}.rp-character-overview{grid-template-columns:1fr}}
`;
document.head.append(compactCardAnalysisStyle);
const samplingStyle=document.createElement('style');
samplingStyle.textContent='#rp-llm{display:grid;gap:12px}#rp-llm h3{font-size:15px;margin:10px 0 0}.rp-sampling-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:10px 0}.rp-sampling-field{display:grid;gap:5px;min-width:0;font-size:12px;color:#aab8d2}.rp-sampling-field input{width:100%;box-sizing:border-box}.rp-sampling-dialog #rp-dialog-content{width:100%;box-sizing:border-box}.rp-sampling-dialog #rp-dialog-content>p{color:#aab8d2;line-height:1.5}.rp-sampling-dialog .rp-sampling-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.rp-sampling-extra-label{display:block;margin:18px 0 7px;font-size:12px;color:#aab8d2}#rp-sampling-extra{width:100%;box-sizing:border-box;font-family:monospace}.rp-sampling-dialog .rp-card-actions{position:sticky;bottom:-24px;background:#191c27;padding-bottom:8px;z-index:2}@media(max-width:700px){.rp-sampling-dialog .rp-sampling-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:440px){.rp-sampling-dialog .rp-sampling-grid,.rp-sampling-grid{grid-template-columns:1fr}}';document.head.append(samplingStyle);
const roleplayStyle=document.createElement('style');
roleplayStyle.textContent='.msg-bubble-wrap{min-width:0}.msg-bubble{min-width:0}.rp-roleplay-paragraph{margin:0 0 1em;line-height:1.75;white-space:normal}.rp-roleplay-paragraph:last-child{margin-bottom:0}.rp-narration{color:#c4cad5}.rp-scene-line{border-left:2px solid #626b81;padding:4px 0 4px 12px;margin:0 0 16px;color:#e5e9f0;font-size:12px;font-weight:650;overflow-wrap:anywhere}.rp-speaker{color:#eee9ff;font-weight:750}.rp-dialogue{font-weight:650;color:#fff}.rp-action{font-style:italic;color:#bcc5d5}.rp-info-card{display:block!important;padding:0!important;margin:16px 0 4px!important;border:1px solid #404247!important;border-left:0!important;border-radius:9px!important;background:#222326!important;overflow:hidden;font-size:12px;color:#f0f0f0}.rp-info-header{display:flex;align-items:center;justify-content:space-between;padding:7px 10px;background:#3b3d40;color:#fff;font-size:12px}.rp-info-copy{border:0;background:transparent;color:#cdd1d7;cursor:pointer;font-size:16px}.rp-info-card pre,.rp-code-block{margin:0;padding:12px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5;font-family:inherit;font-size:12px;color:#e7e7e7}.rp-code-block{border-radius:8px;background:#222326}.msg-img-box{width:100%;max-width:100%;padding:0;border:0;border-radius:0;overflow:visible;background:transparent;box-shadow:none}.msg-img-box img{display:block;width:auto;max-width:100%;height:auto;max-height:960px;object-fit:contain;margin-top:0;margin-bottom:0;border:0;border-radius:0;box-shadow:none;filter:none}.msg-row.bot .msg-img-box img{margin-left:0;margin-right:auto}.msg-row.user .msg-img-box img{margin-left:auto;margin-right:0}@media(max-width:650px){.msg-row{max-width:95%}.rp-info-card pre{font-size:11px}}';document.head.append(roleplayStyle);
const chatSettingsStyle=document.createElement('style');
const chatMobileStyle=document.createElement('style');
chatMobileStyle.textContent='.rp-chat-mobile-close{display:none}';
document.head.append(chatMobileStyle);
chatSettingsStyle.textContent='#rp-chatsettings-panel{display:grid;gap:12px}.rp-chat-layout{display:grid;gap:6px;font-size:12px;color:#aab8d2}.rp-chat-settings-note{font-size:12px;color:#aab8d2;line-height:1.5;margin:0}.rp-chat-style-row{display:grid;gap:8px;padding:12px;border:1px solid #3a4358;border-radius:10px;background:#222735}.rp-chat-style-row strong{font-size:13px}.rp-chat-control-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.rp-chat-control-grid label{font-size:11px;color:#b9c2d4;display:flex;align-items:center;gap:5px;min-width:0}.rp-chat-control-grid input[type="number"]{width:65px;padding:5px}.rp-chat-control-grid input[type="color"]{width:50px;height:30px;padding:1px;border:0;background:transparent;cursor:pointer}.rp-chat-control-grid input[type="checkbox"]{accent-color:#8e84fa}.rp-chat-sample{display:block;border-top:1px solid #394158;padding-top:8px;overflow-wrap:anywhere}.rp-chat-settings-actions{display:flex;gap:8px;flex-wrap:wrap}#rp-chat-settings-status{color:#9bd8aa}#chat-history .msg-bubble{font-family:var(--rp-chat-font,inherit);font-size:var(--rp-base-size,14px);color:var(--rp-base-color,#e8eaf2);font-weight:var(--rp-base-weight,400);font-style:var(--rp-base-style,normal)}#chat-history .rp-scene-line{color:var(--rp-time-color,#e5e9f0);font-size:var(--rp-time-size,12px);font-weight:var(--rp-time-weight,700);font-style:var(--rp-time-style,normal)}#chat-history .rp-narration{color:var(--rp-narration-color,#c4cad5);font-size:var(--rp-narration-size,14px);font-weight:var(--rp-narration-weight,400);font-style:var(--rp-narration-style,italic)}#chat-history .rp-speaker{color:var(--rp-speaker-color,#eee9ff);font-size:var(--rp-speaker-size,14px);font-weight:var(--rp-speaker-weight,700);font-style:var(--rp-speaker-style,normal)}#chat-history .rp-dialogue{color:var(--rp-speech-color,#fff);font-size:var(--rp-speech-size,14px);font-weight:var(--rp-speech-weight,700);font-style:var(--rp-speech-style,normal)}#chat-history .rp-action{color:var(--rp-action-color,#bcc5d5);font-size:var(--rp-action-size,14px);font-weight:var(--rp-action-weight,400);font-style:var(--rp-action-style,italic)}#chat-history .rp-card-info pre,#chat-history .rp-card-info .rp-info-header strong{color:var(--rp-info-color,#e7e7e7);font-size:var(--rp-info-size,12px);font-weight:var(--rp-info-weight,400);font-style:var(--rp-info-style,normal)}#chat-history .rp-card-scenario pre,#chat-history .rp-card-scenario .rp-info-header strong{color:var(--rp-scenario-color,#e7e7e7);font-size:var(--rp-scenario-size,12px);font-weight:var(--rp-scenario-weight,400);font-style:var(--rp-scenario-style,normal)}#chat-history .rp-ooc{color:var(--rp-ooc-color,#b7bed5);font-size:var(--rp-ooc-size,12px);font-weight:var(--rp-ooc-weight,400);font-style:var(--rp-ooc-style,normal)}#chat-history .rp-code-block{color:var(--rp-code-color,#e7e7e7);font-size:var(--rp-code-size,12px);font-weight:var(--rp-code-weight,400);font-style:var(--rp-code-style,normal)}#chat-history.rp-layout-clean .msg-bubble,#chat-history.rp-layout-story .msg-bubble{background:transparent;border:0;box-shadow:none}#chat-history.rp-layout-story .msg-row{width:100%;max-width:100%}#chat-history.rp-layout-story .msg-bubble-wrap{flex:1}#chat-history.rp-layout-clean .msg-row{max-width:92%}';document.head.append(chatSettingsStyle);
if(token)rpRun(loadFeatureSettings);

// Main UI language switch. Conversation content and user/character data are
// intentionally excluded so language changes never rewrite roleplay text.
const rpUiLanguageMap={
  'ระบบแชทสวมบทบาท AI (Messenger Concept)':'AI roleplay chat (Messenger concept)',
  'หน้ารวมความสามารถของ RealmPlay สำหรับใช้งานและตรวจสอบระบบ':'RealmPlay features and system checks',
  'ปรับกติกากลางที่ใช้กับทุกตัวละคร แล้วกดบันทึก':'Customize global rules used by every character, then save.',
  'กด Run audit เพื่อเริ่มตรวจสอบ':'Press Run audit to start the check.',
  'ตรวจเฉพาะการเชื่อมต่อและการตั้งค่าที่อ่านได้ โดยไม่ส่งข้อความหรือสร้างภาพ/เสียงจริง':'Checks readable connections and settings without sending messages or generating media.',
  'ชื่อแชทใหม่':'New chat title',
  'คัดลอก Permanent Memory':'Copy Permanent Memory',
  'เริ่ม Memory ว่าง':'Start with blank Memory',
  'กำลังโหลดการตั้งค่า...':'Loading settings...',
  'ชื่อผู้ใช้':'Username',
  'ชื่อที่แสดง':'Display name',
  'คำอธิบาย':'Description',
  'ยกเลิก':'Cancel',
  'บันทึก':'Save',
  'สร้างตัวละครใหม่':'Create new character',
  'ค้นหาตัวละคร...':'Search characters...',
  'สลับบัญชี / ออกจากระบบ':'Switch Account / Logout',
  'จัดการระบบ (Admin Panel)':'Admin Panel',
  'รางวัล & RPG (Level / Shop / Gacha)':'Rewards & RPG (Level / Shop / Gacha)',
  'เลือกโมเดล LLM (.gguf):':'Select LLM Model (.gguf):',
  'ความเร็วเสียง (Speed):':'Speech Speed:',
  'สร้างเสียงอัตโนมัติเมื่อได้รับคำตอบ':'Auto-generate voice on reply',
  'เล่นเสียงอัตโนมัติ':'Auto-play voice',
  'เปิดใช้งาน RVC Voice Conversion:':'Enable RVC Voice Conversion:',
  'Pitch Shift (ระดับเสียง semitones):':'Pitch Shift (semitones):',
  'Feature Index File (.index):':'Feature Index File (.index):',
  'Index Rate (สัดส่วน Feature):':'Index Rate:',
  'Protect Voiceless Consonants:':'Protect Voiceless Consonants:',
  'ทดสอบเสียง (Test Audio)':'Test Audio',
  'ล้างแคชไฟล์เสียง':'Clear Audio Cache',
  'บันทึกการตั้งค่าเสียง':'Save Voice Settings',
  'บันทึก Proactive timing':'Save Proactive timing',
  'ส่งข้อความ...':'Type a message...',
  'ส่งข้อความ':'Send message',
  'ข้อความล่าสุด':'Latest message',
  'กลับไปข้อความล่าสุด':'Scroll to bottom',
  'เลือกทั้งหมด':'Select all',
  'ลบแชท':'Delete chat',
  'เปิดแชท':'Open chat',
  'ยืนยันการลบห้องแชท':'Confirm Delete Chat'
};
function applyRealmLanguage(language){
  const lang=language==='th'?'th':'en';
  document.documentElement.lang=lang;
  document.querySelectorAll('body *').forEach(element=>{
    if(element.closest('#chat-history')||element.closest('#chat-input'))return;
    for(const node of element.childNodes){
      if(node.nodeType!==Node.TEXT_NODE||!node.textContent.trim())continue;
      if(!node.__rpOriginalText)node.__rpOriginalText=node.textContent;
      const original=node.__rpOriginalText.trim();
      if(lang==='en'&&rpUiLanguageMap[original])node.textContent=node.textContent.replace(original,rpUiLanguageMap[original]);
      if(lang==='th'){const thai=Object.entries(rpUiLanguageMap).find(([,english])=>english===original)?.[0];if(thai)node.textContent=node.textContent.replace(original,thai);}
    }
  });
  const toggle=document.getElementById('language-toggle');
  if(toggle){toggle.textContent=lang==='en'?'TH':'EN';toggle.title=lang==='en'?'Switch to Thai':'Switch to English';}
  localStorage.setItem('realmplay-language',lang);
}
function toggleRealmLanguage(){applyRealmLanguage((localStorage.getItem('realmplay-language')||'en')==='en'?'th':'en');}
applyRealmLanguage(localStorage.getItem('realmplay-language')||'en');
const rpLanguageStyle=document.createElement('style');
rpLanguageStyle.textContent='.language-toggle{min-width:38px;height:30px;padding:0 9px;border:1px solid rgba(159,140,255,.45);border-radius:8px;background:#24263a;color:#eee9ff;font-size:11px;font-weight:700;cursor:pointer}.language-toggle:hover{background:#3a315b;border-color:#a995ff}@media(max-width:600px){.language-toggle{min-width:34px;height:28px;padding:0 7px}}';
document.head.append(rpLanguageStyle);

// Chat bubble display images are deliberately separate from profile/card images.
// Reapply after every render because history replaces its DOM nodes.
(()=>{
  const applySoon=()=>requestAnimationFrame(()=>applyChatBubbleDisplay());
  const originalRender=window.renderChatHistory;
  if(typeof originalRender==='function'){
    window.renderChatHistory=function(...args){
      const result=originalRender.apply(this,args);
      Promise.resolve(result).finally(applySoon);
      return result;
    };
  }
  const originalSelect=window.selectCharacter;
  if(typeof originalSelect==='function'){
    window.selectCharacter=async function(...args){
      const result=await originalSelect.apply(this,args);
      await loadChatBubbleDisplay();
      applySoon();
      return result;
    };
  }
  const history=document.getElementById('chat-history');
  if(history){
    let queued=false;
    new MutationObserver(()=>{
      if(queued)return;
      queued=true;
      requestAnimationFrame(()=>{queued=false;applyChatBubbleDisplay();});
    }).observe(history,{childList:true,subtree:true});
  }
  const characterList=document.getElementById('char-list-container');
  if(characterList){
    let queuedIcons=false;
    new MutationObserver(()=>{if(queuedIcons)return;queuedIcons=true;requestAnimationFrame(()=>{queuedIcons=false;syncCharacterSelectionIcons();});}).observe(characterList,{childList:true});
  }
  if(activeCharacter)loadChatBubbleDisplay();
  applySoon();
  syncCharacterSelectionIcons();
})();

const bubbleDisplayStyle=document.createElement('style');
bubbleDisplayStyle.textContent=`
  .rp-card-dialog>.rp-card-edit-button,.rp-card-dialog>button[aria-label="ปิด"]{transform:translateY(-10px)}
  .rp-card-hero-display-frame{position:relative;display:block;flex:0 0 96px;width:96px;height:96px;padding:0;overflow:hidden;border:2px solid #7166bd;border-radius:50%;background:#171a27;cursor:pointer}
  .rp-card-hero-display{display:block;width:100%!important;height:100%!important;max-width:none!important;max-height:none!important;border-radius:0!important;object-fit:cover!important;object-position:var(--bubble-x,50%) var(--bubble-y,50%)!important;transform:scale(var(--bubble-scale,1));transform-origin:var(--bubble-x,50%) var(--bubble-y,50%)}
  .chat-header-profile{gap:10px!important}
  .chat-header-profile #chat-header-avatar{display:none!important}
  .chat-character-menu{width:34px;height:34px;display:grid;place-items:center;flex:0 0 auto;border:1px solid rgba(159,140,255,.42);border-radius:9px;background:#24263a;color:#e7e1ff;font-size:18px;line-height:1;cursor:pointer;transition:.16s ease}
  .chat-character-menu:hover{background:#3a315b;border-color:#a995ff;transform:translateY(-1px)}
  #chat-header-name{font-size:23px!important;line-height:1.12!important;letter-spacing:.01em}
  .chat-status-indicator{font-size:13px!important;font-weight:650!important;margin-top:4px}
  .bubble-avatar-frame{position:relative;display:block;flex:0 0 84px;width:84px;height:84px;overflow:hidden;padding:0;border:2px solid #7166bd;border-radius:50%;background:#171a27;cursor:pointer;isolation:isolate;box-shadow:0 0 0 2px rgba(0,0,0,.22)}
  .bubble-avatar-frame.user{border-color:#548cff}
  .bubble-avatar-frame::after{content:'◉';position:absolute;right:1px;bottom:1px;z-index:2;display:grid;place-items:center;width:20px;height:20px;border-radius:50%;background:rgba(18,20,31,.88);border:1px solid rgba(235,235,255,.45);color:#fafaff;font-size:11px;opacity:0;transition:opacity .15s}
  .bubble-avatar-frame:hover::after{opacity:1}
  .bubble-avatar-frame .msg-avatar-icon{display:block!important;width:100%!important;height:100%!important;max-width:none!important;max-height:none!important;margin:0!important;border:0!important;border-radius:0!important;object-fit:cover!important;object-position:var(--bubble-x,50%) var(--bubble-y,50%)!important;transform:scale(var(--bubble-scale,1))!important;transform-origin:var(--bubble-x,50%) var(--bubble-y,50%)!important;transition:transform .12s ease}
  .bubble-editor{display:grid;gap:14px}.bubble-editor-preview{position:relative;width:min(230px,100%);aspect-ratio:1;margin:auto;overflow:hidden;border:1px solid #4a4d68;border-radius:50%;background:#151826}.bubble-editor-preview img{display:block;max-width:none;max-height:none}.bubble-editor-control{display:grid;grid-template-columns:110px minmax(0,1fr) 54px;align-items:center;gap:8px;font-size:13px;color:#c6cbe0}.bubble-editor-control output{text-align:right;color:#eee9ff;font-variant-numeric:tabular-nums}.bubble-editor-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;margin-top:4px}
  @media(max-width:700px){.rp-card-hero-display-frame{flex-basis:68px;width:68px;height:68px}}
  @media(max-width:650px){.chat-character-menu{width:29px;height:29px;font-size:16px}#chat-header-name{font-size:19px!important}.chat-status-indicator{font-size:12px!important}.bubble-avatar-frame{flex-basis:56px!important;width:56px!important;height:56px!important;min-width:56px!important;min-height:56px!important;border-width:2px}.bubble-avatar-frame::after{display:none}}
`;
document.head.append(bubbleDisplayStyle);

const rpV2Style=document.createElement('style');rpV2Style.textContent='.rp-card-field[data-field=character_book],.rp-card-field[data-field=extensions],.rp-card-field[data-field=alternate_greetings],.rp-card-field[data-field=system_prompt],.rp-card-field[data-field=post_history_instructions],.rp-card-field[data-field=creator_notes]{grid-column:1/-1}';document.head.append(rpV2Style);

const rpStateContainerStyle=document.createElement('style');
rpStateContainerStyle.textContent='.rp-state-container{margin:18px 0 4px;border:1px solid #48516a;border-radius:12px;background:#1c202b;overflow:hidden;min-width:0;transition:border-color .2s ease}.rp-state-container[open]{border-color:rgba(139,92,246,0.5)}.rp-state-heading{padding:11px 14px;background:#2a3143;color:#dce4f7;font-size:13px;font-weight:700;cursor:pointer;list-style:none;display:flex;align-items:center;justify-content:space-between;user-select:none;transition:background .15s ease}.rp-state-heading::-webkit-details-marker{display:none}.rp-state-heading:hover{background:#353d53;color:#fff}.rp-state-arrow{font-size:11px;color:#94a3b8;transition:transform .2s ease}.rp-state-container[open] .rp-state-arrow{transform:rotate(180deg)}.rp-state-sections{display:grid;gap:10px;padding:12px;min-width:0}.rp-state-container .rp-info-card{margin:0!important;min-width:0}.rp-state-container pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:320px;overflow:auto;margin:0;padding:12px;line-height:1.6}@media(max-width:650px){.rp-state-sections{padding:8px;gap:8px}.rp-state-heading{padding:10px 12px}}';
document.head.append(rpStateContainerStyle);

