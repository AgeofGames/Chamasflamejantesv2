const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {File, Blob} = require('node:buffer');
const code = fs.readFileSync(path.join(__dirname,'../static/share_cards.js'),'utf8');

function harness({native=true, fetcher, shareError}={}) {
  const listeners=new Map(), events=new Map(), timers=new Map(), attrs=new Map();
  const feedback={textContent:''};
  const image={complete:false,addEventListener(name,fn){this[name]=fn;}};
  const panel={querySelector(q){return q.includes('feedback')?feedback:image;}};
  const button={disabled:false,dataset:{cardImage:'https://example.test/card.jpg',cardDownload:'/card.jpg?download=1',cardTitle:'Makise venceu Vitor',cardLink:'https://example.test/resultado'},
    closest(){return panel;},addEventListener(name,fn){listeners.set(name,fn);},setAttribute(k,v){attrs.set(k,v);},removeAttribute(k){attrs.delete(k);}};
  let downloads=0, fetches=0;const shares=[];
  const context={console,URL,AbortController,File,Blob,
    window:{location:{href:'https://example.test/duelo/1',origin:'https://example.test'}},
    navigator:native?{canShare:()=>true,share:async data=>{if(shareError)throw shareError;shares.push(data);}}:{},
    document:{querySelectorAll:()=>[button],addEventListener:(name,fn)=>events.set(name,fn),body:{append(){}},createElement:()=>({click(){downloads++;},remove(){}})},
    fetch:(url,options)=>{fetches++;return fetcher?fetcher(url,options):Promise.resolve({ok:true,headers:{get:()=> 'image/jpeg'},blob:async()=>new Blob(['jpeg-test'],{type:'image/jpeg'})});},
    setTimeout:(fn,ms)=>{timers.set(ms,fn);return ms;},clearTimeout:id=>timers.delete(id)};
  vm.runInNewContext(code,context);
  return {button,feedback,attrs,timers,shares,events,downloads:()=>downloads,fetches:()=>fetches,
    click:()=>listeners.get('click')(),warm:()=>listeners.get('focus')(),panel};
}

test('prepared image is shared only after a user click, with both players and the link',async()=>{
  const ui=harness();ui.warm();await new Promise(resolve=>setImmediate(resolve));
  assert.equal(ui.shares.length,0);
  await ui.click();
  assert.equal(ui.shares.length,1);
  assert.equal(ui.shares[0].files[0].type,'image/jpeg');
  assert.match(ui.shares[0].text,/Makise venceu Vitor.*https:\/\/example.test\/resultado/);
  assert.equal(ui.button.disabled,false);
});

test('unsupported devices receive a download instead of a broken share action',async()=>{
  const ui=harness({native:false});await ui.click();
  assert.equal(ui.downloads(),1);assert.equal(ui.fetches(),0);
  assert.match(ui.feedback.textContent,/Anexe o card/);
});

test('slow image preparation has a deadline and allows retry without endless loading',async()=>{
  const ui=harness({fetcher:(url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(new Error('timeout'))))});
  const pending=ui.click();await ui.click();
  assert.equal(ui.fetches(),1);assert.equal(ui.button.disabled,true);
  ui.timers.get(10000)();await pending;
  assert.equal(ui.button.disabled,false);assert.equal(ui.attrs.has('aria-busy'),false);
  assert.equal(ui.timers.size,0);assert.match(ui.feedback.textContent,/Tente novamente/);
});

test('canceling the native dialog releases the button and does not claim success',async()=>{
  const ui=harness({shareError:Object.assign(new Error('cancel'),{name:'AbortError'})});
  ui.warm();await new Promise(resolve=>setImmediate(resolve));await ui.click();
  assert.equal(ui.button.disabled,false);assert.equal(ui.shares.length,0);assert.equal(ui.feedback.textContent,'');
});

test('an unprepared image is loaded first and waits for a fresh user gesture',async()=>{
  const ui=harness();await ui.click();
  assert.equal(ui.shares.length,0);assert.match(ui.feedback.textContent,/Toque novamente/);
  await ui.click();assert.equal(ui.shares.length,1);
});
