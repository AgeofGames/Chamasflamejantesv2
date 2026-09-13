/* Progressive enhancement; regular forms remain usable without JavaScript. */
(() => {
  'use strict';
  const signed = value => `${value > 0 ? '+' : ''}${value}`;
  const selectPoint = (chart,index) => {
    const item=chart.hubEvents?.[index],detail=chart.querySelector('[data-chart-detail]');
    if (!item || !detail) return;
    chart.querySelectorAll('[data-chart-index]').forEach(p=>p.setAttribute('aria-pressed',String(Number(p.dataset.chartIndex)===index)));
    detail.textContent=`${item.date} · ${item.won?'Vitória':'Derrota'} · Regra: ${signed(item.delta)} pontos`+
      `${item.adjustment?` (inclui ${signed(item.adjustment)} por Elo)`:''}. Saldo: ${item.before} → ${item.after}.`+
      `${item.applied!==item.delta?` Piso zero aplicado: variação real ${signed(item.applied)}.`:''} `;
    const url=new URL(item.url,window.location.href);
    if(url.origin===window.location.origin){const a=document.createElement('a');a.href=url.href;a.textContent=`Ver duelo #${item.event_id} →`;detail.appendChild(a);}
  };
  const init=root=>{
    root.querySelectorAll('[data-hub-chart]').forEach(chart=>{
      if(chart.dataset.hubReady)return;
      try{chart.hubEvents=JSON.parse(chart.querySelector('[data-chart-events]').textContent);}catch(_){return;}
      chart.dataset.hubReady='1';
      chart.querySelectorAll('[data-chart-index]').forEach(point=>{
        const choose=()=>selectPoint(chart,Number(point.dataset.chartIndex));point.setAttribute('aria-pressed','false');
        point.addEventListener('click',choose);point.addEventListener('focus',choose);
        point.addEventListener('keydown',event=>{
          if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}
          if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();const next=Number(point.dataset.chartIndex)+(event.key==='ArrowLeft'?-1:1);chart.querySelector(`[data-chart-index="${next}"]`)?.focus();}
        });
      });
    });
    root.querySelectorAll('[data-hub-composer]').forEach(form=>{
      if(form.dataset.hubReady)return;form.dataset.hubReady='1';
      const kind=form.querySelector('[data-post-kind]');
      const update=()=>{const victory=kind.value==='vitoria';form.querySelector('[data-post-title]').hidden=victory;form.querySelector('[data-post-victory]').hidden=!victory;form.elements.title.required=!victory;form.elements.title.minLength=victory?0:3;form.elements.event.required=victory;form.elements.body.required=!victory;};
      kind.addEventListener('change',update);update();
    });
  };
  document.addEventListener('submit',async event=>{
    const form=event.target;if(event.defaultPrevented||!(form instanceof HTMLFormElement))return;
    if(form.dataset.hubConfirm&&!window.confirm(form.dataset.hubConfirm)){event.preventDefault();return;}
    if(!form.matches('[data-hub-like]')||!window.fetch)return;
    event.preventDefault();if(form.dataset.likeBusy)return;
    const button=form.querySelector('button'),note=form.querySelector('[data-like-status]'),controller=new AbortController();
    const timer=window.setTimeout(()=>controller.abort(),8000);form.dataset.likeBusy='1';button.disabled=true;note.textContent='';
    try{
      const response=await fetch(form.action,{method:'POST',credentials:'same-origin',headers:{'Accept':'application/json'},body:new FormData(form),signal:controller.signal});
      if(!response.ok||response.redirected)throw new Error('request');const result=await response.json();
      if(!Number.isInteger(result.count)||typeof result.liked!=='boolean')throw new Error('response');
      form.elements.liked.value=result.liked?'0':'1';form.querySelector('[data-like-count]').textContent=result.count;
      form.querySelector('[data-like-label]').textContent=result.liked?'Curtido':'Curtir';button.setAttribute('aria-pressed',String(result.liked));
    }catch(_){note.textContent='Não foi possível atualizar a curtida. Tente novamente; se sua sessão expirou, entre com o Google.';}
    finally{window.clearTimeout(timer);delete form.dataset.likeBusy;button.disabled=false;}
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>init(document));else init(document);
  document.addEventListener('chamas:content',event=>init(event.detail?.container||document));
})();
