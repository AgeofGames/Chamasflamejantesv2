const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('opening opponents inside a profile returns focus and scroll to the original page',async()=>{
  const listeners=new Map(), focus=[], calls=[];
  const body={style:{overflow:'auto'}};
  const close={focus(){}};
  const modal={hidden:true,setAttribute(){},querySelector:()=>close};
  const content={innerHTML:''};
  const document={body,addEventListener:(event,fn)=>listeners.set(event,fn),dispatchEvent(){},
    getElementById:id=>id==='profile-modal'?modal:id==='profile-modal-content'?content:null,querySelector:()=>null};
  const context={document,window:{},console,AbortController,
    CustomEvent:class{},setTimeout:()=>1,clearTimeout(){},
    fetch:async url=>{calls.push(url);return{ok:true,text:async()=>'<article>Histórico público</article>'};}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/social.js'),'utf8'),context);
  const trigger=(id)=>({isConnected:true,dataset:{profileCardUrl:'/perfil/'+id+'/card'},focus(){focus.push(id);},
    closest:selector=>selector==='.profile-popup-trigger[data-profile-card-url]'?button:null});
  let button=trigger(1);
  await listeners.get('click')({target:button,preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(modal.hidden,false);assert.equal(body.style.overflow,'hidden');
  button=trigger(2);
  await listeners.get('click')({target:button,preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  listeners.get('keydown')({key:'Escape'});
  assert.equal(modal.hidden,true);assert.equal(body.style.overflow,'auto');
  assert.deepEqual(calls,['/perfil/1/card','/perfil/2/card']);
  assert.deepEqual(focus,[1]);
});
