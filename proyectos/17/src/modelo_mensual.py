"""Probabilidad mensual de al menos un parte en un municipio."""
import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, log_loss, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from .modelo_clima import ROOT, RESULTS

GLOBAL, MONTH, BASE, CLIMATE, HYBRID = ("Prevalencia global", "Frecuencia por mes", "Municipio + mes",
                                         "Clima y territorio", "Híbrido")
NAMES = [GLOBAL, MONTH, BASE, CLIMATE, HYBRID]
NUMERIC = ["log_area", "vpd_previo", "lluvia_previa", "seno_mes", "coseno_mes"]
CATS = ["cod_ine", "mes_cat"]


def read_events():
    src = ROOT / "sources" / "egif"
    coverage = pd.read_csv(src / "cobertura.csv")
    years = sorted(coverage.loc[coverage.apto_modelo.astype(str).str.lower().isin(["true","1","sí","si"]), "anio"].astype(int))
    if not years:
        raise ValueError("Ningún año verificado para construir observaciones sin parte")
    data = pd.read_csv(src / "partes_madrid.csv", dtype={"ine":str,"parte":str}, parse_dates=["fecha"])
    data = data.loc[data.fecha.dt.year.isin(years)].copy()
    if data.fecha.isna().any() or data.duplicated(["anio","parte"]).any() or (data.fecha.dt.year != data.anio).any():
        raise ValueError("Fecha o identificador EGIF incompatible")
    return data, years


def panel(municipalities, monthly, events, years):
    """Cuadrícula de meses verificados, más un año de planificación."""
    if not set(events.ine).issubset(municipalities.cod_ine):
        raise ValueError("Parte sin correspondencia INE")
    future = max(max(years) + 1, 2027)
    periods = pd.MultiIndex.from_product([years + [future],range(1,13)], names=["anio","mes"]).to_frame(index=False)
    grid = municipalities[["cod_ine","zona","estacion","superficie_km2"]].merge(periods,how="cross")
    counts = events.assign(mes=events.fecha.dt.month).groupby(["ine","anio","mes"]).size().rename("partes").reset_index()
    grid = grid.merge(counts.rename(columns={"ine":"cod_ine"}), how="left", on=["cod_ine","anio","mes"],validate="one_to_one")
    covered = grid.anio.isin(years)
    grid.loc[covered, "partes"] = grid.loc[covered, "partes"].fillna(0)
    grid["y"] = grid.partes.gt(0).astype(int)
    grid.loc[~covered,"y"] = np.nan
    # A 1 de enero solo entran años terminados. Una estación se trata una vez.
    weather = []
    for year in periods.anio.unique():
        prior = monthly.loc[monthly.anio.lt(year)]
        climate = prior.groupby(["estacion","mes"],as_index=False).agg(
                            vpd_previo=("vpd_kpa","median"),lluvia_previa=("lluvia_mm","median"))
        weather.append(climate.assign(anio=year))
    grid = grid.merge(pd.concat(weather), on=["estacion","mes","anio"], how="left",validate="many_to_one")
    grid["log_area"] = np.log1p(grid.superficie_km2)
    grid["mes_cat"] = grid.mes.astype(str)
    angle = 2*np.pi*(grid.mes-1)/12
    grid["seno_mes"], grid["coseno_mes"] = np.sin(angle), np.cos(angle)
    return grid


def train(data, name):
    target = data.y.astype(int)
    if name == GLOBAL:
        return float(target.mean())
    if name == MONTH:
        by_month = data.groupby("mes").y.agg(["sum","size"])
        # Misma regularización que en la comparación entregada por el equipo.
        return ((by_month["sum"] + 12*target.mean()) / (by_month["size"]+12)).to_dict()
    transforms = []
    if name in (BASE,HYBRID):
        transforms.append(("categorias",OneHotEncoder(handle_unknown="ignore"),CATS))
    if name in (CLIMATE,HYBRID):
        impute = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                               StandardScaler())
        transforms.append(("continuas",impute,NUMERIC))
    return make_pipeline(ColumnTransformer(transforms), LogisticRegression(C=1., max_iter=1000, tol=1e-7)).fit(data,target)


def predict(fit, data, name):
    if name == GLOBAL:
        return np.full(len(data),fit)
    if name == MONTH:
        return data.mes.map(fit).to_numpy()
    return fit.predict_proba(data)[:,1]


def top20_recall(frame):
    """Reparte fraccionalmente el cupo restante entre todos los empates."""
    recovered = 0.
    for _, block in frame.groupby("mes"):
        n = min(20,len(block))
        boundary = block.p.nlargest(n).iloc[-1]
        better = block.p.gt(boundary)
        same = block.p.eq(boundary)
        recovered += block.y[better].sum() + (n-better.sum()) / same.sum() * block.y[same].sum()
    return recovered / frame.y.sum() if frame.y.sum() else np.nan


def score(data, scores, threshold):
    y = data.y.to_numpy(dtype=int)
    classes = scores >= threshold
    tn,fp,fn,tp = confusion_matrix(y, classes,labels=[0,1]).ravel()
    return dict(n=len(y),positivos=int(y.sum()),prevalencia=y.mean(),roc_auc=roc_auc_score(y,scores),
                ap=average_precision_score(y,scores),brier=brier_score_loss(y,scores),
                log_loss=log_loss(y,scores,labels=[0,1]),precision=precision_score(y,classes,zero_division=0),
                recall=recall_score(y,classes,zero_division=0),f1=f1_score(y,classes,zero_division=0),
                tn=tn,fp=fp,fn=fn,tp=tp,umbral=threshold,recall_at_20=top20_recall(data.assign(p=scores)))


def evaluate(training, evaluation, label, names, metrics, calib, predictions):
    for name in names:
        fit = train(training,name)
        probability = predict(fit,evaluation,name)
        key = dict(experimento=label, anio=int(evaluation.anio.iloc[0]), modelo=name)
        metrics.append({**key, **score(evaluation,probability,training.y.mean())})
        frame = evaluation[["cod_ine","mes","y"]].assign(p=probability,**key)
        # Intervalos de igual anchura: una probabilidad repetida ocupa siempre un solo grupo.
        frame["grupo"] = np.minimum(np.floor(frame.p*10).astype(int),9)
        reliability = frame.groupby("grupo",as_index=False).agg(p_media=("p","mean"),observada=("y","mean"),n=("y","size"))
        calib.append(reliability.assign(**key))
        predictions.append(frame)


def select(metrics):
    table = metrics.loc[(metrics.experimento=="Expansiva") & (metrics.anio.isin([2021,2022]))].groupby("modelo")[["brier","ap"]].mean()
    if set(table.index) != set(NAMES):
        raise ValueError("Se requieren 2021 y 2022 para la selección predefinida")
    # Mantener una referencia hasta que un candidato mejore ambos indicadores medios.
    chosen = GLOBAL
    for name in (MONTH, BASE, CLIMATE, HYBRID):
        if table.loc[name,"brier"] < table.loc[chosen,"brier"] and table.loc[name,"ap"] > table.loc[chosen,"ap"]:
            chosen = name
    return chosen


def effects(fit,name):
    if name not in (BASE,HYBRID,CLIMATE):
        return pd.DataFrame(columns=["variable","coef","odds_ratio"])
    variables = fit[0].get_feature_names_out()
    coefficients = fit[-1].coef_.ravel()
    return pd.DataFrame({"variable":variables,"coef":coefficients,"odds_ratio":np.exp(coefficients)})


def export_fit(fit, name, years, coefs):
    payload = dict(modelo=name,train_desde=min(years),train_hasta=max(years),anios=years,
                   criterio="Comparación secuencial de Brier y AP medios en 2021 y 2022. Se conserva la referencia si mejora solo una métrica.",
                   objetivo="Al menos un parte por municipio y mes.")
    if name in (GLOBAL,MONTH):
        payload["estimacion"] = fit
    else:
        payload["intercepto"] = float(fit[-1].intercept_[0])
        payload["coeficientes"] = dict(zip(coefs.variable,coefs.coef))
        if name in (CLIMATE,HYBRID):
            imputer, scaler = fit[0].named_transformers_["continuas"].steps
            payload.update(mediana_imputacion=dict(zip(NUMERIC,imputer[1].statistics_)),
                           media_estandarizacion=dict(zip(NUMERIC,scaler[1].mean_)),
                           escala_estandarizacion=dict(zip(NUMERIC,scaler[1].scale_)))
    (ROOT/"models"/"mensual.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")


def uncertainty(scores, chosen, year):
    a = scores.query("experimento == 'Expansiva' and anio == @year").pivot(index=["mes","cod_ine","y"],columns="modelo",values="p").reset_index()
    brier_difference = (a[chosen]-a.y)**2 - (a[MONTH]-a.y)**2
    groups = brier_difference.groupby(a.mes).mean().to_numpy()
    rng = np.random.default_rng(2026)
    draws = rng.choice(groups, (2000,len(groups)),replace=True).mean(axis=1)
    return dict(anio=year,referencia=MONTH,modelo=chosen,delta_brier=groups.mean(),
                p025=float(np.quantile(draws,.025)),p975=float(np.quantile(draws,.975)),bloques=len(groups))


def run_models(municipalities, monthly):
    events, years = read_events()
    grid = panel(municipalities,monthly,events,years)
    metrics, calibration, predictions = [], [], []
    # Se emite una temporada completa con datos disponibles antes del 1 de enero.
    folds = [y for y in years if y >= 2018 and y > min(years)]
    for year in folds:
        training = grid[grid.anio < year]
        test = grid[grid.anio == year]
        evaluate(training,test,"Expansiva", NAMES,metrics,calibration,predictions)
        if year == 2023:
            evaluate(training[training.anio >= 2020],test,"Ventana 2020–2022",NAMES,metrics,calibration,predictions)
    chosen = select(pd.DataFrame(metrics))
    final_eval = max(folds)
    training = grid[grid.anio < final_eval]
    test = grid[grid.anio == final_eval]
    # Transferencia sin ningún ejemplo de la zona, siempre con evaluación en el año siguiente.
    for name in (MONTH, BASE, HYBRID):
        blocks = []
        for zone, block in test.groupby("zona"):
            fitted = train(training[training.zona != zone],name)
            blocks.append(block.assign(p=predict(fitted,block,name)))
        heldout = pd.concat(blocks)
        metrics.append(dict(experimento="Zona excluida",anio=final_eval,modelo=name,**score(heldout,heldout.p.to_numpy(),training.y.mean())))
    table = pd.DataFrame(metrics)
    table.to_csv(RESULTS/"metricas_mensuales.csv",index=False,float_format="%.8f")
    pd.concat(calibration).to_csv(RESULTS/"calibracion_mensual.csv",index=False,float_format="%.8f")
    pred = pd.concat(predictions)
    pd.DataFrame([uncertainty(pred,chosen,final_eval)]).to_csv(RESULTS/"incertidumbre_mensual.csv", index=False)
    pred.loc[(pred.anio==final_eval)&(pred.experimento=="Expansiva"),["cod_ine","mes","y","modelo","p","anio"]].to_csv(
        RESULTS/"predicciones_validacion_mensual.csv",index=False,float_format="%.8f")
    learn = grid[grid.anio.isin(years)]
    future = grid[~grid.anio.isin(years)].copy()
    fit = train(learn,chosen)
    future["probabilidad"] = predict(fit,future,chosen)
    future["rango"] = future.groupby("mes").probabilidad.rank(ascending=False,method="min").astype(int)
    counts = learn.groupby(["cod_ine","mes"]).y.agg(anios_con_parte="sum",anios_observados="count",frecuencia_observada="mean").reset_index()
    # Intervalo Wilson de la proporción histórica binomial. No cubre el error del modelo futuro.
    p,n,z = counts.frecuencia_observada,counts.anios_observados,1.959963984540054
    mid = (p + z*z / (2*n)) / (1+z*z/n)
    half = z/(1+z*z/n)*np.sqrt(p*(1-p)/n + z*z/(4*n*n))
    counts["wilson_inf"],counts["wilson_sup"] = (mid-half).clip(0,1), (mid+half).clip(0,1)
    coefs = effects(fit,chosen)
    coefs.to_csv(RESULTS/"coeficientes_mensuales.csv",index=False)
    export_fit(fit,chosen,years,coefs)
    odds = coefs.set_index("variable").odds_ratio
    future["odds_municipio"] = ("categorias__cod_ine_"+future.cod_ine).map(odds)
    future["odds_mes"] = ("categorias__mes_cat_"+future.mes_cat).map(odds)
    outcols = ["cod_ine","mes","probabilidad","rango","odds_municipio","odds_mes"]
    future[outcols].merge(counts,on=["cod_ine","mes"]).to_csv(RESULTS/"ocurrencia_mensual.csv",index=False,float_format="%.8f")
    print(table[(table.anio==final_eval) & (table.experimento!="Zona excluida")].to_string(index=False))
    print("Modelo seleccionado:",chosen)


def run(municipalities, monthly):
    with threadpool_limits(limits=1):
        run_models(municipalities,monthly)
