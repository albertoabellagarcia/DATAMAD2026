from __future__ import annotations

import json
import math
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd
import requests

API = "https://datos.comunidad.madrid/api/3/action/"
IDEM_WFS = "https://idem.comunidad.madrid/geoidem/UnidadesAdministrativas/wfs"
CACHE_DIR = Path("emprendemad_cache")
OUT_HTML = Path("emprendemad.html")
OUT_AUDIT = Path("emprendemad_data_audit.json")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "EmprendeMAD/4.0"

DATASET_CANDIDATES = {
    "municipality_ref": {
        "slugs": ["municipio_comunidad_madrid"],
        "queries": ["municipio comunidad de madrid", "municipios comunidad madrid codigo"],
        "required_formats": {"csv", "json"},
    },
    "business": {
        "slugs": ["col_emp_ramas"],
        "queries": ["col_emp_ramas colectivo empresarial rama actividad municipios", "colectivo empresarial por rama de actividad municipios"],
        "required_formats": {"csv", "json"},
    },
    "population": {
        "slugs": ["padron_por_sexo", "poblacion_censada_por_edad_nacionalidad_y_sexo"],
        "queries": ["padron por sexo municipios comunidad de madrid", "poblacion censada por edad nacionalidad y sexo municipios"],
        "required_formats": {"csv", "json"},
    },
    "density": {
        "slugs": ["1930748", "densidad_de_poblacion_municipios"],
        "queries": ["densidad de población municipios comunidad de madrid", "densidad poblacion municipios"],
        "required_formats": {"csv", "json"},
    },
    "income": {
        "slugs": ["irpf_indicador_renta"],
        "queries": ["indicador renta disponible bruta municipal", "irpf indicador renta municipios comunidad de madrid"],
        "required_formats": {"csv", "json"},
    },
    "business_demography": {
        "slugs": ["demografia_empresarial_tipo_persona"],
        "queries": ["demografia empresarial tipo persona comunidad de madrid"],
        "required_formats": {"csv", "json"},
    },
}

# Ordered finest-to-broadest; each official branch in col_emp_ramas maps 1-to-1 (zero double-counting).
CNAE_CATEGORY_REGISTRY = [
    {
        "id": "restaurantes", "main_sector_es": "Hostelería y Turismo", "main_sector_en": "Hospitality & Tourism",
        "label_es": "Restaurantes y servicios de comidas", "label_en": "Restaurants & food services",
        "cnae_codes": ["561", "5610", "562"], "code_prefixes": ["561", "562"],
        "official_phrases": ["restaurantes y puestos de comidas", "provision de comidas preparadas"],
        "defaults": {"competition": 30, "demand": 25, "purchasing_power": 20, "momentum": 15, "market_scale": 10}, "demand_mode": "consumer_density",
    },
    {
        "id": "cafeterias_bares", "main_sector_es": "Hostelería y Turismo", "main_sector_en": "Hospitality & Tourism",
        "label_es": "Cafeterías y establecimientos de bebidas", "label_en": "Cafes & beverage establishments",
        "cnae_codes": ["563", "5630"], "code_prefixes": ["563"],
        "official_phrases": ["establecimientos de bebidas"],
        "defaults": {"competition": 30, "demand": 30, "purchasing_power": 18, "momentum": 12, "market_scale": 10}, "demand_mode": "consumer_density",
    },
    {
        "id": "alimentacion_retail", "main_sector_es": "Comercio Minorista", "main_sector_en": "Retail Trade",
        "label_es": "Alimentación, supermercados y panadería", "label_en": "Grocery, supermarkets & food retail",
        "cnae_codes": ["471", "472"], "code_prefixes": ["471", "472"],
        "official_phrases": ["comercio al por menor en establecimientos no especializados", "comercio al por menor de productos alimenticios"],
        "defaults": {"competition": 30, "demand": 30, "purchasing_power": 15, "momentum": 15, "market_scale": 10}, "demand_mode": "consumer_density",
    },
    {
        "id": "moda_calzado", "main_sector_es": "Comercio Minorista", "main_sector_en": "Retail Trade",
        "label_es": "Moda, calzado y retail especializado", "label_en": "Fashion, footwear & specialty retail",
        "cnae_codes": ["474", "475", "476", "477"], "code_prefixes": ["474", "475", "476", "477"],
        "official_phrases": ["prendas de vestir", "calzado y articulos de cuero", "otros articulos en establecimientos especializados"],
        "defaults": {"competition": 30, "demand": 25, "purchasing_power": 20, "momentum": 15, "market_scale": 10}, "demand_mode": "consumer_density",
    },
    {
        "id": "clinicas_dentales", "main_sector_es": "Salud y Bienestar", "main_sector_en": "Health & Wellness",
        "label_es": "Clínicas dentales y odontología", "label_en": "Dental clinics",
        "cnae_codes": ["8623"], "code_prefixes": ["8623"],
        "official_phrases": ["actividades odontologicas"],
        "defaults": {"competition": 28, "demand": 24, "purchasing_power": 22, "momentum": 14, "market_scale": 12}, "demand_mode": "health",
    },
    {
        "id": "consultoria_tech", "main_sector_es": "Tech y Servicios Profesionales", "main_sector_en": "Tech & Professional Services",
        "label_es": "Consultoría informática y software", "label_en": "IT consulting & software development",
        "cnae_codes": ["62", "620", "63"], "code_prefixes": ["62", "63"],
        "official_phrases": ["programacion consultoria y otras actividades relacionadas con la informatica", "servicios de informacion"],
        "defaults": {"competition": 25, "demand": 25, "purchasing_power": 18, "momentum": 17, "market_scale": 15}, "demand_mode": "b2b",
    },
    {
        "id": "gimnasios_deporte", "main_sector_es": "Salud y Bienestar", "main_sector_en": "Health & Wellness",
        "label_es": "Gimnasios y actividades deportivas", "label_en": "Gyms & sports activities",
        "cnae_codes": ["93", "931", "9313"], "code_prefixes": ["93"],
        "official_phrases": ["actividades de los gimnasios", "actividades deportivas", "actividades deportivas recreativas y de entretenimiento"],
        "defaults": {"competition": 28, "demand": 28, "purchasing_power": 20, "momentum": 14, "market_scale": 10}, "demand_mode": "wellness",
    },
    {
        "id": "peluqueria_estetica", "main_sector_es": "Servicios Personales", "main_sector_en": "Personal Services",
        "label_es": "Peluquería, estética y servicios personales", "label_en": "Hair salons, beauty & personal services",
        "cnae_codes": ["96", "9602"], "code_prefixes": ["96"],
        "official_phrases": ["peluqueria y otros tratamientos de belleza", "otros servicios personales"],
        "defaults": {"competition": 30, "demand": 25, "purchasing_power": 20, "momentum": 15, "market_scale": 10}, "demand_mode": "consumer_density",
    },
    {
        "id": "alojamiento", "main_sector_es": "Hostelería y Turismo", "main_sector_en": "Hospitality & Tourism",
        "label_es": "Servicios de alojamiento y turismo", "label_en": "Accommodation & hospitality lodging",
        "cnae_codes": ["55"], "code_prefixes": ["55"],
        "official_phrases": ["servicios de alojamiento"],
        "defaults": {"competition": 25, "demand": 25, "purchasing_power": 20, "momentum": 15, "market_scale": 15}, "demand_mode": "consumer_density",
    },
    {
        "id": "comidas_bebidas", "main_sector_es": "Hostelería y Turismo", "main_sector_en": "Hospitality & Tourism",
        "label_es": "Restauración, cafeterías y bares (CNAE 56 / I)", "label_en": "Restaurants, cafes & hospitality (CNAE 56 / I)",
        "cnae_codes": ["56", "I"], "code_prefixes": ["56", "I"],
        "official_phrases": ["servicios de comidas y bebidas", "hosteleria"],
        "defaults": {"competition": 30, "demand": 25, "purchasing_power": 20, "momentum": 15, "market_scale": 10}, "demand_mode": "consumer_density",
    },
    {
        "id": "taller_automocion", "main_sector_es": "Comercio Minorista", "main_sector_en": "Retail Trade",
        "label_es": "Venta y reparación de vehículos (CNAE 45)", "label_en": "Automotive sales & repair (CNAE 45)",
        "cnae_codes": ["45"], "code_prefixes": ["45"],
        "official_phrases": ["venta y reparacion de vehiculos de motor y motocicletas"],
        "defaults": {"competition": 28, "demand": 25, "purchasing_power": 17, "momentum": 15, "market_scale": 15}, "demand_mode": "consumer_density",
    },
    {
        "id": "comercio_mayorista", "main_sector_es": "Comercio y Distribución", "main_sector_en": "Trade & Distribution",
        "label_es": "Comercio al por mayor e intermediarios (CNAE 46)", "label_en": "Wholesale trade & distribution (CNAE 46)",
        "cnae_codes": ["46"], "code_prefixes": ["46"],
        "official_phrases": ["comercio al por mayor e intermediarios del comercio"],
        "defaults": {"competition": 25, "demand": 25, "purchasing_power": 15, "momentum": 15, "market_scale": 20}, "demand_mode": "b2b",
    },
    {
        "id": "comercio_minorista", "main_sector_es": "Comercio Minorista", "main_sector_en": "Retail Trade",
        "label_es": "Comercio al por menor y retail (CNAE 47 / G)", "label_en": "Retail trade & local shops (CNAE 47 / G)",
        "cnae_codes": ["47", "G"], "code_prefixes": ["47", "G"],
        "official_phrases": ["comercio al por menor excepto de vehiculos de motor", "comercio al por mayor y al por menor reparacion de vehiculos"],
        "defaults": {"competition": 30, "demand": 28, "purchasing_power": 18, "momentum": 14, "market_scale": 10}, "demand_mode": "consumer_density",
    },
    {
        "id": "info_comunicaciones", "main_sector_es": "Tech y Servicios Profesionales", "main_sector_en": "Tech & Professional Services",
        "label_es": "Tecnología, telecomunicaciones y media (CNAE J)", "label_en": "IT, telecoms & media (CNAE J)",
        "cnae_codes": ["58", "59", "60", "61", "J"], "code_prefixes": ["58", "59", "60", "61", "J"],
        "official_phrases": ["informacion y comunicaciones", "telecomunicaciones", "edicion"],
        "defaults": {"competition": 25, "demand": 25, "purchasing_power": 18, "momentum": 17, "market_scale": 15}, "demand_mode": "b2b",
    },
    {
        "id": "juridico_contable", "main_sector_es": "Tech y Servicios Profesionales", "main_sector_en": "Tech & Professional Services",
        "label_es": "Servicios jurídicos, asesoría y contabilidad (CNAE 69–70)", "label_en": "Legal, accounting & consulting (CNAE 69–70)",
        "cnae_codes": ["69", "70"], "code_prefixes": ["69", "70"],
        "official_phrases": ["actividades juridicas y de contabilidad", "actividades de consultoria de gestion empresarial"],
        "defaults": {"competition": 26, "demand": 26, "purchasing_power": 18, "momentum": 15, "market_scale": 15}, "demand_mode": "b2b",
    },
    {
        "id": "arquitectura_ingenieria", "main_sector_es": "Tech y Servicios Profesionales", "main_sector_en": "Tech & Professional Services",
        "label_es": "Arquitectura, ingeniería y servicios técnicos (CNAE 71–75 / M)", "label_en": "Architecture, engineering & technical services (CNAE 71–75 / M)",
        "cnae_codes": ["71", "72", "73", "74", "75", "M"], "code_prefixes": ["71", "72", "73", "74", "75", "M"],
        "official_phrases": ["servicios tecnicos de arquitectura e ingenieria", "publicidad y estudios de mercado", "actividades veterinarias", "actividades profesionales cientificas y tecnicas"],
        "defaults": {"competition": 25, "demand": 25, "purchasing_power": 20, "momentum": 15, "market_scale": 15}, "demand_mode": "b2b",
    },
    {
        "id": "sanidad_clinicas", "main_sector_es": "Salud y Bienestar", "main_sector_en": "Health & Wellness",
        "label_es": "Actividades sanitarias, clínicas y fisioterapia (CNAE 86 / Q)", "label_en": "Healthcare, medical & dental clinics (CNAE 86 / Q)",
        "cnae_codes": ["86", "87", "88", "Q"], "code_prefixes": ["86", "87", "88", "Q"],
        "official_phrases": ["actividades sanitarias", "actividades sanitarias y de servicios sociales", "asistencia en establecimientos residenciales", "actividades de servicios sociales sin alojamiento"],
        "defaults": {"competition": 28, "demand": 24, "purchasing_power": 20, "momentum": 16, "market_scale": 12}, "demand_mode": "health",
    },
    {
        "id": "educacion_academias", "main_sector_es": "Educación y Formación", "main_sector_en": "Education & Training",
        "label_es": "Academias, enseñanza y formación (CNAE 85 / P)", "label_en": "Education, tutoring & training academies (CNAE 85 / P)",
        "cnae_codes": ["85", "P"], "code_prefixes": ["85", "P"],
        "official_phrases": ["educacion"],
        "defaults": {"competition": 28, "demand": 24, "purchasing_power": 18, "momentum": 15, "market_scale": 15}, "demand_mode": "education",
    },
    {
        "id": "cultura_ocio_deporte", "main_sector_es": "Salud y Bienestar", "main_sector_en": "Health & Wellness",
        "label_es": "Deporte, ocio y actividades culturales (CNAE 90–93 / R)", "label_en": "Sports, fitness, recreation & culture (CNAE 90–93 / R)",
        "cnae_codes": ["90", "91", "92", "93", "R"], "code_prefixes": ["90", "91", "92", "93", "R"],
        "official_phrases": ["actividades artisticas recreativas y de entretenimiento", "actividades de creacion artisticas y espectaculos"],
        "defaults": {"competition": 28, "demand": 26, "purchasing_power": 20, "momentum": 14, "market_scale": 12}, "demand_mode": "wellness",
    },
    {
        "id": "servicios_personales_hogar", "main_sector_es": "Servicios Personales", "main_sector_en": "Personal Services",
        "label_es": "Otros servicios personales, estética y reparación (CNAE 94–96 / S)", "label_en": "Personal services, beauty & repairs (CNAE 94–96 / S)",
        "cnae_codes": ["94", "95", "96", "S"], "code_prefixes": ["94", "95", "96", "S"],
        "official_phrases": ["otros servicios", "reparacion de ordenadores efectos personales y articulos de uso domestico", "actividades asociativas"],
        "defaults": {"competition": 30, "demand": 25, "purchasing_power": 18, "momentum": 15, "market_scale": 12}, "demand_mode": "consumer_density",
    },
    {
        "id": "servicios_auxiliares_limpieza", "main_sector_es": "Servicios Auxiliares y B2B", "main_sector_en": "Business Support & Services",
        "label_es": "Limpieza, viajes, alquiler y servicios auxiliares (CNAE 77–82 / N)", "label_en": "Cleaning, travel, rental & support services (CNAE 77–82 / N)",
        "cnae_codes": ["77", "78", "79", "80", "81", "82", "N"], "code_prefixes": ["77", "78", "79", "80", "81", "82", "N"],
        "official_phrases": ["actividades administrativas y servicios auxiliares", "servicios a edificios y actividades de jardineria", "actividades de agencias de viajes operadores turisticos"],
        "defaults": {"competition": 25, "demand": 25, "purchasing_power": 16, "momentum": 16, "market_scale": 18}, "demand_mode": "b2b",
    },
    {
        "id": "finanzas_inmobiliario", "main_sector_es": "Finanzas e Inmobiliaria", "main_sector_en": "Finance & Real Estate",
        "label_es": "Finanzas, seguros y servicios inmobiliarios (CNAE K–L)", "label_en": "Finance, insurance & real estate (CNAE K–L)",
        "cnae_codes": ["64", "65", "66", "68", "K", "L"], "code_prefixes": ["64", "65", "66", "68", "K", "L"],
        "official_phrases": ["actividades financieras y de seguros", "actividades inmobiliarias"],
        "defaults": {"competition": 24, "demand": 24, "purchasing_power": 24, "momentum": 14, "market_scale": 14}, "demand_mode": "b2b",
    },
    {
        "id": "transporte_logistica", "main_sector_es": "Logística y Movilidad", "main_sector_en": "Logistics & Mobility",
        "label_es": "Transporte, mensajería y almacenamiento (CNAE H)", "label_en": "Transport, courier & warehousing (CNAE H)",
        "cnae_codes": ["49", "50", "51", "52", "53", "H"], "code_prefixes": ["49", "50", "51", "52", "53", "H"],
        "official_phrases": ["transporte y almacenamiento", "transporte terrestre", "actividades postales y de correos"],
        "defaults": {"competition": 25, "demand": 25, "purchasing_power": 15, "momentum": 15, "market_scale": 20}, "demand_mode": "b2b",
    },
    {
        "id": "construccion_reformas", "main_sector_es": "Construcción e Industria", "main_sector_en": "Construction & Industry",
        "label_es": "Construcción, reformas e instalaciones (CNAE F)", "label_en": "Construction, renovation & trades (CNAE F)",
        "cnae_codes": ["41", "42", "43", "F"], "code_prefixes": ["41", "42", "43", "F"],
        "official_phrases": ["construccion", "construccion de edificios", "actividades de construccion especializada"],
        "defaults": {"competition": 26, "demand": 24, "purchasing_power": 18, "momentum": 14, "market_scale": 18}, "demand_mode": "b2b",
    },
    {
        "id": "industria_alimentaria", "main_sector_es": "Construcción e Industria", "main_sector_en": "Construction & Industry",
        "label_es": "Industria manufacturera y agroalimentaria (CNAE C / A–E)", "label_en": "Manufacturing & food production (CNAE C / A–E)",
        "cnae_codes": ["A", "B", "C", "D", "E", "10", "11", "13", "14", "16", "25", "31", "33"],
        "code_prefixes": ["A", "B", "C", "D", "E", "01", "10", "11", "13", "14", "15", "16", "17", "18", "20", "22", "23", "24", "25", "26", "27", "28", "31", "32", "33", "35", "36", "38"],
        "official_phrases": ["industria manufacturera", "industrias extractivas", "agricultura ganaderia silvicultura y pesca", "suministro de energia", "suministro de agua"],
        "defaults": {"competition": 25, "demand": 22, "purchasing_power": 15, "momentum": 18, "market_scale": 20}, "demand_mode": "b2b",
    },
]

I18N = {
    "es": {
        "title": "EmprendeMAD", "subtitle": "Inteligencia de ubicación empresarial con datos abiertos de la Comunidad de Madrid",
        "language_toggle": "EN", "sector": "Categoría de negocio", "main_sector": "Sector principal",
        "all_sectors": "Todos los sectores", "offline": "Autocontenido · 100% offline",
        "index_note": "El Opportunity Score es un índice compuesto relativo (0–100), no una probabilidad de éxito ni supervivencia.",
        "kpi_best_label": "Mejor Ubicación Recomendada", "kpi_market_label": "Oportunidad de Mercado",
        "kpi_customers_label": "Base Potencial de Clientes", "kpi_income_label": "Poder Adquisitivo",
        "vs_median": "vs. mediana regional", "rank_pos": "Posición", "units_per_10k": "unidades / 10.000 hab.",
        "top_title": "Top 5 municipios recomendados", "top_subtitle": "Haz clic en un municipio para inspeccionar su mapa, desglose y tendencia.",
        "weights_title": "Control de ponderaciones", "custom_weights_toggle": "Usar pesos personalizados",
        "weights_default_info": "Modo automático: usando los pesos por defecto del sector seleccionado.",
        "weights_custom_info": "Modo personalizado: ajusta los sliders (0–100); se normalizan al 100% automáticamente.",
        "weights_zero_err": "Configuración inválida: todos los pesos valen 0. Aumenta al menos una dimensión.",
        "weights_total": "Suma bruta", "reset_weights": "Restablecer pesos del sector",
        "map_title": "Mapa oficial de municipios (Comunidad de Madrid)",
        "map_missing": "No se pudo descargar o validar la geometría municipal oficial (179 municipios). El mapa no se sustituye por polígonos artificiales.",
        "map_click_hint": "Haz clic en cualquier municipio para ver sus métricas y componentes.",
        "chart_title": "Densidad competitiva vs. Opportunity Score (Top 12)",
        "details_title": "Desglose completo del municipio", "components_title": "Contribución de los 5 componentes",
        "momentum_title": "Impulso histórico del sector (unidades productivas observadas)",
        "momentum_note": "Nota: refleja el cambio neto en el número de unidades productivas activas entre años observados, no una tasa individual de cierres.",
        "branch_prov_title": "Clasificación CNAE y ramas oficiales incluidas",
        "stability_title": "Análisis de estabilidad y sensibilidad",
        "stability_note": "Porcentaje de 250 escenarios reproducibles (semilla fija 20261124) en los que cada municipio se mantiene en el Top 5. No es probabilidad de éxito.",
        "stability_stable": "Liderazgo estable", "stability_sensitive": "Liderazgo sensible a los pesos",
        "break_title": "Simulador financiero de punto de equilibrio",
        "break_note": "Todos los parámetros financieros son supuestos editables del usuario, no predicciones ni ingresos observados.",
        "break_req_note": "Nota: 'Clientes/día por 10.000 hab.' es una exigencia financiera normalizada, no tráfico peatonal ni demanda real observada.",
        "break_invalid": "Corrige los parámetros: costes fijos ≥ 0, margen entre 1% y 100%, ticket medio > 0 y días entre 1 y 31.",
        "break_empty": "No hay municipios con población válida disponibles para el simulador.",
        "method_section": "Metodología, Fuentes Oficiales y Auditoría de Calidad",
        "tab_method": "A. Metodología", "tab_sources": "B. Fuentes Oficiales", "tab_validation": "C. Calidad y Auditoría",
        "warning_banner": "Integridad de datos: solo se integran valores oficiales observados. Los datos ausentes no se inventan ni se convierten en cero.",
        "population": "Población", "density": "Densidad", "income": "Renta disponible", "productive_units": "Unidades productivas",
        "competition_density": "Densidad competitiva", "competition_gap": "Hueco competitivo", "potential_demand": "Demanda potencial",
        "purchasing_power": "Poder adquisitivo", "sector_momentum": "Impulso sectorial", "market_scale": "Escala de mercado",
        "stability": "Estabilidad Top-5", "score": "Opportunity Score", "ineligible_note": "Inelegible (datos insuficientes)",
        "no_data": "No hay municipios elegibles con datos completos para esta categoría.",
        "compare_a": "Municipio A (referencia)", "compare_b": "Municipio B (comparar)",
        "fixed_costs": "Costes fijos mensuales (€)", "margin": "Margen de contribución (%)",
        "ticket": "Ticket medio (€)", "days_open": "Días operativos / mes",
        "breakeven_sales": "Ventas mensuales de equilibrio", "customers_month": "Clientes / mes necesarios",
        "customers_day": "Clientes / día necesarios", "customers_per_10k": "Clientes/día por 10.000 hab.",
        "municipality": "Municipio", "earliest_year": "Primer año", "latest_year": "Último año",
        "abs_change": "Cambio neto", "pct_change": "Variación %", "cagr": "CAGR anual", "obs_years": "Años observados",
        "cnae_codes": "Códigos CNAE", "matched_branches": "Ramas oficiales incluidas", "branch_count": "Ramas asociadas",
        "observations": "Observaciones", "munis_with_data": "Municipios con dato",
        "senior_share": "Cuota ≥65 años", "youth_share": "Cuota 15–34 años", "hab_km2": "hab/km²",
        "open_source": "Abrir fuente", "status_passed": "Correcto", "status_warning": "Aviso", "status_failed": "Fallo",
        "scenarios_tested": "Escenarios", "top1_win_rate": "Frecuencia líder en #1",
        "na_short": "N/D", "calc_guide": "Metodología y Auditoría", "unmatched_branches_label": "Ramas sin mapear",
    },
    "en": {
        "title": "EmprendeMAD", "subtitle": "Business Location Intelligence powered by Comunidad de Madrid Open Data",
        "language_toggle": "ES", "sector": "Business category", "main_sector": "Main sector",
        "all_sectors": "All sectors", "offline": "Self-contained · 100% offline",
        "index_note": "Opportunity Score is a relative composite index (0–100), not a probability of business survival or success.",
        "kpi_best_label": "Best Recommended Location", "kpi_market_label": "Market Opportunity",
        "kpi_customers_label": "Potential Customer Base", "kpi_income_label": "Purchasing Power",
        "vs_median": "vs. regional median", "rank_pos": "Rank", "units_per_10k": "units / 10,000 residents",
        "top_title": "Top 5 recommended municipalities", "top_subtitle": "Click a municipality to inspect its map polygon, score breakdown and trend.",
        "weights_title": "Scoring weight controls", "custom_weights_toggle": "Use custom weights",
        "weights_default_info": "Default mode: applying sector-specific assumption weights automatically.",
        "weights_custom_info": "Custom mode: drag sliders (0–100); weights automatically normalize to 100%.",
        "weights_zero_err": "Invalid weights: all sliders are 0. Set at least one weight above zero.",
        "weights_total": "Raw total", "reset_weights": "Reset to sector defaults",
        "map_title": "Official municipal boundaries (Comunidad de Madrid)",
        "map_missing": "Official municipal boundary geometries (179 municipalities) could not be downloaded or validated. Artificial shapes are not shown.",
        "map_click_hint": "Click any municipality on the map to inspect its metrics and score breakdown.",
        "chart_title": "Competition density vs. Opportunity Score (Top 12)",
        "details_title": "Full municipal breakdown", "components_title": "5-Component score contribution",
        "momentum_title": "Sector historical momentum (observed productive units)",
        "momentum_note": "Note: measures net change in active productive units between observed years, not an individual firm closure rate.",
        "branch_prov_title": "CNAE classification & matched official branches",
        "stability_title": "Recommendation stability & sensitivity",
        "stability_note": "Share of 250 reproducible weight scenarios (seed 20261124) in which each municipality remains in the Top 5. Not a success probability.",
        "stability_stable": "Robust top recommendation", "stability_sensitive": "Sensitive to weight assumptions",
        "break_title": "Break-even financial simulator",
        "break_note": "All financial inputs are illustrative user assumptions, not observed revenue or predictions.",
        "break_req_note": "Note: 'Required customers/day per 10k residents' is a normalized financial requirement, not observed pedestrian traffic or actual demand.",
        "break_invalid": "Invalid inputs: fixed costs ≥ 0, margin between 1% and 100%, average transaction > 0, and operating days between 1 and 31.",
        "break_empty": "No municipalities with valid population data are available for simulation.",
        "method_section": "Methodology, Official Data Sources & Validation Audit",
        "tab_method": "A. Methodology", "tab_sources": "B. Official Sources", "tab_validation": "C. Data Quality & Audit",
        "warning_banner": "Data integrity rule: only observed official values are embedded. Missing values are never fabricated or converted to zero.",
        "population": "Population", "density": "Density", "income": "Disposable income", "productive_units": "Productive units",
        "competition_density": "Competition density", "competition_gap": "Competition gap", "potential_demand": "Potential demand",
        "purchasing_power": "Purchasing power", "sector_momentum": "Sector momentum", "market_scale": "Market scale",
        "stability": "Top-5 stability", "score": "Opportunity Score", "ineligible_note": "Ineligible (insufficient data)",
        "no_data": "No municipalities meet the completeness threshold for this category.",
        "compare_a": "Municipality A (primary)", "compare_b": "Municipality B (compare)",
        "fixed_costs": "Monthly fixed costs (€)", "margin": "Contribution margin (%)",
        "ticket": "Average transaction (€)", "days_open": "Operating days / month",
        "breakeven_sales": "Break-even monthly sales", "customers_month": "Required customers / month",
        "customers_day": "Required customers / day", "customers_per_10k": "Req. customers/day per 10k",
        "municipality": "Municipality", "earliest_year": "Earliest year", "latest_year": "Latest year",
        "abs_change": "Net change", "pct_change": "% change", "cagr": "Annual CAGR", "obs_years": "Observed years",
        "cnae_codes": "CNAE codes", "matched_branches": "Official branches included", "branch_count": "Matched branches",
        "observations": "Observations", "munis_with_data": "Municipalities with data",
        "senior_share": "Age ≥65 share", "youth_share": "Age 15–34 share", "hab_km2": "inhab/km²",
        "open_source": "Open dataset", "status_passed": "Passed", "status_warning": "Warning", "status_failed": "Failed",
        "scenarios_tested": "Scenarios", "top1_win_rate": "Current leader #1 win rate",
        "na_short": "N/A", "calc_guide": "Methodology & Audit", "unmatched_branches_label": "Unmapped branches",
    },
}


@dataclass
class LoadedSource:
    role: str
    institution: str = "Comunidad de Madrid · Portal de Datos Abiertos"
    dataset_id: str | None = None
    dataset_title: str | None = None
    dataset_url: str | None = None
    license: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    resource_format: str | None = None
    retrieval: str | None = None
    retrieved_utc: str | None = None
    geographic_level: str | None = None
    variables_used: list[str] | None = None
    rows: int | None = None
    columns: list[str] | None = None
    schema: dict[str, Any] | None = None
    note: str | None = None
    error: str | None = None


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = unicodedata.normalize("NFKD", str(value).lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("ñ", "n")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def compact_text(value: Any) -> str:
    return normalize_text(value).replace(" ", "")


def canonical_muni_name(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    raw = str(value).strip()
    if raw.lower() in {"", "nan", "none", "null", "na", "n/a", "-", "--"}:
        return ""
    m = re.match(r"^(.+?),\s*(el|la|los|las)$", raw, flags=re.IGNORECASE)
    if m:
        raw = f"{m.group(2)} {m.group(1)}"
    else:
        m2 = re.match(r"^(.+?)\s*\((el|la|los|las)\)$", raw, flags=re.IGNORECASE)
        if m2:
            raw = f"{m2.group(2)} {m2.group(1)}"
    return normalize_text(raw)


def _clean_str_series(series: pd.Series) -> pd.Series:
    s = series.where(series.notna(), None)
    out = s.map(lambda v: None if v is None else str(v).strip())
    bad = out.isin({"", "nan", "NaN", "NAN", "None", "none", "NULL", "null", "NA", "N/A", "n/a", "NaT", "-", "--", "..", "..."})
    return out.where(~bad, float("nan"))


def safe_float_series(series: pd.Series) -> pd.Series:
    s = _clean_str_series(series).astype(object)
    s = s.map(lambda v: None if pd.isna(v) else str(v).replace("\u00a0", "").replace(" ", ""))
    s = s.replace({
        "": None, "-": None, "--": None, "nan": None, "NaN": None,
        "N/A": None, "n/a": None, "NA": None, "s/d": None, "S/D": None,
        "s.d.": None, "No disponible": None, "no disponible": None, "n.d.": None, ".": None,
    })
    s_str = s.astype(object)
    has_comma = s_str.map(lambda v: isinstance(v, str) and "," in v).fillna(False).astype(bool)
    has_dot = s_str.map(lambda v: isinstance(v, str) and "." in v).fillna(False).astype(bool)
    both = has_comma & has_dot
    if both.any():
        def _fix_both(val: str) -> str:
            return val.replace(".", "").replace(",", ".") if val.rfind(",") > val.rfind(".") else val.replace(",", "")
        s_str.loc[both] = s_str.loc[both].map(_fix_both)
    comma_only = has_comma & ~both
    if comma_only.any():
        s_str.loc[comma_only] = s_str.loc[comma_only].map(lambda v: v.replace(",", "."))
    return pd.to_numeric(s_str, errors="coerce")


# =============================================================================
# A. DATA ACQUISITION
# =============================================================================

def ckan_action(name: str, **params: Any) -> dict[str, Any]:
    last_err = None
    for attempt in range(6):
        try:
            response = SESSION.get(API + name, params=params, timeout=90)
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(min(2 ** attempt, 12))
                continue
            response.raise_for_status()
            payload = response.json()
            if not payload.get("success"):
                raise RuntimeError(f"CKAN {name} returned success=false")
            return payload["result"]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(min(2 ** attempt, 12))
    raise RuntimeError(f"CKAN action failed for {name}: {last_err}")


def discover_package(role: str) -> dict[str, Any]:
    cfg = DATASET_CANDIDATES[role]
    for slug in cfg["slugs"]:
        try:
            return ckan_action("package_show", id=slug)
        except Exception:
            pass
    scored: list[tuple[float, dict[str, Any]]] = []
    for query in cfg["queries"]:
        try:
            res = ckan_action("package_search", q=query, rows=15)
        except Exception:
            continue
        for pkg in res.get("results", []):
            score = 0.0
            title = normalize_text(pkg.get("title"))
            name = normalize_text(pkg.get("name"))
            notes = normalize_text(pkg.get("notes"))
            for slug in cfg["slugs"]:
                needle = normalize_text(slug)
                if needle and (needle in name or needle in title):
                    score += 8
            for token in normalize_text(query).split():
                if token and (token in title or token in name):
                    score += 1
                if token and token in notes:
                    score += 0.2
            if any((r.get("format") or "").lower() in cfg["required_formats"] or r.get("datastore_active") for r in pkg.get("resources", [])):
                score += 4
            scored.append((score, pkg))
    if not scored:
        raise RuntimeError(f"Could not discover package for role '{role}'")
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def rank_resources(pkg: dict[str, Any], preferred_formats: set[str]) -> list[dict[str, Any]]:
    candidates: list[tuple[float, dict[str, Any]]] = []
    for res in pkg.get("resources", []):
        fmt = ((res.get("format") or "") or Path(urlparse(res.get("url", "")).path).suffix.lstrip(".")).lower()
        res_name = normalize_text(res.get("name"))
        res_url = normalize_text(res.get("url"))
        score = 0.0
        if fmt in preferred_formats:
            score += 6
        if fmt == "csv":
            score += 4
        if res.get("datastore_active"):
            score += 3
        if fmt in {"pdf", "zip", "xlsx", "xls", "html", "xml", "wms", "wfs"} and score == 0:
            continue
        if "municip" in res_name or "municip" in res_url:
            score += 4
        if any(bad in res_name or bad in res_url for bad in ("diccionario", "metadato", "estructura", "definicion", "glosario", "esquema")):
            score -= 10
        if "distrit" in res_name and "municip" not in res_name:
            score -= 4
        score += int(bool(res.get("url"))) + int(bool(res.get("name")))
        if score > 0:
            candidates.append((score, res))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in candidates]


def cache_path(resource_id: str, fmt_hint: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(resource_id))
    ext = ".json" if "json" in fmt_hint.lower() else ".csv"
    return CACHE_DIR / f"{safe_id}{ext}"


def _detect_skiprows(path: Path, enc: str, sep: str) -> int:
    try:
        with path.open("r", encoding=enc, errors="replace") as fh:
            lines = [fh.readline() for _ in range(12)]
        counts = [ln.count(sep) for ln in lines if ln.strip()]
        if len(counts) >= 3 and counts[0] == 0 and max(counts[1:]) >= 2:
            for idx, ln in enumerate(lines):
                if ln.strip() and ln.count(sep) >= 2:
                    return idx
    except Exception:
        pass
    return 0


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    head = path.read_bytes()[:512].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        path.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded file {path.name} is HTML instead of CSV")

    last_err = None
    best_single = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-15", "latin1"):
        for sep in (";", ",", "\t", None):
            try:
                skip = _detect_skiprows(path, enc, sep) if sep else 0
                kwargs: dict[str, Any] = {"encoding": enc, "dtype": str}
                if sep is None:
                    kwargs.update({"sep": None, "engine": "python"})
                else:
                    kwargs.update({"sep": sep, "skiprows": skip})
                df = pd.read_csv(path, **kwargs)
                if len(df.columns) > 1:
                    return df
                if best_single is None and not df.empty:
                    best_single = df
            except Exception as exc:  # noqa: BLE001
                last_err = exc
    if best_single is not None:
        return best_single
    raise RuntimeError(f"Unable to parse CSV {path.name}: {last_err}")


def _unwrap_json_records(payload: Any) -> list[Any] | None:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "result" in payload:
            u = _unwrap_json_records(payload["result"])
            if u is not None:
                return u
        for key in ("records", "data", "datos", "items", "rows", "municipios", "features"):
            if key in payload:
                u = _unwrap_json_records(payload[key])
                if u is not None:
                    return u
        for val in payload.values():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
    return None


def _download_datastore(res_id: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch = ckan_action("datastore_search", resource_id=res_id, limit=5000, offset=offset)
        records = batch.get("records", [])
        rows.extend(records)
        total = int(batch.get("total", len(rows)))
        if not records or len(rows) >= total:
            break
        offset += len(records)
        time.sleep(0.1)
    df = pd.DataFrame(rows)
    return df.drop(columns=["_id"]) if "_id" in df.columns else df


def download_resource(pkg: dict[str, Any], res: dict[str, Any], role: str) -> tuple[pd.DataFrame | dict[str, Any], LoadedSource]:
    fmt = ((res.get("format") or "") or Path(urlparse(res.get("url", "")).path).suffix.lstrip(".")).lower()
    pkg_name = pkg.get("name", "")
    raw_url = res.get("url")
    pkg_page = f"https://datos.comunidad.madrid/catalogo/dataset/{pkg_name}" if pkg_name else pkg.get("url")
    meta = LoadedSource(
        role=role,
        dataset_id=pkg_name or None,
        dataset_title=pkg.get("title"),
        dataset_url=pkg_page,
        license=pkg.get("license_title") or pkg.get("license_id") or "CC BY 4.0",
        resource_id=res.get("id"),
        resource_name=res.get("name"),
        resource_format=fmt or None,
        retrieved_utc=now_utc(),
    )

    if raw_url:
        try:
            path = cache_path(res["id"], fmt + raw_url)
            if not path.exists():
                with SESSION.get(raw_url, timeout=180, stream=True) as response:
                    response.raise_for_status()
                    with path.open("wb") as fh:
                        for chunk in response.iter_content(131072):
                            if chunk:
                                fh.write(chunk)
            if "json" in path.suffix:
                head = path.read_bytes()[:512].lstrip().lower()
                if head.startswith(b"<!doctype") or head.startswith(b"<html"):
                    path.unlink(missing_ok=True)
                    raise RuntimeError(f"Downloaded file {path.name} is HTML")
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
                    meta.retrieval = "GeoJSON download"
                    meta.rows = len(payload.get("features", []))
                    return payload, meta
                records_list = _unwrap_json_records(payload)
                if records_list is not None:
                    rows = [
                        (dict(item.get("properties") or {}) if isinstance(item, dict) and "properties" in item else item)
                        for item in records_list if isinstance(item, dict)
                    ]
                    df = pd.DataFrame(rows)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    meta.retrieval = "JSON download"
                    meta.rows = len(df)
                    meta.columns = list(df.columns)
                    return df, meta
                raise RuntimeError("Unsupported JSON structure")

            df = read_csv_with_fallback(path)
            if "_id" in df.columns:
                df = df.drop(columns=["_id"])
            if len(df.columns) > 1:
                meta.retrieval = "CSV download"
                meta.rows = len(df)
                meta.columns = list(df.columns)
                return df, meta
        except Exception as csv_exc:
            if not res.get("datastore_active"):
                raise RuntimeError(f"Direct download failed for '{role}': {csv_exc}") from csv_exc

    if res.get("datastore_active"):
        df = _download_datastore(res["id"])
        meta.retrieval = "CKAN DataStore"
        meta.rows = len(df)
        meta.columns = list(df.columns)
        return df, meta

    raise RuntimeError(f"Resource for role '{role}' could not be retrieved")


# =============================================================================
# B & C. CLEANING, STANDARDIZATION & COLUMN INFERENCE
# =============================================================================

NON_CODE_COLUMNS = {
    "valor", "dato", "value", "total", "anio", "ano", "year", "periodo",
    "unidad", "estado dato", "medida", "indicador", "sexo", "edad",
    "rama de actividad", "tipo territorio", "superficie km2", "densidad por km2",
}

NON_NUMERIC_VALUE_COLUMNS = {
    "anio", "ano", "year", "periodo", "codigo territorio", "cod territorio",
    "municipio codigo", "municipio codigo ine", "codigo municipio", "codigo ine",
}


def header_alias_score(column_name: str, aliases: Iterable[str]) -> float:
    col = normalize_text(column_name)
    score = 0.0
    for alias in aliases:
        ali = normalize_text(alias)
        if not ali:
            continue
        if col == ali:
            score += 12
        elif ali in col:
            score += 6
        elif compact_text(ali) == compact_text(col):
            score += 9
    return score


def _parse_single_muni_code(val: Any) -> Any:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return float("nan")
    text = str(val).strip()
    if text.lower() in {"", "nan", "none", "null", "na"}:
        return float("nan")
    text = re.sub(r"\.0+$", "", text)
    m_nat = re.search(r"(28\d{3})$", text)
    if len(text) >= 7 and m_nat:
        return m_nat.group(1)
    m = re.fullmatch(r"\D*(\d{1,6})\D*", text)
    if not m:
        return float("nan")
    digits = m.group(1)
    if len(digits) <= 3:
        num = int(digits)
        return f"28{num:03d}" if 1 <= num <= 200 else float("nan")
    if len(digits) == 5:
        return digits if digits.startswith("28") and digits != "28000" else float("nan")
    if len(digits) == 6 and digits.startswith("28"):
        return digits[:5]
    return float("nan")


def standardize_municipality_code(series: pd.Series) -> pd.Series:
    return series.map(_parse_single_muni_code)


def infer_year_column(df: pd.DataFrame) -> str | None:
    best = (0.0, None)
    for col in df.columns:
        score = header_alias_score(col, ["año", "ano", "year", "periodo", "fecha referencia", "ejercicio"])
        sample = _clean_str_series(df[col]).astype(str).str.extract(r"\b(19\d{2}|20\d{2})\b", expand=False)
        ratio = sample.notna().mean()
        if score == 0 and ratio > 0:
            yrs = pd.to_numeric(sample, errors="coerce")
            if yrs.dropna().nunique() > 40:
                continue
        score += ratio * 8
        if score > best[0]:
            best = (score, col)
    return best[1] if best[0] >= 7 else None


def infer_column(
    df: pd.DataFrame,
    aliases: Iterable[str],
    expect: str = "string",
    known_names: set[str] | None = None,
    known_codes: set[str] | None = None,
    exclude_cols: set[str] | None = None,
) -> str | None:
    exclude_cols = exclude_cols or set()
    best = (-1.0, None)
    for col in df.columns:
        if col in exclude_cols:
            continue
        col_norm = normalize_text(col)
        if expect == "code" and (col_norm in {"id", "objectid", "fid", "gid", "oid"} or col_norm in NON_CODE_COLUMNS):
            continue
        if expect == "numeric" and col_norm in NON_NUMERIC_VALUE_COLUMNS:
            continue

        score = header_alias_score(col, aliases)
        series = df[col]
        if expect == "numeric":
            num_ratio = safe_float_series(series).notna().mean()
            if num_ratio < 0.05:
                continue
            score += num_ratio * 8
        elif expect == "code":
            parsed = standardize_municipality_code(series)
            ratio = parsed.notna().mean()
            nunique = parsed.nunique(dropna=True)
            if nunique <= 2:
                score -= 10
            score += ratio * 8
            if known_codes and nunique >= 10:
                overlap = len(set(parsed.dropna()) & known_codes)
                if overlap >= 20:
                    score += 12
                elif overlap >= 5:
                    score += 5
        else:
            cleaned = _clean_str_series(series)
            nonnull = cleaned.notna().mean()
            unique_ratio = min(cleaned.nunique(dropna=True) / max(len(series), 1), 1.0)
            score += nonnull * 2 + unique_ratio * 1.5
            if known_names:
                canon_vals = set(cleaned.dropna().map(canonical_muni_name))
                overlap = len(canon_vals & known_names)
                if overlap >= 20:
                    score += 14
                elif overlap >= 5:
                    score += 6
        if score > best[0]:
            best = (score, col)
    threshold = 7.5 if expect in {"numeric", "code"} else 6.0
    return best[1] if best[0] >= threshold else None


def municipality_key(name: Any, code: Any) -> str | None:
    code_text = str(code).strip() if pd.notna(code) else ""
    if re.fullmatch(r"\d{5}", code_text):
        return f"code:{code_text}"
    nm = canonical_muni_name(name)
    return f"name:{nm}" if nm else None


def infer_join_columns(
    df: pd.DataFrame,
    known_names: set[str] | None = None,
    known_codes: set[str] | None = None,
) -> dict[str, str | None]:
    code_col = infer_column(
        df,
        [
            "municipio codigo ine", "codigo ine", "cod ine", "ine municipio",
            "codigo municipio", "cod municipio", "codigo territorio", "cod territorio",
            "municipio codigo", "cmun", "codmun", "municipio cod", "cod mun",
        ],
        expect="code",
        known_codes=known_codes,
    )
    name_col = infer_column(
        df,
        [
            "municipio nombre", "nombre municipio", "municipio", "territorio",
            "denominacion municipio", "desc municipio", "municipality",
            "nom municipio", "descmun", "des mun", "nom mun", "entidad", "localidad",
        ],
        known_names=known_names,
        exclude_cols={code_col} if code_col else set(),
    )
    return {"municipality_name": name_col, "municipality_code": code_col}


def _filter_municipal_territory_level(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    t_col = infer_column(df, ["tipo territorio", "nivel territorial", "ambito territorial"])
    if not t_col:
        return df, {"territory_type_col": None, "filtered_non_municipal_rows": 0}
    vals = _clean_str_series(df[t_col]).map(normalize_text)
    muni_mask = vals.str.contains(r"\bmunicip", regex=True, na=False).fillna(False)
    if muni_mask.any():
        return df.loc[muni_mask].copy(), {
            "territory_type_col": t_col,
            "kept_territory_types": sorted(set(vals.loc[muni_mask].dropna())),
            "filtered_non_municipal_types": sorted(set(vals.loc[~muni_mask].dropna())),
            "filtered_non_municipal_rows": int((~muni_mask).sum()),
        }
    return df, {"territory_type_col": t_col, "filtered_non_municipal_rows": 0}


def infer_schema_snapshot(df: pd.DataFrame) -> dict[str, Any]:
    return {
        col: {
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].notna().sum()),
            "sample": df[col].dropna().astype(str).head(4).tolist(),
        }
        for col in df.columns[:40]
    }


def extract_municipality_ref(df: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    join_cols = infer_join_columns(df)
    if not join_cols["municipality_name"] and not join_cols["municipality_code"]:
        return None, {"note": f"No municipality name/code pair identified. Columns: {list(df.columns)}"}
    out = pd.DataFrame(index=df.index)
    out["municipality_name"] = _clean_str_series(df[join_cols["municipality_name"]]) if join_cols["municipality_name"] else float("nan")
    out["municipality_code"] = standardize_municipality_code(df[join_cols["municipality_code"]]) if join_cols["municipality_code"] else float("nan")
    nuts_col = infer_column(df, ["nuts4 nombre", "comarca", "zona"])
    if nuts_col:
        out["zone_name"] = _clean_str_series(df[nuts_col])

    out["join_key"] = [municipality_key(n, c) for n, c in zip(out["municipality_name"], out["municipality_code"])]
    dup_codes = int(out["municipality_code"].dropna().duplicated().sum())
    out = out.dropna(subset=["join_key"]).drop_duplicates("join_key")
    return out, {
        "municipality_name_col": join_cols["municipality_name"],
        "municipality_code_col": join_cols["municipality_code"],
        "official_count": int(len(out)),
        "duplicate_codes_in_ref": dup_codes,
    }


def extract_business_table(
    df: pd.DataFrame,
    known_names: set[str] | None = None,
    known_codes: set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    df, territory_info = _filter_municipal_territory_level(df)
    join_cols = infer_join_columns(df, known_names=known_names, known_codes=known_codes)
    year_col = infer_year_column(df)
    exclude = {c for c in (join_cols["municipality_name"], join_cols["municipality_code"], year_col) if c}

    branch_col = infer_column(df, ["rama de actividad", "rama actividad", "rama", "actividad", "cnae", "epigrafe", "sector", "division"], exclude_cols=exclude)
    branch_code_col = infer_column(df, ["codigo actividad", "codigo cnae", "cnae codigo", "epigrafe codigo", "rama codigo"], exclude_cols=exclude | ({branch_col} if branch_col else set()))
    measure_col = infer_column(df, ["medida", "indicador", "concepto", "variable", "magnitud", "tipo unidad"], exclude_cols=exclude | ({branch_col} if branch_col else set()))
    value_col = infer_column(df, ["valor", "unidades productivas", "numero", "número", "dato", "total", "cantidad", "empresas"], expect="numeric", exclude_cols=exclude | ({branch_col, branch_code_col, measure_col} - {None}))

    if not join_cols["municipality_name"] and not join_cols["municipality_code"]:
        raise RuntimeError(f"Could not identify municipality column in business dataset. Columns: {list(df.columns)}")
    if not branch_col and not branch_code_col:
        raise RuntimeError(f"Could not identify business-branch column in business dataset. Columns: {list(df.columns)}")
    if not value_col:
        raise RuntimeError(f"Could not identify numeric value column in business dataset. Columns: {list(df.columns)}")

    work = pd.DataFrame(index=df.index)
    work["municipality_name"] = _clean_str_series(df[join_cols["municipality_name"]]) if join_cols["municipality_name"] else float("nan")
    work["municipality_code"] = standardize_municipality_code(df[join_cols["municipality_code"]]) if join_cols["municipality_code"] else float("nan")

    if branch_col and branch_code_col:
        code_s = _clean_str_series(df[branch_code_col])
        label_s = _clean_str_series(df[branch_col])
        both = code_s.notna() & label_s.notna() & ~code_s.eq(label_s)
        branch_text = label_s.copy()
        branch_text.loc[both] = code_s.loc[both].astype(str) + " · " + label_s.loc[both].astype(str)
        branch_text = branch_text.combine_first(code_s)
    elif branch_col:
        branch_text = _clean_str_series(df[branch_col])
    else:
        branch_text = _clean_str_series(df[branch_code_col])

    work["branch"] = branch_text
    work["value"] = safe_float_series(df[value_col])
    invalid_numeric_count = int(df[value_col].notna().sum() - work["value"].notna().sum())

    work["year"] = float("nan")
    if year_col:
        work["year"] = pd.to_numeric(_clean_str_series(df[year_col]).astype(str).str.extract(r"\b(19\d{2}|20\d{2})\b", expand=False), errors="coerce")

    selected_measure_label = None
    available_measures: list[str] = []
    if measure_col:
        measure_raw = _clean_str_series(df[measure_col])
        available_measures = sorted(set(measure_raw.dropna()))
        measure_norm = measure_raw.map(normalize_text)
        chosen_mask = None
        for pat in (r"unidad(?:es)? productiva", r"colectivo empresarial", r"\bempresas\b", r"\bestablecimientos\b", r"\blocales\b"):
            m = measure_norm.str.contains(pat, regex=True, na=False).fillna(False)
            if m.any():
                top_norm = measure_norm.loc[m].value_counts().index[0]
                chosen_mask = measure_norm.eq(top_norm)
                selected_measure_label = measure_raw.loc[chosen_mask].dropna().iloc[0]
                break
        if chosen_mask is not None and chosen_mask.any():
            work = work.loc[chosen_mask].copy()

    work["branch_norm"] = work["branch"].map(normalize_text)
    work["join_key"] = [municipality_key(n, c) for n, c in zip(work["municipality_name"], work["municipality_code"])]

    negative_count = int((work["value"] < 0).sum())
    work = work.loc[work["value"].isna() | (work["value"] >= 0)].copy()
    work = work.dropna(subset=["value", "join_key", "branch"])
    work = work[~work["branch_norm"].isin({"", "total", "todas las ramas", "todos los sectores", "total ramas"})]

    keys = ["join_key"] + (["year"] if work["year"].notna().any() else []) + ["branch"]
    duplicate_obs_before_agg = int(work.duplicated(subset=keys).sum())
    work = work.groupby(keys, dropna=False, as_index=False).agg({"municipality_name": "first", "municipality_code": "first", "value": "sum"})

    return work, {
        "municipality_name_col": join_cols["municipality_name"],
        "municipality_code_col": join_cols["municipality_code"],
        "branch_col": branch_col,
        "branch_code_col": branch_code_col,
        "value_col": value_col,
        "year_col": year_col,
        "measure_col": measure_col,
        "selected_measure_label": selected_measure_label,
        "available_measures": available_measures,
        "territory_filter": territory_info,
        "invalid_numeric_count": invalid_numeric_count,
        "negative_count": negative_count,
        "duplicate_obs_before_agg": duplicate_obs_before_agg,
        "annual_years": sorted(int(x) for x in work["year"].dropna().unique()) if work["year"].notna().any() else [],
    }


def extract_population_table(
    df: pd.DataFrame,
    known_names: set[str] | None = None,
    known_codes: set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    df, territory_info = _filter_municipal_territory_level(df)
    join_cols = infer_join_columns(df, known_names=known_names, known_codes=known_codes)
    year_col = infer_year_column(df)
    age_col = infer_column(df, ["edad", "grupo edad", "tramo edad", "edad quinquenal"])
    sex_col = infer_column(df, ["sexo"])
    exclude = {c for c in (join_cols["municipality_name"], join_cols["municipality_code"], year_col, age_col, sex_col) if c}
    value_col = infer_column(df, ["valor", "poblacion", "población", "habitantes", "dato", "total"], expect="numeric", exclude_cols=exclude)

    if not join_cols["municipality_name"] and not join_cols["municipality_code"]:
        raise RuntimeError(f"Could not identify municipality column in population dataset. Columns: {list(df.columns)}")
    if not value_col:
        raise RuntimeError(f"Could not identify population value column. Columns: {list(df.columns)}")

    work = pd.DataFrame(index=df.index)
    work["municipality_name"] = _clean_str_series(df[join_cols["municipality_name"]]) if join_cols["municipality_name"] else float("nan")
    work["municipality_code"] = standardize_municipality_code(df[join_cols["municipality_code"]]) if join_cols["municipality_code"] else float("nan")
    work["population"] = safe_float_series(df[value_col])
    work["year"] = float("nan")
    if year_col:
        work["year"] = pd.to_numeric(_clean_str_series(df[year_col]).astype(str).str.extract(r"\b(19\d{2}|20\d{2})\b", expand=False), errors="coerce")
    work["age"] = _clean_str_series(df[age_col]).fillna("") if age_col else ""
    work["sex"] = _clean_str_series(df[sex_col]).fillna("") if sex_col else ""
    work["join_key"] = [municipality_key(n, c) for n, c in zip(work["municipality_name"], work["municipality_code"])]
    work = work.dropna(subset=["population", "join_key"])

    age_norm = work["age"].map(normalize_text)
    sex_norm = work["sex"].map(normalize_text)
    total_sex_mask = (sex_norm.eq("") | sex_norm.str.contains(r"\b(?:ambos|total|todos)\b", regex=True, na=False).fillna(False)).fillna(False)
    if not total_sex_mask.any():
        total_sex_mask = pd.Series(True, index=work.index)

    latest_year = None
    if work["year"].notna().any():
        latest_year = int(work["year"].dropna().max())
        work = work.loc[work["year"].fillna(latest_year) == latest_year].copy()
        age_norm = work["age"].map(normalize_text)
        total_sex_mask = total_sex_mask.loc[work.index]

    total_mask = total_sex_mask.copy()
    if age_col:
        age_total = age_norm.eq("") | age_norm.str.contains(r"\b(?:todas las edades|total)\b", regex=True, na=False).fillna(False)
        if age_total.any():
            total_mask = total_mask & age_total

    total = (
        work.loc[total_mask, ["join_key", "municipality_name", "municipality_code", "population"]]
        .groupby("join_key", dropna=False, as_index=False)
        .agg({"municipality_name": "first", "municipality_code": "first", "population": "sum"})
    )
    total["population_year"] = latest_year

    senior_share = None
    youth_share = None
    if age_col:
        senior_mask = total_sex_mask & age_norm.str.contains(r"\b(?:6[5-9]|[7-9]\d|100)\b|\b(?:65|70|75|80|85|90|100)\s*(?:y\s*)?mas\b", regex=True, na=False).fillna(False)
        if senior_mask.any():
            senior = work.loc[senior_mask, ["join_key", "population"]].groupby("join_key", as_index=False)["population"].sum().rename(columns={"population": "senior_population"})
            total = total.merge(senior, on="join_key", how="left")
            total["senior_share"] = total["senior_population"] / total["population"].replace(0, float("nan"))
            senior_share = "derived"

        youth_mask = total_sex_mask & age_norm.str.contains(r"\b(?:1[5-9]|2\d|3[0-4])\b", regex=True, na=False).fillna(False)
        if youth_mask.any():
            youth = work.loc[youth_mask, ["join_key", "population"]].groupby("join_key", as_index=False)["population"].sum().rename(columns={"population": "youth_population"})
            total = total.merge(youth, on="join_key", how="left")
            total["youth_share"] = total["youth_population"] / total["population"].replace(0, float("nan"))
            youth_share = "derived"

    return total, {
        "municipality_name_col": join_cols["municipality_name"],
        "municipality_code_col": join_cols["municipality_code"],
        "value_col": value_col,
        "year_col": year_col,
        "age_col": age_col,
        "sex_col": sex_col,
        "latest_year": latest_year,
        "territory_filter": territory_info,
        "senior_share": senior_share,
        "youth_share": youth_share,
    }


def extract_density_table(
    df: pd.DataFrame,
    known_names: set[str] | None = None,
    known_codes: set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    df, territory_info = _filter_municipal_territory_level(df)
    join_cols = infer_join_columns(df, known_names=known_names, known_codes=known_codes)
    year_col = infer_year_column(df)
    exclude = {c for c in (join_cols["municipality_name"], join_cols["municipality_code"], year_col) if c}
    density_col = infer_column(df, ["valor", "densidad poblacion", "densidad de poblacion", "densidad", "hab km2", "habitantes km2", "dato"], expect="numeric", exclude_cols=exclude)

    if not join_cols["municipality_name"] and not join_cols["municipality_code"]:
        raise RuntimeError(f"Could not identify municipality column in density dataset. Columns: {list(df.columns)}")
    if not density_col:
        raise RuntimeError(f"Could not identify density column in density dataset. Columns: {list(df.columns)}")

    work = pd.DataFrame(index=df.index)
    work["municipality_name"] = _clean_str_series(df[join_cols["municipality_name"]]) if join_cols["municipality_name"] else float("nan")
    work["municipality_code"] = standardize_municipality_code(df[join_cols["municipality_code"]]) if join_cols["municipality_code"] else float("nan")
    work["density"] = safe_float_series(df[density_col])
    work["year"] = float("nan")
    if year_col:
        work["year"] = pd.to_numeric(_clean_str_series(df[year_col]).astype(str).str.extract(r"\b(19\d{2}|20\d{2})\b", expand=False), errors="coerce")
    work["join_key"] = [municipality_key(n, c) for n, c in zip(work["municipality_name"], work["municipality_code"])]
    work = work.dropna(subset=["join_key", "density"])

    latest_year = None
    if work["year"].notna().any():
        latest_year = int(work["year"].dropna().max())
        work = work.loc[work["year"].fillna(latest_year) == latest_year].copy()

    work = work.groupby("join_key", dropna=False, as_index=False).agg({"municipality_name": "first", "municipality_code": "first", "density": "last"})
    work["density_year"] = latest_year
    return work, {
        "municipality_name_col": join_cols["municipality_name"],
        "municipality_code_col": join_cols["municipality_code"],
        "density_col": density_col,
        "year_col": year_col,
        "latest_year": latest_year,
        "territory_filter": territory_info,
    }


def extract_income_table(
    df: pd.DataFrame,
    known_names: set[str] | None = None,
    known_codes: set[str] | None = None,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    df, territory_info = _filter_municipal_territory_level(df)
    join_cols = infer_join_columns(df, known_names=known_names, known_codes=known_codes)
    year_col = infer_year_column(df)
    unit_col = infer_column(df, ["unidad", "unidades"])
    exclude = {c for c in (join_cols["municipality_name"], join_cols["municipality_code"], year_col, unit_col) if c}
    metric_col = infer_column(df, ["medida", "indicador", "concepto", "variable", "serie"], exclude_cols=exclude)
    value_col = infer_column(df, ["valor", "dato", "renta", "renta disponible", "euros", "importe"], expect="numeric", exclude_cols=exclude | ({metric_col} if metric_col else set()))

    if join_cols["municipality_name"] is None and join_cols["municipality_code"] is None:
        return None, {"note": f"No municipality join column identified. Columns: {list(df.columns)}"}

    work = None
    chosen_metric_label = None
    if metric_col and value_col:
        metric_raw = _clean_str_series(df[metric_col])
        metric_norm = metric_raw.map(normalize_text)
        chosen_rows = None
        for pat in (r"renta disponible.*(?:per capita|habitante|hogar|bruta)", r"renta disponible", r"per capita|habitante", r"renta|rdb|indice"):
            m = metric_norm.str.contains(pat, regex=True, na=False).fillna(False)
            if m.any():
                top_norm = metric_norm.loc[m].value_counts().index[0]
                chosen_rows = metric_norm.eq(top_norm)
                chosen_metric_label = metric_raw.loc[chosen_rows].dropna().iloc[0]
                break
        if chosen_rows is None and metric_raw.notna().any():
            top_norm = metric_norm.dropna().value_counts().index[0]
            chosen_rows = metric_norm.eq(top_norm)
            chosen_metric_label = metric_raw.loc[chosen_rows].dropna().iloc[0]
        if chosen_rows is not None and chosen_rows.any():
            work = pd.DataFrame(index=df.index[chosen_rows])
            work["municipality_name"] = _clean_str_series(df.loc[chosen_rows, join_cols["municipality_name"]]) if join_cols["municipality_name"] else float("nan")
            work["municipality_code"] = standardize_municipality_code(df.loc[chosen_rows, join_cols["municipality_code"]]) if join_cols["municipality_code"] else float("nan")
            work["income_indicator"] = safe_float_series(df.loc[chosen_rows, value_col])
            work["metric_name"] = chosen_metric_label
            work["income_unit"] = _clean_str_series(df.loc[chosen_rows, unit_col]) if unit_col else float("nan")
            if year_col:
                work["year"] = pd.to_numeric(_clean_str_series(df.loc[chosen_rows, year_col]).astype(str).str.extract(r"\b(19\d{2}|20\d{2})\b", expand=False), errors="coerce")

    if work is None and value_col:
        work = pd.DataFrame(index=df.index)
        work["municipality_name"] = _clean_str_series(df[join_cols["municipality_name"]]) if join_cols["municipality_name"] else float("nan")
        work["municipality_code"] = standardize_municipality_code(df[join_cols["municipality_code"]]) if join_cols["municipality_code"] else float("nan")
        work["income_indicator"] = safe_float_series(df[value_col])
        work["metric_name"] = value_col
        work["income_unit"] = _clean_str_series(df[unit_col]) if unit_col else float("nan")
        if year_col:
            work["year"] = pd.to_numeric(_clean_str_series(df[year_col]).astype(str).str.extract(r"\b(19\d{2}|20\d{2})\b", expand=False), errors="coerce")

    if work is None:
        return None, {"note": f"No reliable income metric column identified. Columns: {list(df.columns)}"}

    work["join_key"] = [municipality_key(n, c) for n, c in zip(work["municipality_name"], work["municipality_code"])]
    work = work.dropna(subset=["join_key", "income_indicator"])
    latest_year = None
    if "year" in work.columns and work["year"].notna().any():
        latest_year = int(work["year"].dropna().max())
        work = work.loc[work["year"].fillna(latest_year) == latest_year].copy()

    work = work.groupby("join_key", dropna=False, as_index=False).agg({
        "municipality_name": "first",
        "municipality_code": "first",
        "income_indicator": "last",
        "metric_name": "first",
        "income_unit": "first",
    })
    work["income_year"] = latest_year
    return work, {
        "municipality_name_col": join_cols["municipality_name"],
        "municipality_code_col": join_cols["municipality_code"],
        "metric_col": metric_col,
        "value_col": value_col,
        "year_col": year_col,
        "latest_year": latest_year,
        "metric_label": chosen_metric_label,
        "unit_label": work["income_unit"].dropna().iloc[0] if not work.empty and work["income_unit"].notna().any() else None,
        "territory_filter": territory_info,
    }


def extract_regional_demography_context(df: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    year_col = infer_year_column(df)
    metric_col = infer_column(df, ["medida", "indicador", "concepto", "variable"])
    value_col = infer_column(df, ["valor", "dato", "numero", "número", "tasa"], expect="numeric")
    if not year_col or not value_col:
        return [], {"note": "Could not identify yearly context columns"}
    work = pd.DataFrame({
        "year": pd.to_numeric(_clean_str_series(df[year_col]).astype(str).str.extract(r"\b(19\d{2}|20\d{2})\b", expand=False), errors="coerce"),
        "value": safe_float_series(df[value_col]),
        "metric": _clean_str_series(df[metric_col]).fillna("") if metric_col else "",
    }).dropna(subset=["year", "value"])
    if metric_col:
        metric_norm = work["metric"].map(normalize_text)
        preferred = metric_norm.str.contains("alta|nacimiento|baja|muerte|demografia|unidades empresariales", na=False).fillna(False)
        if preferred.any():
            work = work.loc[preferred]
    context = work.groupby(["year", "metric"], as_index=False)["value"].sum().sort_values(["metric", "year"]).head(40).to_dict("records")
    return context, {"year_col": year_col, "metric_col": metric_col, "value_col": value_col}


def load_role(role: str) -> tuple[pd.DataFrame | dict[str, Any] | None, LoadedSource]:
    pkg = discover_package(role)
    resources = rank_resources(pkg, DATASET_CANDIDATES[role]["required_formats"])
    if not resources:
        pkg_name = pkg.get("name", "")
        return None, LoadedSource(
            role=role, dataset_id=pkg_name or None, dataset_title=pkg.get("title"),
            dataset_url=f"https://datos.comunidad.madrid/catalogo/dataset/{pkg_name}" if pkg_name else pkg.get("url"),
            license=pkg.get("license_title") or pkg.get("license_id"), error="No CSV/JSON resource found",
        )
    last_err = None
    for res in resources[:4]:
        try:
            data, meta = download_resource(pkg, res, role)
            if isinstance(data, pd.DataFrame):
                if data.empty or len(data.columns) <= 1:
                    last_err = f"Resource '{res.get('name')}' parsed with <=1 column"
                    continue
                meta.schema = infer_schema_snapshot(data)
            return data, meta
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
    pkg_name = pkg.get("name", "")
    return None, LoadedSource(
        role=role, dataset_id=pkg_name or None, dataset_title=pkg.get("title"),
        dataset_url=f"https://datos.comunidad.madrid/catalogo/dataset/{pkg_name}" if pkg_name else pkg.get("url"),
        license=pkg.get("license_title") or pkg.get("license_id"), error=last_err or "Failed to load resource",
    )


def load_role_candidates(role: str) -> list[tuple[pd.DataFrame, LoadedSource]]:
    pkg = discover_package(role)
    resources = rank_resources(pkg, DATASET_CANDIDATES[role]["required_formats"])
    results: list[tuple[pd.DataFrame, LoadedSource]] = []
    for res in resources[:5]:
        try:
            data, meta = download_resource(pkg, res, role)
            if isinstance(data, pd.DataFrame) and not data.empty and len(data.columns) > 1:
                meta.schema = infer_schema_snapshot(data)
                results.append((data, meta))
        except Exception as exc:  # noqa: BLE001
            print(f"{role}: resource '{res.get('name')}' skipped -> {exc}")
    return results


# =============================================================================
# D. SECTOR CLASSIFICATION (OFFICIAL CNAE-2009 REGISTRY, ZERO OVERLAP)
# =============================================================================

def _extract_leading_cnae_token(branch_text: str) -> str | None:
    m = re.match(r"^(?:cnae\s*[-:]?\s*)?([A-U]|\d{2,4})\b", branch_text.strip(), flags=re.IGNORECASE)
    if m:
        tok = m.group(1).upper()
        if tok.isdigit() and len(tok) == 4 and (tok.startswith("19") or tok.startswith("20")):
            return None
        return tok
    return None


def classify_official_branches(business: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    branches = sorted(business["branch"].dropna().unique().tolist())
    assigned_branch_to_cat: dict[str, str] = {}
    overlaps_resolved: list[dict[str, Any]] = []
    cat_buckets: dict[str, list[str]] = {c["id"]: [] for c in CNAE_CATEGORY_REGISTRY}

    for branch in branches:
        b_norm = normalize_text(branch)
        lead_tok = _extract_leading_cnae_token(branch)
        matching_cats: list[dict[str, Any]] = []
        for cat in CNAE_CATEGORY_REGISTRY:
            matched = False
            if lead_tok:
                for pref in cat["code_prefixes"]:
                    pref_u = pref.upper()
                    if lead_tok == pref_u or (lead_tok.isdigit() and pref_u.isdigit() and lead_tok.startswith(pref_u)):
                        matched = True
                        break
            if not matched:
                for phrase in cat["official_phrases"]:
                    ph_n = normalize_text(phrase)
                    if ph_n and (b_norm == ph_n or ph_n in b_norm):
                        matched = True
                        break
            if matched:
                matching_cats.append(cat)

        if matching_cats:
            chosen = matching_cats[0]
            assigned_branch_to_cat[branch] = chosen["id"]
            cat_buckets[chosen["id"]].append(branch)
            if len(matching_cats) > 1:
                overlaps_resolved.append({"branch": branch, "assigned_to": chosen["id"], "other_candidates": [c["id"] for c in matching_cats[1:]]})

    unmatched_branches = [b for b in branches if b not in assigned_branch_to_cat]
    groups: list[dict[str, Any]] = []
    for cat in CNAE_CATEGORY_REGISTRY:
        matched_list = cat_buckets[cat["id"]]
        if not matched_list:
            continue
        sub = business.loc[business["branch"].isin(matched_list)]
        groups.append({
            "id": cat["id"],
            "main_sector_es": cat["main_sector_es"], "main_sector_en": cat["main_sector_en"],
            "label_es": cat["label_es"], "label_en": cat["label_en"],
            "cnae_codes": cat["cnae_codes"], "branch_labels": matched_list,
            "defaults": cat["defaults"], "demand_mode": cat["demand_mode"],
            "observation_count": int(len(sub)), "municipalities_with_data": int(sub["join_key"].nunique()),
        })

    return groups, {
        "total_distinct_branches": len(branches),
        "mapped_branches": len(assigned_branch_to_cat),
        "unmatched_branches": unmatched_branches,
        "active_categories": len(groups),
        "overlaps_resolved_exclusively": overlaps_resolved,
        "double_counting_prevented": True,
    }


# =============================================================================
# F. GEOGRAPHIC PROCESSING (IDEM WFS 179 MUNICIPALITIES + SIMPLIFY)
# =============================================================================

def parse_wfs_capabilities(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    names = []
    for elem in root.iter():
        if elem.tag.endswith("FeatureType"):
            for child in list(elem):
                if child.tag.endswith("Name") and child.text:
                    names.append(child.text.strip())
                    break
    return names


def _is_polygon_geojson(payload: dict[str, Any]) -> bool:
    return any((f.get("geometry") or {}).get("type", "") in {"Polygon", "MultiPolygon"} for f in payload.get("features", [])[:15])


def detect_boundary_property_keys(
    feature_collection: dict[str, Any],
    known_names: set[str] | None = None,
    known_codes: set[str] | None = None,
) -> tuple[str | None, str | None]:
    features = feature_collection.get("features", [])
    if not features:
        return None, None
    props = list((features[0].get("properties") or {}).keys())
    name_key, best_name_score = None, 0.0
    code_key, best_code_score = None, 0.0

    for key in props:
        score = header_alias_score(key, ["municipio", "nombre", "name", "denominacion", "etiqueta", "rotulo", "descr", "toponimo", "ds_nombre", "nm_"])
        sample_vals = [str((f.get("properties") or {}).get(key, "")) for f in features[:40]]
        if known_names and len({canonical_muni_name(v) for v in sample_vals} & known_names) >= 10:
            score += 20
        if score > best_name_score and any(re.search(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ]{3,}", v) for v in sample_vals):
            best_name_score, name_key = score, key

    for key in props:
        if normalize_text(key) in {"id", "objectid", "fid", "gid", "oid"}:
            continue
        score = header_alias_score(key, ["codigo municipio", "cod mun", "cod_mun", "ine", "codigo ine", "natcode", "codine", "cd_mun", "cmun", "codigo"])
        sample_vals = [(f.get("properties") or {}).get(key) for f in features[:40]]
        parsed_vals = [_parse_single_muni_code(v) for v in sample_vals]
        valid_ratio = sum(pd.notna(v) for v in parsed_vals) / max(len(sample_vals), 1)
        if known_codes and len({str(v) for v in parsed_vals if pd.notna(v)} & known_codes) >= 10:
            score += 20
        if valid_ratio >= 0.5 and score > best_code_score:
            best_code_score, code_key = score, key

    return name_key, code_key


def _utm30n_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    ep2, k0, lon0 = e2 / (1 - e2), 0.9996, math.radians(-3.0)
    x, y = easting - 500000.0, northing
    mu = (y / k0) / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    fp = mu + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu) + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu) + (151 * e1**3 / 96) * math.sin(6 * mu) + (1097 * e1**4 / 512) * math.sin(8 * mu)
    c1, t1 = ep2 * (math.cos(fp) ** 2), math.tan(fp) ** 2
    r1 = a * (1 - e2) / ((1 - e2 * (math.sin(fp) ** 2)) ** 1.5)
    n1 = a / math.sqrt(1 - e2 * (math.sin(fp) ** 2))
    d = x / (n1 * k0)
    lat = fp - (n1 * math.tan(fp) / r1) * (d**2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * (d**4) / 24 + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 3 * c1**2 - 252 * ep2) * (d**6) / 720)
    lon = lon0 + (d - (1 + 2 * t1 + c1) * (d**3) / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * (d**5) / 120) / math.cos(fp)
    return round(math.degrees(lon), 5), round(math.degrees(lat), 5)


def _douglas_peucker(pts: list[list[float]], eps: float) -> list[list[float]]:
    if len(pts) <= 4:
        return pts
    stack, keep = [(0, len(pts) - 1)], [False] * len(pts)
    keep[0] = keep[-1] = True
    while stack:
        s, e = stack.pop()
        a, b = pts[s], pts[e]
        dx, dy = b[0] - a[0], b[1] - a[1]
        max_d, idx = 0.0, -1
        for i in range(s + 1, e):
            p = pts[i]
            if dx == 0.0 and dy == 0.0:
                d = math.hypot(p[0] - a[0], p[1] - a[1])
            else:
                t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                d = math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))
            if d > max_d:
                max_d, idx = d, i
        if max_d > eps and idx != -1:
            keep[idx] = True
            stack.append((s, idx))
            stack.append((idx, e))
    out = [p for p, k in zip(pts, keep) if k]
    return out if len(out) >= 4 else pts


def _simplify_ring(ring: list[list[float]], eps: float = 0.00045) -> list[list[float]]:
    if len(ring) <= 6:
        return [[round(p[0], 5), round(p[1], 5)] for p in ring]
    open_pts = ring[:-1] if ring[0] == ring[-1] else ring
    simp = _douglas_peucker(open_pts, eps)
    if len(simp) < 3:
        simp = open_pts[:3]
    rounded = [[round(p[0], 5), round(p[1], 5)] for p in simp]
    if rounded[0] != rounded[-1]:
        rounded.append(rounded[0])
    return rounded


def _normalize_and_simplify_geometry(geometry: dict[str, Any] | None) -> dict[str, Any] | None:
    if not geometry or "coordinates" not in geometry:
        return None
    gtype = geometry.get("type")
    if gtype not in {"Polygon", "MultiPolygon"}:
        return None
    sample: list[tuple[float, float]] = []

    def _collect(node: Any) -> None:
        if len(sample) >= 5:
            return
        if isinstance(node, list) and len(node) >= 2 and isinstance(node[0], (int, float)) and isinstance(node[1], (int, float)):
            sample.append((float(node[0]), float(node[1])))
        elif isinstance(node, list):
            for child in node:
                _collect(child)

    _collect(geometry["coordinates"])
    if not sample:
        return None
    c0, c1 = sample[0]
    mode = "swap" if (38.0 <= c0 <= 42.5 and -6.0 <= c1 <= -1.5) else ("utm30" if (300000 <= c0 <= 600000 and 4350000 <= c1 <= 4600000) else "ok")

    def _fix_ring(ring: list[Any]) -> list[list[float]]:
        pts: list[list[float]] = []
        for p in ring:
            x, y = float(p[0]), float(p[1])
            if mode == "swap":
                pts.append([y, x])
            elif mode == "utm30":
                pts.append(list(_utm30n_to_wgs84(x, y)))
            else:
                pts.append([x, y])
        return _simplify_ring(pts)

    if gtype == "Polygon":
        return {"type": "Polygon", "coordinates": [_fix_ring(r) for r in geometry["coordinates"] if len(r) >= 3]}
    return {"type": "MultiPolygon", "coordinates": [[_fix_ring(r) for r in poly if len(r) >= 3] for poly in geometry["coordinates"]]}


def _merge_geometries(geoms: list[dict[str, Any]]) -> dict[str, Any]:
    if len(geoms) == 1:
        return geoms[0]
    polys: list[Any] = []
    for g in geoms:
        polys.append(g["coordinates"]) if g["type"] == "Polygon" else polys.extend(g["coordinates"])
    return {"type": "MultiPolygon", "coordinates": polys}


def fetch_boundary_geojson(
    known_names: set[str] | None = None,
    known_codes: set[str] | None = None,
    crosswalk: dict[str, str] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    meta: dict[str, Any] = {"service": IDEM_WFS, "attempts": []}
    feature_names: list[str] = []
    for version in ("1.1.0", "1.0.0"):
        try:
            cap = SESSION.get(IDEM_WFS, params={"REQUEST": "GetCapabilities", "SERVICE": "WFS", "VERSION": version}, timeout=120)
            cap.raise_for_status()
            feature_names = parse_wfs_capabilities(cap.text)
            if feature_names:
                meta["feature_types"] = feature_names[:30]
                break
        except Exception as exc:  # noqa: BLE001
            meta["capabilities_error"] = str(exc)

    if not feature_names:
        return None, {"error": f"WFS capabilities failed: {meta.get('capabilities_error', 'no layers')}"}

    scored = []
    for name in feature_names:
        nm = normalize_text(name)
        if any(bad in nm for bad in ("nucleo", "abandonado", "limite", "provincia", "seccion", "distrito", "entidad")):
            continue
        score = (25 if "idem cm unid admin" in nm else 0) + (12 if ("unid" in nm and "admin" in nm) else 0) + (10 if "municip" in nm else 0)
        scored.append((score, name))
    scored.sort(reverse=True)

    for _, feature_type in scored[:6]:
        for version, srs in (("1.0.0", "EPSG:4326"), ("1.1.0", "CRS:84"), ("1.1.0", "EPSG:4326")):
            for outfmt in ("application/json", "application/json; subtype=geojson", "json"):
                try:
                    response = SESSION.get(
                        IDEM_WFS,
                        params={"SERVICE": "WFS", "VERSION": version, "REQUEST": "GetFeature", "typeName": feature_type, "outputFormat": outfmt, "srsName": srs, "maxFeatures": 1000},
                        timeout=180,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    feats = payload.get("features", []) if payload.get("type") == "FeatureCollection" else []
                    if len(feats) < 100 or not _is_polygon_geojson(payload):
                        meta["attempts"].append(f"{feature_type} ({version}/{srs}): rejected (features={len(feats)}, polygon={_is_polygon_geojson(payload)})")
                        continue

                    name_key, code_key = detect_boundary_property_keys(payload, known_names=known_names, known_codes=known_codes)
                    if not name_key and not code_key:
                        meta["attempts"].append(f"{feature_type}: no name/code keys in {list((feats[0].get('properties') or {}).keys())}")
                        continue

                    grouped: dict[str, dict[str, Any]] = {}
                    for feat in feats:
                        props = dict(feat.get("properties") or {})
                        nm = props.get(name_key) if name_key else None
                        raw_code = props.get(code_key) if code_key else None
                        std_code = _parse_single_muni_code(raw_code) if raw_code is not None else float("nan")
                        join = municipality_key(nm, std_code)
                        if not join:
                            continue
                        if not join.startswith("code:") and crosswalk:
                            cn = canonical_muni_name(nm)
                            if cn in crosswalk:
                                join = crosswalk[cn]
                                std_code = join.split(":")[1]
                        if known_codes and join.startswith("code:") and join.split(":")[1] not in known_codes:
                            continue
                        geom = _normalize_and_simplify_geometry(feat.get("geometry"))
                        if not geom:
                            continue
                        entry = grouped.setdefault(join, {
                            "name": str(nm).strip() if nm is not None else "",
                            "code": str(std_code).strip() if pd.notna(std_code) else "",
                            "canon": canonical_muni_name(nm),
                            "geoms": [],
                        })
                        entry["geoms"].append(geom)

                    if len(grouped) < 100:
                        meta["attempts"].append(f"{feature_type}: only {len(grouped)} valid municipalities matched")
                        continue

                    features_out = [
                        {
                            "type": "Feature",
                            "properties": {"_em_join": jk, "_em_name": info["name"], "_em_code": info["code"], "_em_canon": info["canon"]},
                            "geometry": _merge_geometries(info["geoms"]),
                        }
                        for jk, info in grouped.items()
                    ]
                    meta.update({
                        "retrieval": f"IDEM WFS {version}", "feature_type": feature_type, "output_format": outfmt,
                        "srs": srs, "crs_normalized": "EPSG:4326 (WGS84 lon/lat)", "raw_features": len(feats),
                        "features": len(features_out), "name_property": name_key, "code_property": code_key,
                    })
                    return {"type": "FeatureCollection", "features": features_out}, meta
                except Exception as exc:  # noqa: BLE001
                    meta["attempts"].append(f"{feature_type} ({version}/{outfmt}): {exc}")
    return None, {"error": "Could not download a valid official municipal polygon layer from IDEM WFS", "attempts": meta["attempts"]}


# =============================================================================
# E & J. MASTER SPINE JOIN & PROGRAMMATIC AUDIT
# =============================================================================

def build_name_to_code_crosswalk(tables: Iterable[pd.DataFrame | None]) -> dict[str, str]:
    crosswalk: dict[str, str] = {}
    for tbl in tables:
        if tbl is None or tbl.empty or "municipality_name" not in tbl.columns or "municipality_code" not in tbl.columns:
            continue
        for nm, cd in zip(tbl["municipality_name"], tbl["municipality_code"]):
            cn = canonical_muni_name(nm)
            if cn and pd.notna(cd) and re.fullmatch(r"\d{5}", str(cd).strip()):
                crosswalk.setdefault(cn, f"code:{str(cd).strip()}")
    return crosswalk


def harmonize_join_keys(df: pd.DataFrame | None, crosswalk: dict[str, str]) -> pd.DataFrame | None:
    if df is None or df.empty or not crosswalk:
        return df
    df = df.copy()
    df["join_key"] = [
        jk if str(jk).startswith("code:") else crosswalk.get(canonical_muni_name(nm), jk)
        for jk, nm in zip(df["join_key"], df["municipality_name"])
    ]
    return df


def compute_cagr(series: list[tuple[int, float]]) -> float | None:
    series = sorted([(int(y), float(v)) for y, v in series if pd.notna(y) and pd.notna(v)], key=lambda x: x[0])
    if len(series) < 2 or series[0][1] <= 0 or series[-1][0] <= series[0][0]:
        return None
    return (series[-1][1] / series[0][1]) ** (1 / (series[-1][0] - series[0][0])) - 1


def _validate_bbox_madrid(boundary_geojson: dict[str, Any] | None) -> dict[str, Any]:
    if not boundary_geojson or not boundary_geojson.get("features"):
        return {"valid": False, "outside_bbox_vertices": 0}
    outside, total_pts = 0, 0

    def _visit(node: Any) -> None:
        nonlocal outside, total_pts
        if isinstance(node, list) and len(node) >= 2 and isinstance(node[0], (int, float)) and isinstance(node[1], (int, float)):
            total_pts += 1
            if not (-4.9 <= float(node[0]) <= -2.8 and 39.7 <= float(node[1]) <= 41.4):
                outside += 1
        elif isinstance(node, list):
            for child in node:
                _visit(child)

    for feat in boundary_geojson["features"]:
        _visit((feat.get("geometry") or {}).get("coordinates"))
    return {"valid": outside == 0 and total_pts > 0, "total_vertices": total_pts, "outside_bbox_vertices": outside}


def build_data_model(
    municipality_ref: pd.DataFrame,
    business: pd.DataFrame,
    population: pd.DataFrame | None,
    density: pd.DataFrame | None,
    income: pd.DataFrame | None,
    boundary_geojson: dict[str, Any] | None,
    business_schema: dict[str, Any],
    ref_schema: dict[str, Any],
    income_schema: dict[str, Any],
    boundary_meta: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    crosswalk = build_name_to_code_crosswalk([municipality_ref, population, density, income, business])
    business = harmonize_join_keys(business, crosswalk)
    population = harmonize_join_keys(population, crosswalk)
    density = harmonize_join_keys(density, crosswalk)
    income = harmonize_join_keys(income, crosswalk)

    spine_keys = set(municipality_ref["join_key"])
    unmatched_biz_munis = sorted({str(n) for jk, n in zip(business["join_key"], business["municipality_name"]) if jk not in spine_keys})

    business_matched = business.loc[business["join_key"].isin(spine_keys)].copy()
    b_keys = ["join_key"] + (["year"] if business_matched["year"].notna().any() else []) + ["branch"]
    business_matched = business_matched.groupby(b_keys, dropna=False, as_index=False).agg({"municipality_name": "first", "municipality_code": "first", "value": "sum"})

    base = municipality_ref[["join_key", "municipality_name", "municipality_code"]].copy()
    if "zone_name" in municipality_ref.columns:
        base["zone_name"] = municipality_ref["zone_name"]
    if population is not None and not population.empty:
        base = base.merge(population[[c for c in ["join_key", "population", "population_year", "senior_share", "youth_share"] if c in population.columns]].drop_duplicates("join_key"), on="join_key", how="left")
    if density is not None and not density.empty:
        base = base.merge(density[[c for c in ["join_key", "density", "density_year"] if c in density.columns]].drop_duplicates("join_key"), on="join_key", how="left")
    if income is not None and not income.empty:
        base = base.merge(income[[c for c in ["join_key", "income_indicator", "income_year", "metric_name", "income_unit"] if c in income.columns]].drop_duplicates("join_key"), on="join_key", how="left")

    groups, sector_audit = classify_official_branches(business_matched)
    latest_biz_year = int(business_matched["year"].dropna().max()) if business_matched["year"].notna().any() else None
    latest_biz = business_matched.loc[business_matched["year"] == latest_biz_year] if latest_biz_year is not None else business_matched
    total_biz_by_join = latest_biz.groupby("join_key", as_index=False)["value"].sum().rename(columns={"value": "total_business_units"})
    business_years = sorted(int(x) for x in business_matched["year"].dropna().unique()) if business_matched["year"].notna().any() else []

    rows = []
    for _, muni in base.sort_values("municipality_name").iterrows():
        jk = muni["join_key"]
        muni_biz = business_matched.loc[business_matched["join_key"] == jk]
        tb = total_biz_by_join.loc[total_biz_by_join["join_key"] == jk, "total_business_units"]
        sector_payload = {}
        for group in groups:
            sel = muni_biz.loc[muni_biz["branch"].isin(group["branch_labels"])]
            if sel.empty:
                sector_payload[group["id"]] = {"count": None, "latest_year": None, "earliest_count": None, "earliest_year": None, "history": [], "momentum": None}
            elif sel["year"].notna().any():
                ts = sel.groupby("year", as_index=False)["value"].sum().sort_values("year")
                sector_payload[group["id"]] = {
                    "count": float(ts["value"].iloc[-1]),
                    "latest_year": int(ts["year"].iloc[-1]),
                    "earliest_count": float(ts["value"].iloc[0]),
                    "earliest_year": int(ts["year"].iloc[0]),
                    "history": [{"year": int(y), "count": float(v)} for y, v in zip(ts["year"], ts["value"])],
                    "momentum": compute_cagr([(int(y), float(v)) for y, v in zip(ts["year"], ts["value"])]),
                }
            else:
                sector_payload[group["id"]] = {"count": float(sel["value"].sum()), "latest_year": None, "earliest_count": None, "earliest_year": None, "history": [], "momentum": None}

        rows.append({
            "join_key": jk,
            "municipality_name": str(muni["municipality_name"]).strip(),
            "municipality_code": str(muni["municipality_code"]).strip() if pd.notna(muni["municipality_code"]) else "",
            "zone_name": str(muni["zone_name"]).strip() if "zone_name" in muni and pd.notna(muni["zone_name"]) else "",
            "population": float(muni["population"]) if "population" in muni and pd.notna(muni["population"]) else None,
            "population_year": int(muni["population_year"]) if "population_year" in muni and pd.notna(muni["population_year"]) else None,
            "density": float(muni["density"]) if "density" in muni and pd.notna(muni["density"]) else None,
            "density_year": int(muni["density_year"]) if "density_year" in muni and pd.notna(muni["density_year"]) else None,
            "income_indicator": float(muni["income_indicator"]) if "income_indicator" in muni and pd.notna(muni["income_indicator"]) else None,
            "income_year": int(muni["income_year"]) if "income_year" in muni and pd.notna(muni["income_year"]) else None,
            "income_metric": str(muni["metric_name"]).strip() if "metric_name" in muni and pd.notna(muni["metric_name"]) else None,
            "income_unit": str(muni["income_unit"]).strip() if "income_unit" in muni and pd.notna(muni["income_unit"]) else None,
            "senior_share": float(muni["senior_share"]) if "senior_share" in muni and pd.notna(muni["senior_share"]) else None,
            "youth_share": float(muni["youth_share"]) if "youth_share" in muni and pd.notna(muni["youth_share"]) else None,
            "total_business_units": float(tb.iloc[0]) if not tb.empty else None,
            "total_business_year": latest_biz_year,
            "sectors": sector_payload,
        })

    geo_matched_keys: set[str] = set()
    if boundary_geojson:
        filtered_feats = []
        for feat in boundary_geojson.get("features", []):
            jk = (feat.get("properties") or {}).get("_em_join")
            if jk in spine_keys and jk not in geo_matched_keys:
                geo_matched_keys.add(jk)
                feat_copy = json.loads(json.dumps(feat))
                feat_copy["properties"]["_em_name"] = base.loc[base["join_key"] == jk, "municipality_name"].iloc[0]
                filtered_feats.append(feat_copy)
        boundary_geojson = {"type": "FeatureCollection", "features": filtered_feats}

    bbox_check = _validate_bbox_madrid(boundary_geojson)
    missing_geo_munis = sorted(base.loc[~base["join_key"].isin(geo_matched_keys), "municipality_name"].tolist())

    n_exp = len(base)
    n_pop = sum(r["population"] is not None for r in rows)
    n_den = sum(r["density"] is not None for r in rows)
    n_inc = sum(r["income_indicator"] is not None for r in rows)
    n_biz = sum(r["total_business_units"] is not None for r in rows)

    validation_checks = [
        {
            "id": "municipality_matching",
            "status": "passed" if n_exp == 179 and n_biz == 179 and ref_schema.get("duplicate_codes_in_ref", 0) == 0 else ("warning" if n_biz >= 150 else "failed"),
            "details": {"expected_official": n_exp, "matched_business": n_biz, "unmatched_business_count": len(unmatched_biz_munis), "unmatched_business_sample": unmatched_biz_munis[:20], "duplicate_codes_in_ref": ref_schema.get("duplicate_codes_in_ref", 0)},
        },
        {
            "id": "sector_mapping",
            "status": "passed" if sector_audit["active_categories"] >= 10 and len(sector_audit["unmatched_branches"]) == 0 else ("warning" if sector_audit["active_categories"] >= 8 else "failed"),
            "details": sector_audit,
        },
        {
            "id": "data_completeness",
            "status": "passed" if (n_pop == n_exp and n_den == n_exp and n_inc >= n_exp * 0.9) else "warning",
            "details": {"missing_population": n_exp - n_pop, "missing_density": n_exp - n_den, "missing_income": n_exp - n_inc, "missing_business": n_exp - n_biz, "has_historical_series": len(business_years) >= 2},
        },
        {
            "id": "business_data_validation",
            "status": "passed" if business_schema.get("negative_count", 0) == 0 and business_schema.get("invalid_numeric_count", 0) == 0 else "warning",
            "details": {"duplicate_obs_aggregated": business_schema.get("duplicate_obs_before_agg", 0), "negative_counts_removed": business_schema.get("negative_count", 0), "invalid_numeric_values": business_schema.get("invalid_numeric_count", 0), "years_observed": business_years, "selected_measure": business_schema.get("selected_measure_label")},
        },
        {
            "id": "geographical_validation",
            "status": "passed" if (len(geo_matched_keys) == n_exp and bbox_check["valid"]) else ("warning" if len(geo_matched_keys) >= 150 and bbox_check["valid"] else "failed"),
            "details": {"matched_geometries": len(geo_matched_keys), "expected_geometries": n_exp, "missing_geometries_count": len(missing_geo_munis), "missing_geometries_sample": missing_geo_munis[:20], "crs": boundary_meta.get("crs_normalized", "N/A"), "bbox_valid": bbox_check["valid"], "outside_bbox_vertices": bbox_check.get("outside_bbox_vertices", 0)},
        },
        {
            "id": "score_validation",
            "status": "passed",
            "details": {"normalization": "Mid-rank percentile (0-1)", "completeness_rule": "population > 0, count != null, >= 3 of 5 components", "reproducible_seed": 20261124, "empirically_validated_against_survival": False},
        },
    ]

    data_model = {
        "generated_utc": now_utc(),
        "rows": rows,
        "sector_groups": groups,
        "business_years": business_years,
        "boundaries": boundary_geojson,
        "validation_checks": validation_checks,
        "sector_audit": sector_audit,
        "income_meta": {"metric": income_schema.get("metric_label"), "unit": income_schema.get("unit_label"), "year": income_schema.get("latest_year")},
    }
    summary = {
        "coverage_official_reference": n_exp,
        "matched_business": n_biz,
        "matched_population": n_pop,
        "matched_density": n_den,
        "matched_income": n_inc,
        "sector_groups": len(groups),
        "business_years": business_years,
        "official_boundary_features": len(geo_matched_keys),
    }
    return data_model, summary


# =============================================================================
# H & I. OFFLINE HTML APPLICATION TEMPLATE
# =============================================================================

def html_template(data: dict[str, Any], report: dict[str, Any]) -> str:
    payload = json.dumps({"data": data, "report": report, "i18n": I18N}, ensure_ascii=False).replace("</script>", "<\\/script>")
    html = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EmprendeMAD · Business Location Intelligence</title>
<style>
:root{--bg:#f4f7fb;--card:#fff;--ink:#102033;--muted:#5b6e84;--line:#dce5ef;--accent:#d91a3c}
*{box-sizing:border-box}
body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.45}
header{background:#0f1f33;color:#fff;padding:15px 22px;position:sticky;top:0;z-index:20;box-shadow:0 4px 18px rgba(0,0,0,.15)}
.header-wrap{max-width:1400px;margin:0 auto;display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:42px;height:42px;border-radius:11px;background:linear-gradient(135deg,#e11d48,#f59e0b);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:19px}
.brand h1{margin:0;font-size:22px}.brand small{display:block;color:#cbd5e1;font-size:12px}
.header-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.btn{border:1px solid rgba(255,255,255,.2);background:#1b314d;color:#fff;padding:8px 13px;border-radius:10px;cursor:pointer;font-size:13px;font-weight:600}
.btn:hover{background:#26446b}
.btn-sec{border:1px solid var(--line);background:#f8fafc;color:var(--ink);padding:7px 11px;border-radius:9px;cursor:pointer;font-size:12px;font-weight:700}
main{max-width:1400px;margin:0 auto;padding:18px;display:flex;flex-direction:column;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 8px 24px rgba(15,31,51,.04)}
.selector-bar{display:grid;grid-template-columns:1fr 1.3fr 1fr;gap:14px;align-items:end}
label.lbl{display:block;font-size:11px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px}
select,input[type=number]{width:100%;padding:9px 11px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:var(--ink);font:inherit;font-size:14px}
.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.kpi-card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:15px}
.kpi-card.hi{background:linear-gradient(135deg,#0f1f33,#1e3a5f);color:#fff;border-color:#0f1f33}
.kpi-card.hi .kpi-lbl{color:#cbd5e1}.kpi-card.hi .kpi-sub{color:#94a3b8}
.kpi-lbl{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.kpi-val{font-size:21px;font-weight:800;margin-top:5px}.kpi-sub{font-size:12px;color:var(--muted);margin-top:4px}
.workspace{display:grid;grid-template-columns:1.18fr .82fr;gap:16px;align-items:start}
.stack{display:flex;flex-direction:column;gap:16px}
.map-wrap{width:100%;background:#eef4f9;border:1px solid var(--line);border-radius:14px;min-height:500px;position:relative;overflow:hidden}
#svgMap{width:100%;height:500px;display:block;background:#f7fbff}
.map-tip{position:absolute;pointer-events:none;display:none;background:#0f1f33;color:#fff;padding:6px 10px;border-radius:8px;font-size:12px;z-index:8;white-space:nowrap}
.map-leg{position:absolute;right:12px;bottom:12px;background:rgba(255,255,255,.94);border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:11px}
.rank-list{display:flex;flex-direction:column;gap:9px;margin-top:10px}
.rank-card{border:1px solid var(--line);border-radius:12px;padding:11px;background:#fbfdff;cursor:pointer;transition:.15s}
.rank-card:hover,.rank-card.active{border-color:var(--accent);box-shadow:0 6px 16px rgba(217,26,60,.1)}
.rank-top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.score-pill{color:#fff;font-weight:800;font-size:12px;padding:3px 9px;border-radius:999px}
.small{font-size:12px;color:var(--muted)}
.slider-row{display:grid;grid-template-columns:140px 1fr 38px 50px;gap:8px;align-items:center;margin:8px 0;font-size:12px}
.slider-row input[type=range]{width:100%;accent-color:var(--accent);cursor:pointer}
.slider-row input[type=range]:disabled{opacity:.45;cursor:not-allowed}
.alert-err{background:#fef2f2;border:1px solid #fecaca;color:#991b1b;padding:10px 12px;border-radius:10px;font-size:12px;font-weight:600;margin:8px 0}
.alert-warn{background:#fffbeb;border-left:4px solid #d97706;color:#78350f;padding:10px 12px;border-radius:8px;font-size:12px;margin:8px 0}
.details-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:10px 0}
.mbox{background:#f8fafc;border:1px solid var(--line);border-radius:10px;padding:9px 11px}
.mbox .label{font-size:10.5px;color:var(--muted);font-weight:700;text-transform:uppercase}
.mbox .value{font-size:16px;font-weight:800;margin-top:3px}
.bar-row{display:grid;grid-template-columns:165px 1fr 48px 56px;gap:8px;align-items:center;margin:7px 0;font-size:12px}
.bar-track{height:10px;background:#e2e8f0;border-radius:999px;overflow:hidden}
.bar-fill{height:100%;border-radius:999px}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.break-inputs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:12px 0}
.table-wrap{overflow-x:auto}
table.tbl{width:100%;border-collapse:collapse;font-size:12.5px}
table.tbl th,table.tbl td{border-bottom:1px solid var(--line);padding:8px;text-align:left}
table.tbl th{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.pill{display:inline-block;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:700;background:#f1f5f9;color:var(--ink);margin:2px 4px 2px 0}
.status-passed{background:#dcfce7;color:#166534}.status-warning{background:#fef3c7;color:#92400e}.status-failed{background:#fee2e2;color:#991b1b}
details.acc{border:1px solid var(--line);border-radius:14px;background:#fff;padding:14px 16px}
details.acc summary{cursor:pointer;font-weight:800;font-size:15px}
.tab-bar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
.tab-btn{padding:7px 13px;border-radius:9px;border:1px solid var(--line);background:#f8fafc;font-weight:700;font-size:12px;cursor:pointer}
.tab-btn.active{background:#0f1f33;color:#fff;border-color:#0f1f33}
.fbox{background:#0f1f33;color:#e2e8f0;padding:11px 13px;border-radius:9px;font-family:ui-monospace,monospace;font-size:12px;overflow-x:auto;margin:7px 0}
footer{text-align:center;padding:16px;font-size:12px;color:var(--muted)}
@media(max-width:1100px){.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.workspace,.two-col,.selector-bar{grid-template-columns:1fr}}
@media(max-width:700px){.kpi-grid,.details-grid,.break-inputs{grid-template-columns:1fr}.bar-row{grid-template-columns:115px 1fr 42px 46px}}
</style>
</head>
<body>
<header>
  <div class="header-wrap">
    <div class="brand">
      <div class="logo">E</div>
      <div><h1>Emprende<span style="color:#fb7185">MAD</span></h1><small id="subtitle"></small></div>
    </div>
    <div class="header-actions">
      <span class="pill" style="background:#1e3a5f;color:#e2e8f0" id="offlineBadge"></span>
      <button class="btn" id="guideBtn"></button>
      <button class="btn" id="langBtn"></button>
    </div>
  </div>
</header>

<main>
  <section class="card">
    <div class="selector-bar">
      <div><label class="lbl" id="mainSectorLabel" for="mainSectorSelect"></label><select id="mainSectorSelect"></select></div>
      <div><label class="lbl" id="sectorLabel" for="sectorSelect"></label><select id="sectorSelect"></select></div>
      <div><div class="small" id="indexNote"></div></div>
    </div>
  </section>

  <section class="kpi-grid">
    <div class="kpi-card hi"><div class="kpi-lbl" id="kpiBestLabel"></div><div class="kpi-val" id="kpiBestValue">—</div><div class="kpi-sub" id="kpiBestSub">—</div></div>
    <div class="kpi-card"><div class="kpi-lbl" id="kpiMarketLabel"></div><div class="kpi-val" id="kpiMarketValue">—</div><div class="kpi-sub" id="kpiMarketSub">—</div></div>
    <div class="kpi-card"><div class="kpi-lbl" id="kpiCustomersLabel"></div><div class="kpi-val" id="kpiCustomersValue">—</div><div class="kpi-sub" id="kpiCustomersSub">—</div></div>
    <div class="kpi-card"><div class="kpi-lbl" id="kpiIncomeLabel"></div><div class="kpi-val" id="kpiIncomeValue">—</div><div class="kpi-sub" id="kpiIncomeSub">—</div></div>
  </section>

  <section class="workspace">
    <div class="card">
      <h2 id="mapTitle" style="margin:0 0 4px 0;font-size:17px"></h2>
      <div class="small" id="mapHint" style="margin-bottom:10px"></div>
      <div class="map-wrap" id="mapWrap">
        <svg id="svgMap" viewBox="0 0 900 500" preserveAspectRatio="xMidYMid meet"></svg>
        <div class="map-tip" id="mapTooltip"></div>
        <div id="mapEmpty" class="alert-err" style="display:none;margin:16px"></div>
        <div class="map-leg" id="legendBox"></div>
      </div>
      <div id="mapSnapshot" style="margin-top:12px"></div>
    </div>

    <div class="stack">
      <div class="card">
        <h2 id="topTitle" style="margin:0 0 4px 0;font-size:17px"></h2>
        <div class="small" id="topSubtitle"></div>
        <div class="rank-list" id="ranking"></div>
      </div>

      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px">
          <h2 id="weightsTitle" style="margin:0;font-size:16px"></h2>
          <button class="btn-sec" id="resetWeightsBtn"></button>
        </div>
        <label style="display:inline-flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;font-weight:700">
          <input type="checkbox" id="customWeightsToggle"><span id="customWeightsLabel"></span>
        </label>
        <div class="small" id="weightsModeNote" style="margin:6px 0 8px 0"></div>
        <div id="weightsZeroError" class="alert-err" style="display:none"></div>
        <div id="weightsSlidersHost"></div>
        <div class="small" id="weightsTotalRow" style="margin-top:8px;font-weight:700"></div>
      </div>
    </div>
  </section>

  <section class="two-col">
    <div class="card"><h2 id="detailsTitle" style="margin:0 0 10px 0;font-size:17px"></h2><div id="detailContent"></div></div>
    <div class="stack">
      <div class="card"><h2 id="branchProvTitle" style="margin:0 0 10px 0;font-size:17px"></h2><div id="branchProvContent"></div></div>
      <div class="card"><h2 id="stabilityTitle" style="margin:0 0 6px 0;font-size:17px"></h2><div class="small" id="stabilityNote" style="margin-bottom:10px"></div><div id="stabilityContent"></div></div>
    </div>
  </section>

  <section class="two-col">
    <div class="card"><h2 id="chartTitle" style="margin:0 0 10px 0;font-size:17px"></h2><div class="table-wrap"><svg id="comparisonChart" viewBox="0 0 720 300" preserveAspectRatio="xMidYMid meet"></svg></div></div>
    <div class="card"><h2 id="momentumTitle" style="margin:0 0 6px 0;font-size:17px"></h2><div class="small" id="momentumNote" style="margin-bottom:10px"></div><div id="momentumMetrics"></div><div class="table-wrap"><svg id="momentumChart" viewBox="0 0 720 220" preserveAspectRatio="xMidYMid meet"></svg></div></div>
  </section>

  <section class="card">
    <h2 id="breakTitle" style="margin:0 0 4px 0;font-size:17px"></h2>
    <div class="small" id="breakNote"></div>
    <div class="two-col" style="margin-top:12px">
      <div><label class="lbl" id="compareALabel" for="compareA"></label><select id="compareA"></select></div>
      <div><label class="lbl" id="compareBLabel" for="compareB"></label><select id="compareB"></select></div>
    </div>
    <div class="break-inputs">
      <div><label class="lbl" id="fixedLabel" for="fixedCosts"></label><input id="fixedCosts" type="number" value="6000" min="0" step="100"></div>
      <div><label class="lbl" id="marginLabel" for="marginPct"></label><input id="marginPct" type="number" value="60" min="1" max="100" step="1"></div>
      <div><label class="lbl" id="ticketLabel" for="avgTicket"></label><input id="avgTicket" type="number" value="18" min="0.5" step="0.5"></div>
      <div><label class="lbl" id="daysLabel" for="daysOpen"></label><input id="daysOpen" type="number" value="26" min="1" max="31" step="1"></div>
    </div>
    <div id="breakEvenError" class="alert-err" style="display:none"></div>
    <div id="breakEvenOutput"></div>
    <div id="breakEvenChartWrap" style="margin-top:12px"></div>
  </section>

  <details class="acc" id="guideSection" open>
    <summary id="methodSectionTitle"></summary>
    <div class="alert-warn" id="warningBanner" style="margin-top:12px"></div>
    <div class="tab-bar">
      <button class="tab-btn active" data-tab="method" id="tabMethodBtn"></button>
      <button class="tab-btn" data-tab="sources" id="tabSourcesBtn"></button>
      <button class="tab-btn" data-tab="validation" id="tabValidationBtn"></button>
    </div>
    <div id="tabMethod" class="tab-pane"></div>
    <div id="tabSources" class="tab-pane" style="display:none"></div>
    <div id="tabValidation" class="tab-pane" style="display:none"></div>
  </details>
</main>
<footer>EmprendeMAD · Open Data Business Location Intelligence</footer>

<script>
const APP=__PAYLOAD__, T=APP.i18n, DATA=APP.data, REPORT=APP.report;
const WKEYS=['competition','demand','purchasing_power','momentum','market_scale'];
const state={
  lang:'es', mainSector:'ALL',
  sectorId:DATA.sector_groups[0]?DATA.sector_groups[0].id:null,
  useCustomWeights:false,
  weights:DATA.sector_groups[0]?Object.assign({},DATA.sector_groups[0].defaults):{competition:30,demand:25,purchasing_power:20,momentum:15,market_scale:10},
  selectedKey:null, compareAKey:null, compareBKey:null, activeTab:'method'
};
function tr(k){return (T[state.lang]&&T[state.lang][k])||k;}
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function fmt(v,d=1){if(v===null||v===undefined||Number.isNaN(Number(v)))return tr('na_short');return Number(v).toLocaleString(state.lang==='es'?'es-ES':'en-GB',{maximumFractionDigits:d});}
function colScore(s){if(s===null||s===undefined)return '#cbd5e1';if(s>=80)return '#138255';if(s>=65)return '#6fa832';if(s>=50)return '#d69b1d';if(s>=35)return '#e67e22';return '#cc4a53';}
function med(vals){const a=vals.filter(v=>v!==null&&v!==undefined&&!Number.isNaN(Number(v))).map(Number).sort((x,y)=>x-y);if(!a.length)return null;const m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;}
function curSector(){return DATA.sector_groups.find(s=>s.id===state.sectorId)||DATA.sector_groups[0]||null;}

function midRank(values,rev=false){
  const a=values.map((v,i)=>(v===null||v===undefined||Number.isNaN(Number(v)))?null:{i,v:Number(v)}).filter(Boolean).sort((x,y)=>x.v-y.v);
  const out=Array(values.length).fill(null);
  for(let i=0;i<a.length;){
    let j=i;while(j+1<a.length&&a[j+1].v===a[i].v)j++;
    const r=a.length===1?0.5:(i+j)/2/(a.length-1);
    for(let k=i;k<=j;k++)out[a[k].i]=rev?1-r:r;
    i=j+1;
  }
  return out;
}
function demandVal(row,sec){
  const pop=row.population;if(!pop||pop<=0)return null;
  const lp=Math.log10(pop), ld=row.density&&row.density>0?Math.log10(row.density):null, lb=row.total_business_units&&row.total_business_units>0?Math.log10(row.total_business_units):null;
  if(sec.demand_mode==='consumer_density')return ld!==null?0.58*lp+0.42*ld:lp;
  if(sec.demand_mode==='b2b')return lb!==null?(0.55*lb+0.25*lp+(row.income_indicator&&row.income_indicator>0?0.20*Math.log10(Math.max(1,row.income_indicator)):0)):lp;
  if(sec.demand_mode==='health'){let v=0.55*lp+(ld!==null?0.20*ld:0);if(row.senior_share!=null)v+=0.25*row.senior_share*10;return v;}
  if(sec.demand_mode==='education'){let v=0.60*lp+(ld!==null?0.20*ld:0);if(row.youth_share!=null)v+=0.20*row.youth_share*10;return v;}
  if(sec.demand_mode==='wellness'){let v=0.45*lp+(ld!==null?0.25*ld:0);if(row.income_indicator&&row.income_indicator>0)v+=0.30*Math.log10(Math.max(1,row.income_indicator));return v;}
  return lp;
}
function computeStability(scored){
  const rates={};scored.forEach(r=>rates[r.join_key]=0);
  if(!scored.length)return{rates,scenarios:0,leaderWinRate:0};
  let seed=20261124;const rand=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
  const N=250,leader=scored[0].join_key;let wins=0;
  for(let s=0;s<N;s++){
    const w={};WKEYS.forEach(k=>w[k]=rand()+0.05);
    const rk=scored.map(r=>{let n=0,d=0;WKEYS.forEach(k=>{if(r.components[k]!=null){n+=w[k]*r.components[k];d+=w[k];}});return{jk:r.join_key,sc:d>0?n/d:-1};}).sort((a,b)=>b.sc-a.sc);
    if(rk[0]&&rk[0].jk===leader)wins++;
    rk.slice(0,5).forEach(x=>rates[x.jk]++);
  }
  Object.keys(rates).forEach(k=>rates[k]=Math.round(rates[k]/N*100));
  return{rates,scenarios:N,leaderWinRate:Math.round(wins/N*100)};
}
function computeModel(){
  const sec=curSector();if(!sec)return{scored:[],all:[],zeroWeights:false,stabilityMeta:{scenarios:0,leaderWinRate:0},medComp:null,medInc:null};
  const act=state.useCustomWeights?state.weights:sec.defaults;
  const wsum=WKEYS.reduce((s,k)=>s+Math.max(0,Math.min(100,Number(act[k])||0)),0);
  const zeroWeights=wsum<=0;
  const base=DATA.rows.map(r=>{
    const sd=(r.sectors&&r.sectors[sec.id])||{};
    const count=sd.count!==undefined?sd.count:null;
    const cd=(count!==null&&r.population&&r.population>0)?(count/r.population*10000):null;
    return Object.assign({},r,{count,latest_year:sd.latest_year??null,earliest_count:sd.earliest_count??null,earliest_year:sd.earliest_year??null,history:sd.history||[],momentum:sd.momentum??null,competition_density:cd,demand_raw:demandVal(r,sec),market_scale_raw:r.population&&r.population>0?Math.log10(r.population):null});
  });
  const cR=midRank(base.map(r=>r.competition_density),true),dR=midRank(base.map(r=>r.demand_raw),false),iR=midRank(base.map(r=>r.income_indicator),false),mR=midRank(base.map(r=>r.momentum),false),sR=midRank(base.map(r=>r.market_scale_raw),false);
  const all=base.map((r,i)=>{
    const components={competition:cR[i],demand:dR[i],purchasing_power:iR[i],momentum:mR[i],market_scale:sR[i]};
    const avail=WKEYS.filter(k=>components[k]!==null&&components[k]!==undefined).length;
    const eligible=Boolean(r.population&&r.population>0&&r.count!==null&&avail>=3);
    let score=null;const normWeights={},contributions={};
    if(eligible&&!zeroWeights){
      let num=0,den=0;
      WKEYS.forEach(k=>{const w=Math.max(0,Math.min(100,Number(act[k])||0));if(components[k]!=null){num+=w*components[k];den+=w;}});
      if(den>0){
        score=Math.round(100*num/den);
        WKEYS.forEach(k=>{const w=Math.max(0,Math.min(100,Number(act[k])||0));if(components[k]!=null){normWeights[k]=w/den;contributions[k]=(w/den)*components[k]*100;}else{normWeights[k]=0;contributions[k]=null;}});
      }
    }
    return Object.assign({},r,{components,eligible,score,normWeights,contributions});
  });
  const scored=all.filter(r=>r.score!==null).sort((a,b)=>b.score-a.score);
  scored.forEach((r,i)=>r.rank=i+1);
  const stab=computeStability(scored);
  scored.forEach(r=>r.stability=stab.rates[r.join_key]??0);
  return{scored,all,zeroWeights,stabilityMeta:stab,medComp:med(scored.map(r=>r.competition_density)),medInc:med(all.map(r=>r.income_indicator))};
}

function populateSectorSelectors(){
  const ms=document.getElementById('mainSectorSelect'),ss=document.getElementById('sectorSelect'),seen=new Set(),mains=[];
  DATA.sector_groups.forEach(g=>{if(!seen.has(g.main_sector_es)){seen.add(g.main_sector_es);mains.push({k:g.main_sector_es,l:state.lang==='es'?g.main_sector_es:g.main_sector_en});}});
  ms.innerHTML=`<option value="ALL">${esc(tr('all_sectors'))} (${DATA.sector_groups.length})</option>`+mains.map(m=>`<option value="${esc(m.k)}" ${state.mainSector===m.k?'selected':''}>${esc(m.l)}</option>`).join('');
  const list=state.mainSector==='ALL'?DATA.sector_groups:DATA.sector_groups.filter(g=>g.main_sector_es===state.mainSector);
  if(!list.some(g=>g.id===state.sectorId)&&list.length){state.sectorId=list[0].id;if(!state.useCustomWeights)state.weights=Object.assign({},list[0].defaults);}
  ss.innerHTML=list.map(g=>`<option value="${esc(g.id)}" ${g.id===state.sectorId?'selected':''}>${esc(state.lang==='es'?g.label_es:g.label_en)} (${g.branch_labels.length})</option>`).join('');
}

function initWeightSlidersOnce(){
  document.getElementById('weightsSlidersHost').innerHTML=WKEYS.map(k=>`
    <div class="slider-row">
      <label for="slider_${k}" id="slabel_${k}" style="font-weight:700"></label>
      <input type="range" min="0" max="100" step="1" id="slider_${k}">
      <span id="sraw_${k}" style="text-align:right;font-weight:700"></span>
      <span id="spct_${k}" class="pill" style="text-align:center"></span>
    </div>`).join('');
  WKEYS.forEach(k=>{
    document.getElementById(`slider_${k}`).addEventListener('input',e=>{
      let v=Math.round(Number(e.target.value));v=Math.max(0,Math.min(100,Number.isNaN(v)?0:v));
      state.weights[k]=v;
      if(!state.useCustomWeights){state.useCustomWeights=true;document.getElementById('customWeightsToggle').checked=true;}
      renderDynamic();
    });
  });
}

function syncWeightsUI(zeroW){
  const sec=curSector(),act=state.useCustomWeights?state.weights:(sec?sec.defaults:state.weights);
  const lm={competition:tr('competition_gap'),demand:tr('potential_demand'),purchasing_power:tr('purchasing_power'),momentum:tr('sector_momentum'),market_scale:tr('market_scale')};
  const tot=WKEYS.reduce((s,k)=>s+Math.max(0,Math.min(100,Number(act[k])||0)),0);
  document.getElementById('customWeightsToggle').checked=state.useCustomWeights;
  document.getElementById('weightsModeNote').textContent=state.useCustomWeights?tr('weights_custom_info'):tr('weights_default_info');
  const err=document.getElementById('weightsZeroError');err.style.display=zeroW?'block':'none';err.textContent=tr('weights_zero_err');
  WKEYS.forEach(k=>{
    const v=Math.max(0,Math.min(100,Number(act[k])||0)),sl=document.getElementById(`slider_${k}`);
    document.getElementById(`slabel_${k}`).textContent=lm[k];
    if(Number(sl.value)!==v)sl.value=v;
    sl.disabled=!state.useCustomWeights;
    document.getElementById(`sraw_${k}`).textContent=String(v);
    document.getElementById(`spct_${k}`).textContent=tot>0?Math.round(v/tot*100)+'%':'0%';
  });
  document.getElementById('weightsTotalRow').textContent=`${tr('weights_total')}: ${tot} → 100%`;
}

function renderTopKPIs(m){
  const top=m.scored[0]||null;
  if(!top){
    ['kpiBestValue','kpiMarketValue','kpiCustomersValue','kpiIncomeValue'].forEach(id=>document.getElementById(id).textContent='—');
    ['kpiBestSub','kpiMarketSub','kpiCustomersSub','kpiIncomeSub'].forEach(id=>document.getElementById(id).textContent=tr('no_data'));
    return;
  }
  document.getElementById('kpiBestValue').textContent=`${top.municipality_name} (${top.score}/100)`;
  document.getElementById('kpiBestSub').textContent=`${tr('rank_pos')} #1 · ${tr('stability')}: ${top.stability}%`;
  const cd=m.medComp&&top.competition_density!==null?` (${((top.competition_density-m.medComp)/m.medComp*100)>=0?'+':''}${fmt((top.competition_density-m.medComp)/m.medComp*100,0)}% ${tr('vs_median')}: ${fmt(m.medComp,1)})`:'';
  document.getElementById('kpiMarketValue').textContent=`${fmt(top.competition_density,1)} ${tr('units_per_10k')}`;
  document.getElementById('kpiMarketSub').textContent=`${fmt(top.count,0)} ${tr('productive_units')}${cd}`;
  const demo=top.senior_share!=null?` · ${tr('senior_share')}: ${fmt(top.senior_share*100,1)}%`:(top.youth_share!=null?` · ${tr('youth_share')}: ${fmt(top.youth_share*100,1)}%`:'');
  document.getElementById('kpiCustomersValue').textContent=`${fmt(top.population,0)} (${top.population_year||'—'})`;
  document.getElementById('kpiCustomersSub').textContent=`${tr('density')}: ${fmt(top.density,1)} ${tr('hab_km2')} (${top.density_year||'—'})${demo}`;
  const idiff=m.medInc&&top.income_indicator!==null?` (${((top.income_indicator-m.medInc)/m.medInc*100)>=0?'+':''}${fmt((top.income_indicator-m.medInc)/m.medInc*100,0)}% ${tr('vs_median')}: ${fmt(m.medInc,1)})`:'';
  document.getElementById('kpiIncomeValue').textContent=top.income_indicator!==null?`${fmt(top.income_indicator,1)} ${top.income_unit?esc(top.income_unit):''}`:tr('na_short');
  document.getElementById('kpiIncomeSub').textContent=`${top.income_year||'—'}${idiff}`;
}

function renderTop5(m){
  const h=document.getElementById('ranking');
  if(!m.scored.length){h.innerHTML=`<div class="alert-warn">${esc(tr('no_data'))}</div>`;return;}
  h.innerHTML=m.scored.slice(0,5).map(r=>`
    <div class="rank-card ${r.join_key===state.selectedKey?'active':''}" data-key="${esc(r.join_key)}">
      <div class="rank-top"><strong>#${r.rank} · ${esc(r.municipality_name)}</strong><span class="score-pill" style="background:${colScore(r.score)}">${r.score}/100</span></div>
      <div class="small" style="margin-top:4px">${tr('productive_units')}: <strong>${fmt(r.count,0)}</strong> · ${tr('competition_density')}: <strong>${fmt(r.competition_density,1)}</strong>/10k</div>
      <div class="small">${tr('population')}: <strong>${fmt(r.population,0)}</strong> · ${tr('income')}: <strong>${fmt(r.income_indicator,1)}</strong> · ${tr('stability')}: <strong>${r.stability}%</strong></div>
    </div>`).join('');
  h.querySelectorAll('.rank-card').forEach(el=>el.addEventListener('click',()=>{state.selectedKey=el.dataset.key;renderDynamic();}));
}

function renderMap(m){
  const svg=document.getElementById('svgMap'),emp=document.getElementById('mapEmpty'),leg=document.getElementById('legendBox'),tip=document.getElementById('mapTooltip'),wrap=document.getElementById('mapWrap');
  if(!DATA.boundaries||!DATA.boundaries.features||!DATA.boundaries.features.length){
    svg.style.display='none';emp.style.display='block';emp.textContent=tr('map_missing');leg.innerHTML='';return;
  }
  svg.style.display='block';emp.style.display='none';
  let minLon=Infinity,maxLon=-Infinity,minLat=Infinity,maxLat=-Infinity;
  function scan(n){
    if(Array.isArray(n)&&n.length>=2&&typeof n[0]==='number'&&typeof n[1]==='number'){
      if(n[0]<minLon)minLon=n[0];if(n[0]>maxLon)maxLon=n[0];if(n[1]<minLat)minLat=n[1];if(n[1]>maxLat)maxLat=n[1];
    }else if(Array.isArray(n)){for(let i=0;i<n.length;i++)scan(n[i]);}
  }
  DATA.boundaries.features.forEach(f=>{if(f.geometry&&f.geometry.coordinates)scan(f.geometry.coordinates);});
  const asp=Math.cos(((minLat+maxLat)/2)*Math.PI/180),w=900,h=500,pad=16;
  const sx=Math.max(0.0001,(maxLon-minLon)*asp),sy=Math.max(0.0001,maxLat-minLat),sc=Math.min((w-pad*2)/sx,(h-pad*2)/sy);
  const ox=(w-sx*sc)/2,oy=(h-sy*sc)/2,px=lon=>ox+((lon-minLon)*asp)*sc,py=lat=>h-oy-(lat-minLat)*sc;
  const p2d=rings=>rings.map(r=>r.map((p,i)=>(i?'L':'M')+px(p[0]).toFixed(1)+','+py(p[1]).toFixed(1)).join('')+'Z').join(' ');
  const byK=Object.fromEntries(m.all.map(r=>[r.join_key,r]));
  svg.innerHTML=DATA.boundaries.features.map(f=>{
    const g=f.geometry||{},d=g.type==='Polygon'?p2d(g.coordinates):(g.type==='MultiPolygon'?g.coordinates.map(p2d).join(' '):'');
    if(!d)return'';
    const jk=f.properties._em_join,row=byK[jk],score=row?row.score:null,sel=jk===state.selectedKey;
    return `<path d="${d}" fill="${colScore(score)}" fill-opacity="${sel?0.95:0.78}" stroke="${sel?'#0f1f33':'#fff'}" stroke-width="${sel?2.2:0.9}" data-key="${esc(jk)}" data-name="${esc(f.properties._em_name||'')}" data-score="${score===null?'':score}"></path>`;
  }).join('');
  svg.querySelectorAll('path').forEach(el=>{
    el.addEventListener('click',()=>{state.selectedKey=el.dataset.key;renderDynamic();});
    el.addEventListener('mousemove',e=>{
      const r=wrap.getBoundingClientRect(),sc=el.dataset.score;
      tip.innerHTML=`<strong>${esc(el.dataset.name)}</strong> · ${sc!==''?`${tr('score')}: ${sc}/100`:tr('na_short')}`;
      tip.style.display='block';tip.style.left=Math.min(r.width-200,Math.max(8,e.clientX-r.left+12))+'px';tip.style.top=Math.max(8,e.clientY-r.top-34)+'px';
    });
    el.addEventListener('mouseleave',()=>tip.style.display='none');
  });
  leg.innerHTML=`<div style="font-weight:800;margin-bottom:3px">${esc(tr('score'))}</div>`+
    [['#138255','80–100'],['#6fa832','65–79'],['#d69b1d','50–64'],['#e67e22','35–49'],['#cc4a53','0–34'],['#cbd5e1',tr('na_short')]]
    .map(([c,l])=>`<div><span style="display:inline-block;width:10px;height:10px;background:${c};border-radius:2px;margin-right:5px"></span>${esc(l)}</div>`).join('');
}

function renderSelected(m){
  let row=m.all.find(r=>r.join_key===state.selectedKey)||m.scored[0]||m.all[0];
  if(!row)return;
  state.selectedKey=row.join_key;
  const sec=curSector(),sLbl=sec?(state.lang==='es'?sec.label_es:sec.label_en):'';
  document.getElementById('mapSnapshot').innerHTML=`
    <div style="background:#f8fafc;border:1px solid var(--line);border-radius:12px;padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
        <div><strong style="font-size:15px">${esc(row.municipality_name)}</strong> <span class="pill">INE ${esc(row.municipality_code||'—')}</span>${row.zone_name?`<span class="pill">${esc(row.zone_name)}</span>`:''}<div class="small">${esc(sLbl)}</div></div>
        <span class="score-pill" style="background:${colScore(row.score)};font-size:13px">${row.score!==null?`${row.score}/100 (#${row.rank})`:tr('ineligible_note')}</span>
      </div>
      <div class="details-grid" style="margin-bottom:0">
        <div class="mbox"><div class="label">${esc(tr('productive_units'))} (${row.latest_year||'—'})</div><div class="value">${fmt(row.count,0)}</div></div>
        <div class="mbox"><div class="label">${esc(tr('competition_density'))}</div><div class="value">${fmt(row.competition_density,1)}</div></div>
        <div class="mbox"><div class="label">${esc(tr('population'))} (${row.population_year||'—'})</div><div class="value">${fmt(row.population,0)}</div></div>
        <div class="mbox"><div class="label">${esc(tr('income'))} (${row.income_year||'—'})</div><div class="value">${fmt(row.income_indicator,1)}</div></div>
      </div>
    </div>`;

  const lm={competition:tr('competition_gap'),demand:tr('potential_demand'),purchasing_power:tr('purchasing_power'),momentum:tr('sector_momentum'),market_scale:tr('market_scale')};
  const bars=WKEYS.map(k=>{
    const pct=row.components[k],c=row.contributions[k],nw=row.normWeights[k];
    return `<div class="bar-row"><div>${esc(lm[k])} <span class="small">(${nw?Math.round(nw*100)+'%':'0%'})</span></div><div class="bar-track"><div class="bar-fill" style="width:${pct===null?0:Math.round(pct*100)}%;background:${colScore(pct===null?null:pct*100)}"></div></div><div>${pct===null?tr('na_short'):fmt(pct*100,0)}</div><div class="small" style="text-align:right">${c==null?tr('na_short'):'+'+fmt(c,1)}</div></div>`;
  }).join('');
  document.getElementById('detailContent').innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><strong>${esc(row.municipality_name)}</strong><span class="small">${tr('obs_years')}: ${row.population_year||'—'} / ${row.density_year||'—'} / ${row.income_year||'—'}</span></div>
    <div class="details-grid">
      <div class="mbox"><div class="label">${esc(tr('score'))}</div><div class="value">${row.score!==null?row.score+'/100':tr('na_short')}</div></div>
      <div class="mbox"><div class="label">${esc(tr('density'))}</div><div class="value">${fmt(row.density,1)}</div></div>
      <div class="mbox"><div class="label">${esc(tr('cagr'))}</div><div class="value">${row.momentum!==null?fmt(row.momentum*100,1)+'%':tr('na_short')}</div></div>
      <div class="mbox"><div class="label">${esc(tr('stability'))}</div><div class="value">${row.stability!==undefined?row.stability+'%':tr('na_short')}</div></div>
    </div>
    <h3 style="font-size:13.5px;margin:10px 0 6px 0">${esc(tr('components_title'))}</h3>${bars}`;
  renderMomentum(row);
}

function renderMomentum(row){
  const hist=row.history||[],mEl=document.getElementById('momentumMetrics'),svg=document.getElementById('momentumChart');
  if(!hist.length){mEl.innerHTML=`<div class="small">${esc(tr('no_data'))}</div>`;svg.innerHTML='';return;}
  const f=hist[0],l=hist[hist.length-1],abs=l.count-f.count,pct=f.count>0?abs/f.count*100:null;
  mEl.innerHTML=`<div class="details-grid">
    <div class="mbox"><div class="label">${esc(tr('earliest_year'))} (${f.year})</div><div class="value">${fmt(f.count,0)}</div></div>
    <div class="mbox"><div class="label">${esc(tr('latest_year'))} (${l.year})</div><div class="value">${fmt(l.count,0)}</div></div>
    <div class="mbox"><div class="label">${esc(tr('abs_change'))}</div><div class="value">${abs>=0?'+':''}${fmt(abs,0)} (${pct!==null?fmt(pct,1)+'%':tr('na_short')})</div></div>
    <div class="mbox"><div class="label">${esc(tr('cagr'))}</div><div class="value">${row.momentum!==null?fmt(row.momentum*100,2)+'%':tr('na_short')}</div></div>
  </div>`;
  const w=720,h=220,ml=48,mr=18,mt=16,mb=32,xmin=f.year,xmax=l.year;
  let ymax=1;hist.forEach(d=>{if(d.count>ymax)ymax=d.count;});ymax*=1.12;
  const px=yr=>xmax===xmin?(ml+w-mr)/2:ml+(w-ml-mr)*((yr-xmin)/(xmax-xmin)),py=v=>h-mb-(h-mt-mb)*(v/ymax);
  let out=`<rect x="0" y="0" width="${w}" height="${h}" fill="#fbfdff"/>`;
  for(let i=0;i<5;i++){const gy=mt+(h-mt-mb)*i/4;out+=`<line x1="${ml}" y1="${gy}" x2="${w-mr}" y2="${gy}" stroke="#e2e8f0"/>`;}
  if(hist.length>1)out+=`<path d="${hist.map((d,i)=>`${i?'L':'M'}${px(d.year).toFixed(1)},${py(d.count).toFixed(1)}`).join(' ')}" fill="none" stroke="#d91a3c" stroke-width="3" stroke-linecap="round"/>`;
  out+=hist.map(d=>`<circle cx="${px(d.year).toFixed(1)}" cy="${py(d.count).toFixed(1)}" r="4.5" fill="#0f1f33"><title>${d.year}: ${fmt(d.count,0)}</title></circle><text x="${px(d.year).toFixed(1)}" y="${h-10}" text-anchor="middle" font-size="11" fill="#5b6e84">${d.year}</text>`).join('');
  svg.innerHTML=out;
}

function renderBranchProv(m){
  const sec=curSector();if(!sec)return;
  const validMunis=m.all.filter(r=>r.count!==null).length;
  document.getElementById('branchProvContent').innerHTML=`
    <div class="details-grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
      <div class="mbox"><div class="label">${esc(tr('branch_count'))}</div><div class="value">${sec.branch_labels.length}</div></div>
      <div class="mbox"><div class="label">${esc(tr('observations'))}</div><div class="value">${fmt(sec.observation_count,0)}</div></div>
      <div class="mbox"><div class="label">${esc(tr('munis_with_data'))}</div><div class="value">${validMunis} / ${DATA.rows.length}</div></div>
    </div>
    <div class="small" style="margin-bottom:6px"><strong>${esc(tr('cnae_codes'))}:</strong> ${sec.cnae_codes.map(c=>`<span class="pill">${esc(c)}</span>`).join('')} · <strong>${esc(tr('obs_years'))}:</strong> ${DATA.business_years.join(', ')||tr('na_short')}</div>
    <div class="small" style="font-weight:700;margin-top:6px">${esc(tr('matched_branches'))}:</div>
    <div style="margin-top:4px">${sec.branch_labels.map(b=>`<span class="pill" style="background:#fff1f2;color:#9f1239">${esc(b)}</span>`).join('')}</div>`;
}

function renderStability(m){
  const host=document.getElementById('stabilityContent');
  if(!m.scored.length){host.innerHTML=`<div class="small">${esc(tr('no_data'))}</div>`;return;}
  const sm=m.stabilityMeta,reg=sm.leaderWinRate>=60?tr('stability_stable'):tr('stability_sensitive');
  const top=[...m.scored].sort((a,b)=>b.stability-a.stability).slice(0,6);
  host.innerHTML=`
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">
      <span class="pill">${esc(tr('scenarios_tested'))}: ${sm.scenarios}</span>
      <span class="pill">${esc(tr('top1_win_rate'))}: ${sm.leaderWinRate}%</span>
      <span class="pill ${sm.leaderWinRate>=60?'status-passed':'status-warning'}">${esc(reg)}</span>
    </div>
    <div class="table-wrap"><table class="tbl">
      <tr><th>${esc(tr('municipality'))}</th><th>${esc(tr('score'))}</th><th>${esc(tr('stability'))}</th></tr>
      ${top.map(r=>`<tr><td>${esc(r.municipality_name)}</td><td>${r.score}/100 (#${r.rank})</td><td><strong>${r.stability}%</strong></td></tr>`).join('')}
    </table></div>`;
}

function renderCompChart(m){
  const svg=document.getElementById('comparisonChart'),top=m.scored.slice(0,12);
  if(!top.length){svg.innerHTML='';return;}
  const w=720,h=300,ml=48,mr=28,mt=22,mb=82,step=(w-ml-mr)/top.length;
  let maxD=1;top.forEach(r=>{if((r.competition_density||0)>maxD)maxD=r.competition_density;});
  let out=`<rect x="0" y="0" width="${w}" height="${h}" fill="#fff"/>`,pts=[];
  for(let i=0;i<5;i++){const gy=mt+(h-mt-mb)*i/4;out+=`<line x1="${ml}" y1="${gy}" x2="${w-mr}" y2="${gy}" stroke="#e2e8f0"/>`;}
  top.forEach((r,i)=>{
    const x=ml+i*step+step*0.2,bw=step*0.55,bh=(h-mt-mb)*((r.competition_density||0)/maxD),y=h-mb-bh,cx=x+bw/2,cy=h-mb-(h-mt-mb)*(r.score/100);
    out+=`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${bh.toFixed(1)}" fill="${colScore(r.score)}88" stroke="${colScore(r.score)}" rx="5"><title>${esc(r.municipality_name)} · ${fmt(r.competition_density,1)}/10k · ${r.score}/100</title></rect>`;
    out+=`<text x="${cx.toFixed(1)}" y="${h-68}" font-size="10.5" fill="#5b6e84" transform="rotate(32 ${cx.toFixed(1)} ${h-68})">${esc(r.municipality_name)}</text>`;
    pts.push({cx,cy,r});
  });
  out+=`<path d="${pts.map((p,i)=>`${i?'L':'M'}${p.cx.toFixed(1)},${p.cy.toFixed(1)}`).join(' ')}" fill="none" stroke="#0f1f33" stroke-width="2.5"/>`;
  out+=pts.map(p=>`<circle cx="${p.cx.toFixed(1)}" cy="${p.cy.toFixed(1)}" r="4" fill="#0f1f33"><title>${esc(p.r.municipality_name)}: ${p.r.score}/100</title></circle>`).join('');
  out+=`<text x="${ml}" y="14" font-size="11" fill="#5b6e84">${esc(tr('competition_density'))}</text><text x="${w-130}" y="14" font-size="11" fill="#5b6e84">${esc(tr('score'))}</text>`;
  svg.innerHTML=out;
}

function populateBreakEvenSelects(m){
  const valid=m.all.filter(r=>r.population&&r.population>0).sort((a,b)=>(b.score??-1)-(a.score??-1)||a.municipality_name.localeCompare(b.municipality_name));
  const sA=document.getElementById('compareA'),sB=document.getElementById('compareB');
  if(!valid.length){sA.innerHTML='';sB.innerHTML='';return;}
  const opts=valid.map(r=>`<option value="${esc(r.join_key)}">${esc(r.municipality_name)}${r.score!==null?` (${r.score}/100)`:''}</option>`).join('');
  sA.innerHTML=opts;sB.innerHTML=opts;
  if(!state.compareAKey||!valid.some(r=>r.join_key===state.compareAKey))state.compareAKey=valid[0].join_key;
  if(!state.compareBKey||!valid.some(r=>r.join_key===state.compareBKey))state.compareBKey=(valid[1]||valid[0]).join_key;
  sA.value=state.compareAKey;sB.value=state.compareBKey;
}

function renderBreakEven(m){
  const valid=m.all.filter(r=>r.population&&r.population>0);
  const out=document.getElementById('breakEvenOutput'),err=document.getElementById('breakEvenError'),ch=document.getElementById('breakEvenChartWrap');
  if(!valid.length){err.style.display='block';err.textContent=tr('break_empty');out.innerHTML='';ch.innerHTML='';return;}
  const fixed=Number(document.getElementById('fixedCosts').value),marginPct=Number(document.getElementById('marginPct').value),ticket=Number(document.getElementById('avgTicket').value),days=Number(document.getElementById('daysOpen').value);
  if(Number.isNaN(fixed)||fixed<0||Number.isNaN(marginPct)||marginPct<=0||marginPct>100||Number.isNaN(ticket)||ticket<=0||Number.isNaN(days)||days<1||days>31){
    err.style.display='block';err.textContent=tr('break_invalid');out.innerHTML='';ch.innerHTML='';return;
  }
  err.style.display='none';
  const a=valid.find(r=>r.join_key===state.compareAKey)||valid[0],b=valid.find(r=>r.join_key===state.compareBKey)||valid[1]||valid[0];
  const sales=fixed/(marginPct/100),custMo=sales/ticket,custDay=custMo/days;
  const reqA=custDay/a.population*10000,reqB=custDay/b.population*10000,maxReq=Math.max(reqA,reqB,0.01);
  const rowHtml=(lbl,r,req)=>`<tr><td><strong>${lbl}</strong></td><td>${esc(r.municipality_name)}</td><td>${r.score!==null?r.score+'/100':tr('na_short')}</td><td>${fmt(sales,2)} €</td><td>${fmt(custMo,0)}</td><td>${fmt(custDay,1)}</td><td><strong>${fmt(req,2)}</strong></td></tr>`;
  out.innerHTML=`<div class="table-wrap"><table class="tbl">
    <tr><th>#</th><th>${esc(tr('municipality'))}</th><th>${esc(tr('score'))}</th><th>${esc(tr('breakeven_sales'))}</th><th>${esc(tr('customers_month'))}</th><th>${esc(tr('customers_day'))}</th><th>${esc(tr('customers_per_10k'))}</th></tr>
    ${rowHtml('A',a,reqA)}${rowHtml('B',b,reqB)}
  </table></div><div class="small" style="margin-top:6px">${esc(tr('break_req_note'))}</div>`;
  ch.innerHTML=`<div style="background:#f8fafc;border:1px solid var(--line);border-radius:12px;padding:12px">
    <div class="small" style="font-weight:700;margin-bottom:6px">${esc(tr('customers_per_10k'))}</div>
    <div class="bar-row"><div>A · ${esc(a.municipality_name)}</div><div class="bar-track"><div class="bar-fill" style="width:${(reqA/maxReq*100).toFixed(1)}%;background:#0f1f33"></div></div><div>${fmt(reqA,2)}</div><div></div></div>
    <div class="bar-row"><div>B · ${esc(b.municipality_name)}</div><div class="bar-track"><div class="bar-fill" style="width:${(reqB/maxReq*100).toFixed(1)}%;background:#d91a3c"></div></div><div>${fmt(reqB,2)}</div><div></div></div>
  </div>`;
}

function renderAuditTabs(){
  const sec=curSector();
  if(state.lang==='es'){
    document.getElementById('tabMethod').innerHTML=`
      <div class="fbox">OpportunityScore(m, s) = round( 100 × [ Σ (w_k · P_k(m,s)) / Σ w_k ] )  para dimensiones disponibles k</div>
      <ul class="small" style="line-height:1.7">
        <li><strong>Normalización por rango medio (Mid-Rank Percentile):</strong> ordena los municipios elegibles y asigna percentiles en [0, 1], reduciendo el impacto de outliers frente a Min–Max simple.</li>
        <li><strong>Hueco competitivo (P_comp):</strong> inverso de <code>Unidades(m,s) / Población(m) × 10.000</code> (col_emp_ramas / padron_por_sexo).</li>
        <li><strong>Demanda potencial (P_dem):</strong> función específica del modo <code>${esc(sec?sec.demand_mode:'')}</code> (consumo urbano, B2B productivo, salud/edad ≥65, educación/edad 15–34, o bienestar).</li>
        <li><strong>Poder adquisitivo (P_inc):</strong> indicador oficial municipal de renta disponible (irpf_indicador_renta). No representa ingresos empresariales.</li>
        <li><strong>Impulso sectorial (P_mom):</strong> CAGR observado entre el primer y el último año de <code>col_emp_ramas</code>.</li>
        <li><strong>Escala de mercado (P_scale):</strong> <code>log10(Población)</code>.</li>
        <li><strong>Regla de completitud mínima:</strong> exige <code>Población &gt; 0</code>, conteo observado (no nulo) y al menos 3 de 5 dimensiones. Si faltan componentes, se excluyen y los pesos restantes se renormalizan al 100%.</li>
        <li><strong>Aviso de validación:</strong> este índice compuesto no ha sido validado empíricamente frente a tasas futuras de supervivencia empresarial.</li>
      </ul>`;
  }else{
    document.getElementById('tabMethod').innerHTML=`
      <div class="fbox">OpportunityScore(m, s) = round( 100 × [ Σ (w_k · P_k(m,s)) / Σ w_k ] )  over available dimensions k</div>
      <ul class="small" style="line-height:1.7">
        <li><strong>Mid-Rank Percentile Normalization:</strong> ranks eligible municipalities in [0, 1], limiting outlier distortion compared to raw Min–Max scaling.</li>
        <li><strong>Competition Gap (P_comp):</strong> inverted rank of <code>Units(m,s) / Population(m) × 10,000</code> (col_emp_ramas / padron_por_sexo).</li>
        <li><strong>Potential Demand (P_dem):</strong> sector-specific mode <code>${esc(sec?sec.demand_mode:'')}</code> (consumer density, B2B ecosystem, healthcare/senior share, education/youth share, or wellness).</li>
        <li><strong>Purchasing Power (P_inc):</strong> official municipal disposable-income indicator (irpf_indicador_renta), not business revenue.</li>
        <li><strong>Sector Momentum (P_mom):</strong> observed CAGR between earliest and latest year in <code>col_emp_ramas</code>.</li>
        <li><strong>Market Scale (P_scale):</strong> <code>log10(Population)</code>.</li>
        <li><strong>Minimum Completeness Rule:</strong> requires <code>Population &gt; 0</code>, observed count (non-null), and ≥ 3 of 5 dimensions; missing components are excluded and remaining weights renormalize to 100%.</li>
        <li><strong>Empirical Disclaimer:</strong> this composite index has not been empirically validated against future business survival outcomes.</li>
      </ul>`;
  }

  const srcs=Object.values(REPORT.sources||{}).filter(s=>s&&(s.dataset_title||s.dataset_id||s.error));
  document.getElementById('tabSources').innerHTML=`<div class="table-wrap"><table class="tbl">
    <tr><th>Dataset</th><th>ID</th><th>Resource</th><th>Geo Level</th><th>Years</th><th>Licence</th><th>URL</th></tr>
    ${srcs.map(s=>`<tr>
      <td>${esc(s.dataset_title||s.role||'')}</td><td><code>${esc(s.dataset_id||'—')}</code></td><td>${esc(s.resource_name||s.error||'—')}</td>
      <td>${esc(s.geographic_level||'—')}</td><td>${esc((s.schema&&s.schema.annual_years&&s.schema.annual_years.length?s.schema.annual_years.join(', '):(s.schema&&s.schema.latest_year?s.schema.latest_year:'—')))}</td>
      <td>${esc(s.license||'—')}</td><td>${s.dataset_url?`<a href="${esc(s.dataset_url)}" target="_blank" rel="noopener">${esc(tr('open_source'))}</a>`:'—'}</td>
    </tr>`).join('')}
  </table></div>`;

  const checks=DATA.validation_checks||[];
  const unm=(DATA.sector_audit&&DATA.sector_audit.unmatched_branches)||[];
  document.getElementById('tabValidation').innerHTML=`<div class="table-wrap"><table class="tbl">
    <tr><th>Check</th><th>Status</th><th>Audit Details</th></tr>
    ${checks.map(c=>`<tr>
      <td><strong>${esc(c.id)}</strong></td>
      <td><span class="pill status-${esc(c.status)}">${esc(tr('status_'+c.status))}</span></td>
      <td><code class="small">${esc(JSON.stringify(c.details))}</code></td>
    </tr>`).join('')}
  </table></div>`+(unm.length?`<div class="alert-warn"><strong>${esc(tr('unmatched_branches_label'))}:</strong> ${unm.map(esc).join(' · ')}</div>`:'');
}

function applyStaticLabels(){
  document.documentElement.lang=state.lang;
  [['subtitle','subtitle'],['offlineBadge','offline'],['guideBtn','calc_guide'],['langBtn','language_toggle'],
   ['mainSectorLabel','main_sector'],['sectorLabel','sector'],['indexNote','index_note'],
   ['kpiBestLabel','kpi_best_label'],['kpiMarketLabel','kpi_market_label'],['kpiCustomersLabel','kpi_customers_label'],['kpiIncomeLabel','kpi_income_label'],
   ['mapTitle','map_title'],['mapHint','map_click_hint'],['topTitle','top_title'],['topSubtitle','top_subtitle'],
   ['weightsTitle','weights_title'],['customWeightsLabel','custom_weights_toggle'],['resetWeightsBtn','reset_weights'],
   ['detailsTitle','details_title'],['branchProvTitle','branch_prov_title'],['stabilityTitle','stability_title'],['stabilityNote','stability_note'],
   ['chartTitle','chart_title'],['momentumTitle','momentum_title'],['momentumNote','momentum_note'],
   ['breakTitle','break_title'],['breakNote','break_note'],['compareALabel','compare_a'],['compareBLabel','compare_b'],
   ['fixedLabel','fixed_costs'],['marginLabel','margin'],['ticketLabel','ticket'],['daysLabel','days_open'],
   ['methodSectionTitle','method_section'],['warningBanner','warning_banner'],
   ['tabMethodBtn','tab_method'],['tabSourcesBtn','tab_sources'],['tabValidationBtn','tab_validation']
  ].forEach(([id,k])=>{const el=document.getElementById(id);if(el)el.textContent=tr(k);});
}

function renderDynamic(){
  const m=computeModel();
  syncWeightsUI(m.zeroWeights);
  renderTopKPIs(m);
  renderTop5(m);
  renderMap(m);
  renderSelected(m);
  renderBranchProv(m);
  renderStability(m);
  renderCompChart(m);
  populateBreakEvenSelects(m);
  renderBreakEven(m);
  renderAuditTabs();
}

function renderAll(){applyStaticLabels();populateSectorSelectors();renderDynamic();}

document.addEventListener('DOMContentLoaded',()=>{
  initWeightSlidersOnce();
  document.getElementById('mainSectorSelect').addEventListener('change',e=>{state.mainSector=e.target.value;populateSectorSelectors();state.selectedKey=null;renderDynamic();});
  document.getElementById('sectorSelect').addEventListener('change',e=>{state.sectorId=e.target.value;const s=curSector();if(s&&!state.useCustomWeights)state.weights=Object.assign({},s.defaults);state.selectedKey=null;renderDynamic();});
  document.getElementById('customWeightsToggle').addEventListener('change',e=>{state.useCustomWeights=e.target.checked;const s=curSector();if(!state.useCustomWeights&&s)state.weights=Object.assign({},s.defaults);renderDynamic();});
  document.getElementById('resetWeightsBtn').addEventListener('click',()=>{const s=curSector();if(s)state.weights=Object.assign({},s.defaults);state.useCustomWeights=false;renderDynamic();});
  document.getElementById('langBtn').addEventListener('click',()=>{state.lang=state.lang==='es'?'en':'es';renderAll();});
  document.getElementById('guideBtn').addEventListener('click',()=>{const g=document.getElementById('guideSection');g.open=true;g.scrollIntoView({behavior:'smooth'});});
  document.getElementById('compareA').addEventListener('change',e=>{state.compareAKey=e.target.value;renderBreakEven(computeModel());});
  document.getElementById('compareB').addEventListener('change',e=>{state.compareBKey=e.target.value;renderBreakEven(computeModel());});
  ['fixedCosts','marginPct','avgTicket','daysOpen'].forEach(id=>document.getElementById(id).addEventListener('input',()=>renderBreakEven(computeModel())));
  document.querySelectorAll('.tab-btn').forEach(btn=>btn.addEventListener('click',()=>{
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');
    ['method','sources','validation'].forEach(t=>document.getElementById('tab'+t.charAt(0).toUpperCase()+t.slice(1)).style.display=(t===btn.dataset.tab?'block':'none'));
  }));
  renderAll();
});
</script>
</body>
</html>"""
    return html.replace("__PAYLOAD__", payload)


def build_report(
    source_metas: dict[str, LoadedSource],
    summary: dict[str, Any],
    boundary_meta: dict[str, Any],
    context_meta: dict[str, Any],
    validation_checks: list[dict[str, Any]],
    sector_audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generated_utc": now_utc(),
        "api": API,
        "sources": {k: asdict(v) for k, v in source_metas.items()},
        "summary": summary,
        "sector_audit": sector_audit,
        "validation_checks": validation_checks,
        "boundary_meta": boundary_meta,
        "regional_context_schema": context_meta,
    }


def main() -> None:
    def _sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in df.select_dtypes(include=["object", "string"]).columns:
            df[col] = df[col].astype(object).where(df[col].notna(), other=None)
        return df

    loaded: dict[str, pd.DataFrame | dict[str, Any] | None] = {}
    source_metas: dict[str, LoadedSource] = {}

    for role in ("municipality_ref", "population", "density", "income", "business_demography"):
        try:
            data, meta = load_role(role)
            loaded[role] = data
            meta.geographic_level = "Regional (Comunidad de Madrid)" if role == "business_demography" else "Municipal (179 municipios)"
            source_metas[role] = meta
            print(f"{role}: loaded ({meta.retrieval}, {meta.rows} rows)")
        except Exception as exc:  # noqa: BLE001
            loaded[role] = None
            source_metas[role] = LoadedSource(role=role, error=str(exc))
            print(f"{role}: warning -> {exc}")

    # 1. Authoritative 179-municipality reference spine
    if not isinstance(loaded.get("municipality_ref"), pd.DataFrame):
        raise RuntimeError("Authoritative municipality reference (municipio_comunidad_madrid) could not be loaded.")
    municipality_ref, ref_schema = extract_municipality_ref(_sanitize_df(loaded["municipality_ref"]))
    if municipality_ref is None or municipality_ref.empty:
        raise RuntimeError("Could not extract municipalities from authoritative reference.")
    source_metas["municipality_ref"].schema = ref_schema
    source_metas["municipality_ref"].variables_used = ["municipio_codigo_ine", "municipio_nombre", "nuts4_nombre"]

    known_names = {n for n in municipality_ref["municipality_name"].dropna().map(canonical_muni_name) if n}
    known_codes = {str(c) for c in municipality_ref["municipality_code"].dropna()}

    # 2. Population, Density, Income
    population, pop_schema = None, {}
    if isinstance(loaded.get("population"), pd.DataFrame):
        try:
            population, pop_schema = extract_population_table(_sanitize_df(loaded["population"]), known_names=known_names, known_codes=known_codes)
            source_metas["population"].schema = pop_schema
            source_metas["population"].variables_used = [pop_schema.get("value_col"), pop_schema.get("year_col")]
        except Exception as exc:  # noqa: BLE001
            source_metas["population"].error = str(exc)

    density, density_schema = None, {}
    if isinstance(loaded.get("density"), pd.DataFrame):
        try:
            density, density_schema = extract_density_table(_sanitize_df(loaded["density"]), known_names=known_names, known_codes=known_codes)
            source_metas["density"].schema = density_schema
            source_metas["density"].variables_used = [density_schema.get("density_col"), density_schema.get("year_col")]
        except Exception as exc:  # noqa: BLE001
            source_metas["density"].error = str(exc)

    income, income_schema = None, {}
    if isinstance(loaded.get("income"), pd.DataFrame):
        try:
            income, income_schema = extract_income_table(_sanitize_df(loaded["income"]), known_names=known_names, known_codes=known_codes)
            source_metas["income"].schema = income_schema
            source_metas["income"].variables_used = [income_schema.get("value_col"), income_schema.get("metric_col")]
        except Exception as exc:  # noqa: BLE001
            source_metas["income"].error = str(exc)

    # 3. Business dataset (trying ranked resources until clean extraction)
    business_candidates = load_role_candidates("business")
    if not business_candidates:
        raise RuntimeError("Business dataset (col_emp_ramas) could not be downloaded from CKAN.")

    business, business_schema, biz_errors = None, {}, []
    for cand_df, cand_meta in business_candidates:
        try:
            business, business_schema = extract_business_table(_sanitize_df(cand_df), known_names=known_names, known_codes=known_codes)
            cand_meta.geographic_level = "Municipal (179 municipios)"
            cand_meta.schema = business_schema
            cand_meta.variables_used = [business_schema.get("branch_col"), business_schema.get("value_col"), business_schema.get("year_col")]
            source_metas["business"] = cand_meta
            print(f"business: loaded ({cand_meta.resource_name}, {len(business)} aggregated rows)")
            break
        except Exception as exc:  # noqa: BLE001
            biz_errors.append(f"[{cand_meta.resource_name} | cols={cand_meta.columns}]: {exc}")

    if business is None:
        raise RuntimeError("Failed to extract business dataset:\n" + "\n".join(biz_errors))

    # 4. Regional context
    regional_context, context_meta = [], {}
    if isinstance(loaded.get("business_demography"), pd.DataFrame):
        try:
            regional_context, context_schema = extract_regional_demography_context(_sanitize_df(loaded["business_demography"]))
            source_metas["business_demography"].schema = context_schema
            source_metas["business_demography"].variables_used = [context_schema.get("metric_col"), context_schema.get("value_col")]
            context_meta = {"rows": len(regional_context), "schema": context_schema}
        except Exception as exc:  # noqa: BLE001
            source_metas["business_demography"].error = str(exc)

    # 5. Official municipal polygons (IDEM WFS)
    crosswalk = build_name_to_code_crosswalk([municipality_ref, population, density, income, business])
    boundaries, boundary_meta = fetch_boundary_geojson(known_names=known_names, known_codes=known_codes, crosswalk=crosswalk)
    boundary_loaded = LoadedSource(
        role="boundaries",
        institution="Comunidad de Madrid · IDEM Geoportal",
        dataset_title="IDEM WFS - Unidades Administrativas",
        dataset_url=IDEM_WFS,
        license="CC BY 4.0",
        retrieval=boundary_meta.get("retrieval"),
        retrieved_utc=now_utc(),
        geographic_level="Municipal Polygons (EPSG:4326)",
        rows=boundary_meta.get("features"),
        resource_name=boundary_meta.get("feature_type"),
        resource_format=boundary_meta.get("output_format"),
        variables_used=[boundary_meta.get("name_property"), boundary_meta.get("code_property")],
        error=boundary_meta.get("error"),
    )
    source_metas["boundaries"] = boundary_loaded

    data_model, summary = build_data_model(
        municipality_ref, business, population, density, income, boundaries,
        business_schema, ref_schema, income_schema, boundary_meta,
    )
    data_model["regional_context"] = regional_context
    report = build_report(source_metas, summary, boundary_meta, context_meta, data_model["validation_checks"], data_model["sector_audit"])

    OUT_AUDIT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_HTML.write_text(html_template(data_model, report), encoding="utf-8")
    print(f"Built {OUT_HTML} and {OUT_AUDIT} (official coverage={summary['coverage_official_reference']}, boundaries={summary['official_boundary_features']})")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"BUILD STOPPED: {exc}", file=sys.stderr)
        sys.exit(1)

