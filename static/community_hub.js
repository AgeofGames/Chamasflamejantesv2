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
  };
  document.addEventListener('submit',event=>{
    const form=event.target;if(event.defaultPrevented||!(form instanceof HTMLFormElement))return;
    if(form.dataset.hubConfirm&&!window.confirm(form.dataset.hubConfirm)){event.preventDefault();return;}
  });
  const openLinkedPanel=()=>{
    const id=window.location.hash?.slice(1);
    if(!['conquistas','evolucao','rivalidades'].includes(id))return;
    const panel=document.getElementById(id);
    if(panel?.matches('details.profile-journey-card'))panel.open=true;
  };
  const ready=()=>{init(document);openLinkedPanel();};
  window.addEventListener('hashchange',openLinkedPanel);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready);else ready();
  document.addEventListener('chamas:content',event=>init(event.detail?.container||document));
})();
