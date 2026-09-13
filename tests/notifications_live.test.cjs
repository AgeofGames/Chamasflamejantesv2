const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../static/social.js'),'utf8');
const settle=()=>new Promise(resolve=>setImmediate(resolve));

function setup(responses){
  let now=100000, calls=0;
  const events={},windowEvents={},intervals=[],timeouts=new Map(),focus=[],toasts=[];
  const badge={textContent:'0',hidden:true};
  const close={focus:()=>focus.push('close')};
  const toggle={querySelector:()=>badge,setAttribute(){},focus:()=>focus.push('toggle')};
  const list={innerHTML:'original',contains:node=>!!node,querySelectorAll:()=>[]};
  const notifications={hidden:true,querySelector:()=>close};
  const document={hidden:false,activeElement:null,body:{style:{overflow:'auto'}},
    getElementById:id=>id==='notification-popover'?notifications:null,
    querySelector:selector=>selector==='[data-notification-toggle]'?toggle:null,
    querySelectorAll:selector=>selector==='[data-notification-list]'?[list]:[],
    addEventListener:(event,fn)=>events[event]=fn};
  const window={addEventListener:(event,fn)=>windowEvents[event]=fn,chamasNotify:message=>toasts.push(message)};
  let pending;
  const fetch=async(url,options)=>{
    calls++;
    const result=responses.shift();
    if(result==='pending'){
      return new Promise((resolve,reject)=>{
        pending=resolve; options.signal.addEventListener('abort',()=>reject(new Error('Aborted')));
      });
    }
    if(result instanceof Error)throw result;
    return {status:result?.status||200,ok:true,json:async()=>result?.data||{html:'active',unread:1,cursor:'one'}};
  };
  vm.runInNewContext(source,{document,window,fetch,AbortController,console,
    Date:{now:()=>now},setInterval:(fn,ms)=>intervals.push({fn,ms}),
    setTimeout:(fn,ms)=>{const id=Symbol();timeouts.set(id,{fn,ms});return id;},clearTimeout:id=>timeouts.delete(id)});
  return {document,events,windowEvents,intervals,timeouts,list,badge,focus,toasts,
    get calls(){return calls;},advance:ms=>now+=ms,resolve:value=>pending(value)};
}

test('notifications arrive at the next 3-second check without reloading the page',async()=>{
  const state=setup([{data:{html:'empty',unread:0,cursor:'a'}},{data:{html:'new challenge',unread:1,cursor:'b'}}]);
  await settle();assert.equal(state.list.innerHTML,'empty');
  assert.equal(state.intervals[0].ms,3000);
  state.advance(3000);await state.intervals[0].fn();
  assert.equal(state.list.innerHTML,'new challenge');assert.equal(state.badge.textContent,'1');
  assert.equal(state.toasts.length,1);
});

test('a completed duel disappears even while its old action holds keyboard focus',async()=>{
  const state=setup([{data:{html:'old challenge',unread:1,cursor:'a'}},{data:{html:'empty',unread:0,cursor:'b'}}]);
  await settle();
  state.document.activeElement={closest:selector=>selector==='[data-notification-id]'?{dataset:{notificationId:'5'}}:null,
    getAttribute:()=>null};
  state.advance(3000);await state.intervals[0].fn();
  assert.equal(state.list.innerHTML,'empty');assert.equal(state.badge.hidden,true);
  assert.deepEqual(state.focus,['close']);
});

test('hidden tabs pause requests and returning to the page refreshes immediately',async()=>{
  const state=setup([{},{}]);await settle();state.document.hidden=true;
  state.advance(3000);await state.intervals[0].fn();assert.equal(state.calls,1);
  state.document.hidden=false;state.events.visibilitychange();await settle();assert.equal(state.calls,2);
});

test('slow requests cannot overlap and timeout permits recovery',async()=>{
  const state=setup(['pending',{}]);state.advance(3000);await state.intervals[0].fn();assert.equal(state.calls,1);
  [...state.timeouts.values()].find(item=>item.ms===8000).fn();await settle();
  state.advance(6000);await state.intervals[0].fn();assert.equal(state.calls,2);
  assert.equal(state.list.innerHTML,'active');
});

test('unchanged content stays intact and expired sessions stop the polling',async()=>{
  const state=setup([{status:204},{status:401},{}]);await settle();assert.equal(state.list.innerHTML,'original');
  state.advance(3000);await state.intervals[0].fn();state.advance(3000);await state.intervals[0].fn();
  assert.equal(state.calls,2);
});

test('reconnecting retries immediately after a temporary network failure',async()=>{
  const state=setup([new Error('Offline'),{}]);await settle();assert.equal(state.list.innerHTML,'original');
  state.windowEvents.online();await settle();assert.equal(state.calls,2);assert.equal(state.list.innerHTML,'active');
});
