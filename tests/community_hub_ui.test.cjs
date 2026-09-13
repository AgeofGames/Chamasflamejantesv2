const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../static/community_hub.js'),'utf8');
class Form {
  constructor(kind='like') {
    this.dataset=kind==='like'?{hubLike:''}:{};this.action='/mural/publicacao/1/curtir';
    this.elements={liked:{value:'1'},title:{},body:{},event:{}};
    this.parts={button:{disabled:false,setAttribute(k,v){this[k]=v;}},
      '[data-like-status]':{textContent:''},'[data-like-count]':{textContent:'0'},'[data-like-label]':{textContent:'Curtir'}};
  }
  querySelector(s){return this.parts[s];}
  matches(s){return s==='[data-hub-like]'&&Object.hasOwn(this.dataset,'hubLike');}
}
function setup({forms=[],charts=[],fetcher=async()=>({ok:true,json:async()=>({liked:true,count:1})}),confirm=true}={}){
  const events={},timers=new Map(),calls=[];
  const document={readyState:'complete',addEventListener:(e,fn)=>events[e]=fn,
    querySelectorAll:s=>s==='[data-hub-chart]'?charts:s==='[data-hub-composer]'?forms:[],
    createElement:()=>({textContent:'',href:''})};
  const fetch=async(url,options)=>{calls.push({url,options});return fetcher(url,options);};
  const window={addEventListener:(e,fn)=>events[e]=fn,location:{href:'https://site.test/perfil/1',origin:'https://site.test'},fetch,
    confirm:()=>confirm,setTimeout:(fn,ms)=>{const id=Symbol();timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id)};
  vm.runInNewContext(source,{document,window,HTMLFormElement:Form,FormData:class{constructor(form){this.form=form;}},fetch,AbortController,URL});
  const submit=form=>{const event={target:form,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;}};return{event,promise:events.submit(event)};};
  return {events,timers,calls,submit};
}
function chart(){
  const points=[0,1].map(i=>({dataset:{chartIndex:String(i)},events:{},attrs:{},
    setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,fn){this.events[k]=fn;},focus(){this.events.focus();}}));
  const detail={textContent:'',links:[],appendChild(a){this.links.push(a);}};
  const data=[{date:'10/09/2026',won:false,delta:-30,adjustment:0,before:0,after:0,applied:0,url:'/duelo/1',event_id:1},
    {date:'10/09/2026',won:true,delta:120,adjustment:90,before:0,after:120,applied:120,url:'/duelo/2',event_id:2}];
  return {dataset:{},detail,points,data,querySelectorAll:()=>points,
    querySelector(s){if(s==='[data-chart-events]')return{textContent:JSON.stringify(data)};
      if(s==='[data-chart-detail]')return detail;
      const index=s.match(/data-chart-index="(\d+)"/);return index?points[Number(index[1])]:null;}};
}

test('graph details explain zero floor and Elo adjustments and support keyboard selection',()=>{
  const c=chart();setup({charts:[c]});c.points[0].events.click();
  assert.match(c.detail.textContent,/Piso zero aplicado/);assert.match(c.detail.textContent,/0 → 0/);
  c.points[0].events.keydown({key:'ArrowRight',preventDefault(){}});
  assert.match(c.detail.textContent,/\+90 por Elo/);assert.match(c.detail.textContent,/0 → 120/);
  assert.equal(c.points[1].attrs['aria-pressed'],'true');assert.equal(c.detail.links.at(-1).href,'https://site.test/duelo/2');
});

test('chart never creates an off-site duel link and modal initialization is idempotent',()=>{
  const c=chart();c.data[0].url='https://unrelated.test/phish';
  const state=setup({charts:[c]});c.points[0].events.click();assert.equal(c.detail.links.length,0);
  const original=c.points[0].events.click;state.events['chamas:content']({detail:{container:{querySelectorAll:s=>s==='[data-hub-chart]'?[c]:[]}}});
  assert.equal(c.points[0].events.click,original);
});

test('cancelled deletion confirmation prevents the original form submission',async()=>{
  const form=new Form('delete');form.dataset.hubConfirm='Remover esta publicação?';
  const state=setup({confirm:false}),r=state.submit(form);await r.promise;
  assert.equal(r.event.defaultPrevented,true);assert.equal(state.calls.length,0);
});
