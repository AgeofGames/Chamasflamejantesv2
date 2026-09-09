// Exercise failure recovery without a browser or additional npm dependencies.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../static/duel.js'), 'utf8');

function harness(fetcher) {
  const attrs = () => ({attrs:new Map(), setAttribute(k,v){this.attrs.set(k,v);}, removeAttribute(k){this.attrs.delete(k);}});
  const button = {...attrs(), disabled:false};
  const status = {textContent:'', classList:{toggle(){}}};
  const panel = {...attrs(), querySelector(){return status;}, querySelectorAll(query){return query === 'button' ? [button] : [form];}};
  const form = {...attrs(), dataset:{submitting:'true'}, action:'https://chamasflamejantes.com.br/duelo/5/verificar',
    matches(){return true;}, closest(){return panel;}, querySelector(){return button;}};
  const timers = new Map();
  let handler, calls=0;
  const context = {
    console, URL, AbortController, FormData:class {},
    document:{addEventListener(name, fn){handler=fn;}, querySelectorAll(){return [];}, querySelector(){return null;}},
    window:{fetch:true, AbortController, location:{href:form.action,origin:'https://chamasflamejantes.com.br'},
      setTimeout(fn, ms){timers.set(ms,fn);return ms;}, clearTimeout(id){timers.delete(id);}},
    fetch(...args){calls++;return fetcher(...args);},
  };
  vm.runInNewContext(code, context);
  return {button,panel,form,status,timers, calls:()=>calls,
    submit:()=>handler({target:form,submitter:button,preventDefault(){}})};
}

test('a stalled lookup times out, prevents duplicate requests and re-enables the form', async () => {
  const ui=harness((url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Object.assign(new Error('aborted'),{name:'AbortError'})))));
  const pending=ui.submit();
  assert.equal(ui.button.disabled,true);
  assert.equal(ui.button.attrs.get('aria-busy'),'true');
  await ui.submit();
  assert.equal(ui.calls(),1);
  assert.ok(ui.timers.has(20000));
  ui.timers.get(20000)();
  await pending;
  assert.equal(ui.button.disabled,false);
  assert.equal(ui.button.attrs.has('aria-busy'),false);
  assert.equal(ui.form.dataset.submitting,undefined);
  assert.equal(ui.timers.size,0);
  assert.match(ui.status.textContent,/limite de tempo/);
});

test('network failure stops the spinner and leaves a useful message', async () => {
  const ui=harness(()=>Promise.reject(new Error('Falha de conexão')));
  await ui.submit();
  assert.equal(ui.button.disabled,false);
  assert.equal(ui.panel.attrs.has('aria-busy'),false);
  assert.equal(ui.timers.size,0);
  assert.match(ui.status.textContent,/Falha de conexão/);
});

test('an expired session or an HTML server error does not leave loading active', async () => {
  const ui=harness(()=>Promise.resolve({headers:{get(){return 'text/html';}}}));
  await ui.submit();
  assert.equal(ui.button.disabled,false);
  assert.equal(ui.form.dataset.submitting,undefined);
  assert.match(ui.status.textContent,/Recarregue/);
});
