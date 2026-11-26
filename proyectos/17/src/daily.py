"""Experimento de ocurrencia diaria, con fecha de corte común a toda la semana."""
from __future__ import annotations
import calendar
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, log_loss, precision_score, recall_score, roc_auc_score)

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"
METEO = ["vpd_max_kpa", "lluvia_mm", "viento_ms"]
NAMES = ["Prevalencia", "Calendario", "Municipio y calendario", "Municipio, calendario y tiempo antecedente"]


def antecedents(daily):
    """Ventana [t−13, t−7] en días naturales. Exige al menos 4 de 7 días."""
    groups = []
    for station, data in daily.groupby("estacion"):
        data = data.set_index("fecha")[METEO].sort_index().asfreq("D")
        # Extender permite calcular las fechas posteriores al último registro.
        dates = pd.date_range(data.index.min(), data.index.max() + pd.Timedelta(days=7))
        features = data.reindex(dates).rolling(7, min_periods=4).mean().shift(7)
        groups.append(features.rename_axis("fecha").reset_index().assign(estacion=station))
    return pd.concat(groups, ignore_index=True)


def harmonic(dates):
    phase = 2 * np.pi * (dates.dt.dayofyear.to_numpy() - 1) / np.where(dates.dt.is_leap_year, 366, 365)
    return np.column_stack((np.sin(phase), np.cos(phase), np.sin(2 * phase), np.cos(2 * phase)))


def build_panel():
    names = pd.read_csv(PROC/"municipios.csv", dtype={"cod_ine":str, "estacion":str}).sort_values("cod_ine")
    events = pd.read_csv(ROOT/"sources/egif/partes_madrid.csv", dtype={"ine":str}, parse_dates=["fecha"])
    events = events[events.fecha.dt.year.between(2020, 2023)]
    if events.groupby(events.fecha.dt.year).size().to_dict() != {2020:242, 2021:314, 2022:295, 2023:201}:
        raise ValueError("La cobertura EGIF de 2020–23 ha cambiado. Revisar el denominador antes de entrenar.")
    if not set(events.ine) <= set(names.cod_ine) or len(names.cod_ine.unique()) != 179:
        raise ValueError("Desajuste entre municipios cartografiados y partes")
    grid = pd.MultiIndex.from_product([pd.date_range("2020-01-01", "2023-12-31"), names.cod_ine],
                                      names=["fecha", "ine"]).to_frame(index=False)
    grid["y"] = pd.MultiIndex.from_frame(grid[["fecha","ine"]]).isin(
        pd.MultiIndex.from_frame(events[["fecha","ine"]])).astype(int)
    grid = grid.merge(names[["cod_ine","estacion"]], left_on="ine", right_on="cod_ine", validate="many_to_one")
    daily = pd.read_csv(PROC/"estaciones_diarias.csv", dtype={"estacion":str}, parse_dates=["fecha"])
    grid = grid.merge(antecedents(daily), on=["fecha","estacion"], how="left", validate="many_to_one")
    return grid, list(names.cod_ine)


def fit_predict(train, test, codes, variant):
    y = train.y
    if variant == 0:
        return np.repeat(y.mean(),len(test)), {"intercept": float(np.log(y.mean()/(1-y.mean())))}
    medians = train[METEO].median().fillna(0.)
    filled = train[METEO].fillna(medians)
    mean, std = filled.mean(), filled.std().replace(0.,1.).fillna(1.)
    def matrix(data):
        blocks = [sparse.csr_matrix(harmonic(data.fecha))]
        if variant >= 2:
            ids = pd.Categorical(data.ine,categories=codes).codes
            blocks.append(sparse.csr_matrix((np.ones(len(ids)),(np.arange(len(ids)),ids)),shape=(len(ids),len(codes))))
        if variant == 3:
            blocks.extend([sparse.csr_matrix(((data[METEO].fillna(medians)-mean)/std).values),
                           sparse.csr_matrix(data[METEO].isna().astype(float).values)])
        return sparse.hstack(blocks,format="csr")
    model = LogisticRegression(C=1.,solver="lbfgs",max_iter=350,tol=1e-9).fit(matrix(train),y)
    p = model.predict_proba(matrix(test))[:,1]
    coef = model.coef_[0].tolist()
    return p, {"intercept":float(model.intercept_[0]),"season":coef[:4],
               "municipal":dict(zip(codes,coef[4:4+len(codes)])) if variant>=2 else {}}


def evaluate(frame, p, threshold):
    y = frame.y
    pred = p>=threshold
    ranked = frame[["fecha","ine","y"]].assign(p=p)
    # Empates en K: esperanza sobre una elección uniforme entre los empatados.
    rank_first = ranked.groupby("fecha").p.rank(method="min",ascending=False)
    rank_last = ranked.groupby("fecha").p.rank(method="max",ascending=False)
    included = ((21-rank_first)/(rank_last-rank_first+1)).clip(0,1)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return dict(n=len(y),dias_municipio_positivos=int(y.sum()),prevalencia=y.mean(),
                roc_auc=roc_auc_score(y,p),ap=average_precision_score(y,p),
                brier=brier_score_loss(y,p),log_loss=log_loss(y,p,labels=[0,1]),
                recall_at_20=(included*y).sum()/y.sum(),umbral=threshold,
                precision=precision_score(y,pred,zero_division=0),recall=recall_score(y,pred),
                f1=f1_score(y,pred,zero_division=0),tn=tn,fp=fp,fn=fn,tp=tp)


def run():
    grid,codes=build_panel()
    years=grid.fecha.dt.year
    results, calibration = [], []
    for year in [2021,2022,2023]:
        train=grid[years<year]
        test=grid[years==year]
        for variant,name in enumerate(NAMES):
            p,_=fit_predict(train,test,codes,variant)
            results.append(dict(anio=year,modelo=name,**evaluate(test,p,train.y.mean())))
            if np.ptp(p)==0:
                bins=np.zeros(len(p),dtype=int)
            else:
                bins=pd.qcut(p,q=10,labels=False,duplicates="drop")
            curve=pd.DataFrame({"grupo":bins,"p":p,"y":test.y.to_numpy()}).groupby("grupo").agg(
                n=("y","size"),observada=("y","mean"),estimada=("p","mean")).reset_index()
            calibration.append(curve.assign(anio=year,modelo=name))
    metrics=pd.DataFrame(results)
    metrics.to_csv(RESULTS/"metricas_diarias.csv",index=False)
    pd.concat(calibration).to_csv(RESULTS/"calibracion_diaria.csv",index=False)
    # Para uso sin observaciones meteorológicas recientes las alternativas elegibles
    # disponen exclusivamente de información conocida para los siete horizontes.
    selection=metrics[metrics.anio.lt(2023)&metrics.modelo.isin(NAMES[:3])].groupby("modelo").ap.mean()
    selected=selection.idxmax()
    _,params=fit_predict(grid,grid.iloc[:1],codes,NAMES.index(selected))
    params.update(modelo=selected,periodo="2020–2023",codigos=codes,
                  criterio="Máxima AP media en 2021 y 2022 entre referencias disponibles sin observaciones recientes")
    (ROOT/"models/diario.json").write_text(json.dumps(params,ensure_ascii=False,indent=2),encoding="utf-8")
    print(metrics[metrics.anio==2023][["modelo","ap","roc_auc","brier","recall_at_20"]].to_string(index=False))

if __name__=="__main__":
    run()
