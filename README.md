# TSLA & NU Terminal Cuantitativa Institucional (Hedge Fund Standard)

> **Terminal web y PWA móvil de grado institucional** diseñada con estándares de fondos de cobertura cuantitativos (Wall Street Quantitative Trading Desk). Combina **Detección Algorítmica de Suelos y Techos Extremos**, **Smart Money Concepts (SMC)**, **VWAP Multi-Sigma**, **Gestión de Capital por Criterio de Kelly** y **Radar de Oportunidades Asimétricas** para **Tesla (TSLA)**, **Nubank (NU)** y las principales acciones del mercado de EE.UU.

![Hedge Fund Grade](https://img.shields.io/badge/Wall%20Street-Quantitative%20Desk-00ff88?style=for-the-badge&logo=tradingview&logoColor=black)
![TSLA & NU](https://img.shields.io/badge/TSLA%20%26%20NU-Institutional%20Alpha-820ad1?style=for-the-badge&logo=tesla&logoColor=white)
![GitHub Pages](https://img.shields.io/badge/Deploy-GitHub%20Pages-050508?style=for-the-badge&logo=github)

---

## 🌟 Modelos e Indicadores Cuantitativos Institucionales

| Herramienta Institucional | Fundamento Matemático & Operativo | Aplicación en Trading |
|---|---|---|
| 🟢 **Detección de Suelo Extremo** | Z-Score $\le -1.8\sigma$ + RSI Sobrevendido + Acumulación CMF | Identifica puntos de agotamiento de ventas para compras asimétricas de bajo riesgo |
| 🔴 **Detección de Techo Extremo** | Z-Score $\ge +2.0\sigma$ + RSI $>70$ + Divergencia de Volumen | Identifica zonas de distribución de los grandes fondos para toma de beneficios o ventas en corto |
| 📊 **Termómetro de Valoración Dual** | Medición compuesta en 5 fases (Suelo, Descuento, Equilibrio, Premium, Techo) | Evita comprar en zonas de sobrecompra y optimiza entradas en descuento institucional |
| ⚡ **Smart Money Concepts (SMC)** | Order Blocks (OBs), Fair Value Gaps (FVG), BOS & CHoCH | Rastrea las huellas de liquidez de los creadores de mercado (Market Makers) |
| 📈 **VWAP Multi-Sigma (±1σ, ±2σ)** | Precio Ponderado por Volumen con bandas de volatilidad intradía | Proporciona el valor intrínseco de referencia para las instituciones financieras |
| 🧮 **Exponente de Hurst ($H$)** | Análisis de Rango Reescalado ($R/S$) para régimen de mercado | Distingue regímenes de reversión a la media ($H < 0.5$) de regímenes tendenciales ($H > 0.5$) |
| 🛡️ **Criterio de Kelly ($f^*$)** | Asignación matemática óptima de capital: $f^* = \frac{p(b+1)-1}{b}$ | Maximiza el crecimiento geométrico del capital y calcula el Half-Kelly para proteger contra drawdowns |
| 🌐 **Macro Hub & Dark Pool Flow** | VIX, Rendimiento US 10Y, Bloques de Dark Pool y Gamma Exposure (GEX) | Contextualiza la microestructura con el apetito de riesgo global de Wall Street |

---

## 📱 Acceso Inmediato en tu Celular (PWA Web)

Puedes acceder a la terminal institucional directamente en cualquier navegador o instalarla como aplicación móvil en tu teléfono:

👉 **[https://jhondaniel84.github.io/ANALISTA-DE-ACCIONES-DE-TESLA/](https://jhondaniel84.github.io/ANALISTA-DE-ACCIONES-DE-TESLA/)**

### 📲 Cómo Instalarla en tu Teléfono
- **iPhone / Safari**: Toca el botón Compartir (cuadrado con flecha hacia arriba) y selecciona **"Añadir a la pantalla de inicio"**.
- **Android / Chrome**: Toca los 3 puntos superiores y selecciona **"Instalar aplicación"** / **"Añadir a pantalla de inicio"**.

---

## 💻 Entorno Python Standalone (FastAPI + Streamlit)

Si deseas ejecutar la terminal en tu entorno local con soporte de scripts cuantitativos:

```bash
# 1. Instalar dependencias
pip install -r trading_app/requirements.txt

# 2. Iniciar servidor FastAPI
python -m uvicorn trading_app.backend.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Iniciar terminal Streamlit
streamlit run trading_app/frontend/app.py
```

---

## 🔑 Datos en Tiempo Real (Finnhub API)

La aplicación cuenta con un **motor cuantitativo autónomo** de simulación y análisis técnico que funciona sin configuración previa. Si deseas datos en tiempo real de Wall Street:
1. Obtén tu clave gratuita en [finnhub.io](https://finnhub.io).
2. En la app móvil o web, ve a **Configuración** y pega tu clave.

---

## ⚠️ Aviso Legal

Esta aplicación fue desarrollada con fines estrictamente investigativos, analíticos y educativos de nivel cuantitativo. **No constituye asesoría financiera ni recomendación formal de inversión**.
