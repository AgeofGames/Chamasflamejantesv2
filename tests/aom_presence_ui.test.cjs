const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../static/aom_presence.js'),'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));

function avatar(id) {
  const attrs = new Map([['aria-label','Abrir perfil '+id]]);
  return {dataset:{aomPlayer:String(id)}, getAttribute:key=>attrs.get(key)??null,
    setAttribute:(key,value)=>attrs.set(key,value),removeAttribute:key=>attrs.delete(key)};
}
function matchControls(id) {
  const value={textContent:''},note={textContent:''};
  const wrapper={dataset:{aomMatch:String(id)},hidden:true};
  const button={dataset:{copyMatch:''},textContent:'Copiar ID',disabled:false,
    closest:selector=>selector==='[data-copy-match]'?button:selector==='[data-aom-match]'?wrapper:null};
  wrapper.querySelector=selector=>selector==='[data-copy-match]'?button:selector==='[data-aom-match-value]'?value:selector==='[data-aom-copy-status]'?note:null;
  return Object.assign(wrapper,{button,value,note});
}
function setup(responses, initial=[avatar(1),avatar(1),avatar(2)], matches=[], clipboard={writeText:async()=>{}}) {
  let now=100000,calls=0;
  const events={},windowEvents={},timers=new Map(),intervals=[];
  const nodes=initial,statuses=[{dataset:{aomStatus:'1'},textContent:''}];
  const document={hidden:false,querySelector:()=>nodes[0]||null,
    querySelectorAll:selector=>selector==='[data-aom-player]'?nodes:selector==='[data-aom-status]'?statuses:selector==='[data-aom-match]'?matches:[],
    addEventListener:(event,fn)=>events[event]=fn};
  const window={addEventListener:(event,fn)=>windowEvents[event]=fn};
  const fetch=async(url,options)=>{
    calls++;assert.equal(url,'/api/arena/presenca');assert.equal(options.cache,'no-store');
    const response=responses.shift();
    if (response==='pending') return new Promise((resolve,reject)=>{
      options.signal.addEventListener('abort',()=>reject(new Error('Aborted')));
    });
    if (response instanceof Error) throw response;
    return {ok:true,json:async()=>response||{players:{}}};
  };
  vm.runInNewContext(source,{document,window,fetch,navigator:{clipboard},AbortController,console,Date:{now:()=>now},
    setInterval:(fn,ms)=>intervals.push({fn,ms}),setTimeout:(fn,ms)=>{
      const id=Symbol();timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id)});
  return {nodes,statuses,matches,document,events,windowEvents,intervals,timers,
    get calls(){return calls;},advance:ms=>now+=ms};
}

test('one response lights matching IDs on all avatars and removes departed players without reload',async()=>{
  const state=setup([{players:{1:{state:'lobby',expires_in:90}}},{players:{2:{state:'match',expires_in:90}}}]);
  await settle();assert.equal(state.calls,1);
  assert.equal(state.nodes[0].dataset.aomState,'lobby');
  assert.equal(state.nodes[1].dataset.aomState,'lobby');
  assert.equal(state.nodes[2].dataset.aomState,undefined);
  assert.match(state.statuses[0].textContent,/Em sala/);
  state.advance(20000);await state.intervals[0].fn();await settle();
  assert.equal(state.nodes[0].dataset.aomState,undefined);
  assert.equal(state.nodes[0].getAttribute('aria-label'),'Abrir perfil 1');
  assert.equal(state.nodes[2].dataset.aomState,'match');
  assert.match(state.statuses[0].textContent,/não confirmada/);
});

test('fresh presence applies immediately to an opened profile modal without an extra request',async()=>{
  const state=setup([{players:{1:{state:'match',expires_in:90}}}]);await settle();
  state.nodes.push(avatar(1));state.events['chamas:content']();await settle();
  assert.equal(state.nodes[3].dataset.aomState,'match');assert.equal(state.calls,1);
});

test('network failures and suspended tabs expire the light instead of leaving a false online status',async()=>{
  const state=setup([{players:{1:{state:'match',expires_in:30}}},new Error('Offline')]);
  await settle();state.advance(20000);await state.intervals[0].fn();await settle();
  assert.equal(state.nodes[0].dataset.aomState,'match');
  state.document.hidden=true;state.advance(10000);await state.intervals[0].fn();
  assert.equal(state.nodes[0].dataset.aomState,undefined);assert.equal(state.calls,2);
});

test('slow checks cannot overlap, time out, and recover when connectivity returns',async()=>{
  const state=setup(['pending',{players:{1:{state:'lobby',expires_in:50}}}]);
  state.advance(20000);await state.intervals[0].fn();assert.equal(state.calls,1);
  [...state.timers.values()].find(timer=>timer.ms===16000).fn();await settle();
  state.windowEvents.online();await settle();
  assert.equal(state.calls,2);assert.equal(state.nodes[0].dataset.aomState,'lobby');
});

test('hidden tabs make no calls and returning refreshes without waiting for the polling interval',async()=>{
  const state=setup([{}, {players:{2:{state:'match',expires_in:40}}}]);await settle();
  state.document.hidden=true;state.advance(20000);await state.intervals[0].fn();assert.equal(state.calls,1);
  state.document.hidden=false;state.events.visibilitychange();await settle();
  assert.equal(state.calls,2);assert.equal(state.nodes[2].dataset.aomState,'match');
});

test('pages without avatars wait until a profile is opened',async()=>{
  const state=setup([{players:{1:{state:'match',expires_in:40}}}],[]);await settle();assert.equal(state.calls,0);
  state.nodes.push(avatar(1));state.events['chamas:content']();await settle();
  assert.equal(state.calls,1);assert.equal(state.nodes[0].dataset.aomState,'match');
});

test('invalid states and expired confirmations never turn green and lifetime is capped',async()=>{
  const state=setup([{players:{1:{state:'online',expires_in:90},2:{state:'match',expires_in:0}}},
                    {players:{1:{state:'match',expires_in:99999}}}]);await settle();
  assert.equal(state.nodes[0].dataset.aomState,undefined);assert.equal(state.nodes[2].dataset.aomState,undefined);
  state.advance(20000);await state.intervals[0].fn();await settle();
  assert.equal(state.nodes[0].dataset.aomState,'match');state.document.hidden=true;
  state.advance(90000);await state.intervals[0].fn();assert.equal(state.nodes[0].dataset.aomState,undefined);
});

test('detected match ID is displayed and clipboard receives only the numeric ID',async()=>{
  const controls=matchControls(1),copied=[];
  const state=setup([{players:{1:{state:'match',match_id:'43270001',expires_in:90}}}],undefined,[controls],{writeText:async text=>copied.push(text)});
  await settle();assert.equal(controls.hidden,false);assert.equal(controls.value.textContent,'43270001');
  assert.match(state.nodes[0].getAttribute('title'),/43270001/);
  let stopped=false,prevented=false;
  await state.events.click({target:controls.button,preventDefault(){prevented=true;},stopPropagation(){stopped=true;}});
  assert.deepEqual(copied,['43270001']);assert.equal(stopped,true);assert.equal(prevented,true);
  assert.equal(controls.button.textContent,'ID copiado ✓');
});

test('same online state with a new match ID updates both tooltip and copy controls without reload',async()=>{
  const controls=matchControls(1);
  const state=setup([{players:{1:{state:'match',match_id:'43270001',expires_in:90}}},
    {players:{1:{state:'match',match_id:'43270099',expires_in:90}}}],undefined,[controls]);
  await settle();controls.button.textContent='ID copiado ✓';controls.note.textContent='copiado';
  state.advance(20000);await state.intervals[0].fn();await settle();
  assert.equal(controls.value.textContent,'43270099');assert.equal(controls.button.dataset.copyMatch,'43270099');
  assert.equal(controls.button.textContent,'Copiar ID');assert.equal(controls.note.textContent,'');
  assert.match(state.nodes[0].getAttribute('title'),/43270099/);
});

test('a room, missing ID or invalid provider ID never enables copying a match',async()=>{
  for(const item of [{state:'lobby',match_id:'43270002'},{state:'match'},{state:'match',match_id:'x<script>'},
    {state:'match',match_id:'0'},{state:'match',match_id:43270002}]){
    const controls=matchControls(1),state=setup([{players:{1:{...item,expires_in:90}}}],undefined,[controls]);
    await settle();assert.equal(controls.hidden,true);assert.equal(controls.button.disabled,true);
    assert.equal(controls.button.dataset.copyMatch,'');assert.equal(state.nodes[0].dataset.aomMatchId,'');
  }
});

test('expired evidence clears the ID and a stale copy click cannot copy it',async()=>{
  const controls=matchControls(1),copied=[];
  const state=setup([{players:{1:{state:'match',match_id:'43270001',expires_in:15}}}],undefined,[controls],{writeText:async text=>copied.push(text)});
  await settle();state.document.hidden=true;state.advance(15000);
  await state.events.click({target:controls.button,preventDefault(){},stopPropagation(){}});
  assert.deepEqual(copied,[]);assert.equal(controls.hidden,true);assert.equal(controls.value.textContent,'');
  assert.equal(controls.button.disabled,true);assert.equal(state.nodes[0].dataset.aomMatchId,undefined);
});

test('profile modal gets a valid match ID from shared presence without another fetch',async()=>{
  const state=setup([{players:{1:{state:'match',match_id:'43270001',expires_in:90}}}]);await settle();
  const controls=matchControls(1);state.matches.push(controls);state.nodes.push(avatar(1));
  state.events['chamas:content']();await settle();
  assert.equal(controls.hidden,false);assert.equal(controls.value.textContent,'43270001');assert.equal(state.calls,1);
});

test('clipboard rejection keeps the ID readable and offers manual copying',async()=>{
  const controls=matchControls(1);
  const state=setup([{players:{1:{state:'match',match_id:'43270001',expires_in:90}}}],undefined,[controls],{writeText:async()=>{throw new Error('denied');}});
  await settle();await state.events.click({target:controls.button,preventDefault(){},stopPropagation(){}});
  assert.equal(controls.hidden,false);assert.equal(controls.value.textContent,'43270001');
  assert.match(controls.note.textContent,/copie manualmente/);assert.equal(controls.button.disabled,false);
});
