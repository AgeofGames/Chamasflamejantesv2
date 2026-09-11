const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../static/arena_v24.js'),'utf8');

function harness(fetcher=async()=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>({refresh:false,message:'ID inválido'})})) {
  const events={},timers=new Map(),button={textContent:'Verificar',disabled:false},status={textContent:''};
  let submit,close,focused=false,calls=0,navigations=[];
  const form={dataset:{},action:'/arena/equipes/duelo/1/partida',attrs:new Map(),
    querySelector:q=>q==='button'?button:status,addEventListener:(event,fn)=>{submit=fn;},
    setAttribute(k,v){this.attrs.set(k,v);},removeAttribute(k){this.attrs.delete(k);}};
  const trigger={focus(){focused=true;}};
  const floating={open:true,contains:t=>t===trigger,querySelector:q=>q==='summary'?trigger:{addEventListener:(e,fn)=>{close=fn;}}};
  const context={AbortController,FormData:class{},location:{hash:'',assign:url=>navigations.push(url)},
    window:{addEventListener(){}},document:{getElementById:id=>id==='community-challenges'?floating:null,
      querySelectorAll:q=>q==='[data-team-match]'?[form]:[],addEventListener:(e,fn)=>{events[e]=fn;}},
    setTimeout:(fn,ms)=>{timers.set(ms,fn);return ms;},clearTimeout:id=>timers.delete(id),
    fetch:(...args)=>{calls++;return fetcher(...args);}};
  vm.runInNewContext(code,context);
  return {form,button,status,timers,floating,trigger,events,close:()=>close(),focused:()=>focused,
    submit:()=>submit({preventDefault(){}}),calls:()=>calls,navigations};
}

test('community window closes with Escape or the close button and returns focus',()=>{
  const ui=harness();ui.events.keydown({key:'Escape',preventDefault(){}});
  assert.equal(ui.floating.open,false);assert.equal(ui.focused(),true);
  ui.floating.open=true;ui.close();assert.equal(ui.floating.open,false);
});
test('clicking outside closes the community window without moving focus',()=>{
  const ui=harness();ui.events.click({target:ui.trigger});assert.equal(ui.floating.open,true);
  ui.events.click({target:{}});assert.equal(ui.floating.open,false);assert.equal(ui.focused(),false);
});
test('team lookup deadline stops loading and prevents duplicate submissions',async()=>{
  const ui=harness((url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Object.assign(new Error(),{name:'AbortError'})))));
  const pending=ui.submit();await ui.submit();assert.equal(ui.calls(),1);
  assert.equal(ui.button.disabled,true);ui.timers.get(20000)();await pending;
  assert.equal(ui.button.disabled,false);assert.equal(ui.form.dataset.busy,'false');
  assert.equal(ui.form.attrs.has('aria-busy'),false);assert.equal(ui.timers.size,0);
  assert.match(ui.status.textContent,/limite de tempo/);assert.equal(ui.navigations.length,0);
});
test('HTML login responses and network failures release the form',async()=>{
  for(const fetcher of [async()=>({ok:true,headers:{get:()=> 'text/html'}}),async()=>{throw new Error('Sem conexão');}]){
    const ui=harness(fetcher);await ui.submit();assert.equal(ui.button.disabled,false);
    assert.ok(ui.status.textContent);assert.equal(ui.form.dataset.busy,'false');
  }
});
test('one finished query refreshes the duel once and never starts automatic polling',async()=>{
  const ui=harness(async()=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>({refresh:true,message:'Confirmada',url:'/arena/equipes/duelo/1'})}));
  await ui.submit();assert.deepEqual(ui.navigations,['/arena/equipes/duelo/1']);
  assert.equal(ui.timers.size,0);assert.equal(ui.calls(),1);assert.equal(ui.button.disabled,false);
});
