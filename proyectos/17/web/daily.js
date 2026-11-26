(() => {
  let pending;
  window.dailyOccurrence = async function(ine, isoDate) {
    try {
      pending ??= fetch('/models/diario.json').then(r => {
        if (!r.ok) throw Error(r.status);
        return r.json();
      }).catch(err => { pending = undefined; throw err; });
      const model = await pending;
      if (!model.codigos.includes(ine)) return null;
      const year = Number(isoDate.slice(0,4));
      const start = Date.UTC(year,0,1);
      const phase = 2*Math.PI*(Date.parse(isoDate+'T00:00:00Z')-start)/(Date.UTC(year+1,0,1)-start);
      const x = [Math.sin(phase), Math.cos(phase), Math.sin(2*phase), Math.cos(2*phase)];
      const base = model.intercept + x.reduce((s,v,i)=>s+v*(model.season?.[i]??0),0);
      const predict = id => 1/(1+Math.exp(-(base+(model.municipal?.[id]??0))));
      return {p:predict(ine), regional:model.codigos.reduce((s,id)=>s+predict(id),0)/model.codigos.length,
              nombre:model.modelo, periodo:model.periodo};
    } catch { return null; }
  };
})();
