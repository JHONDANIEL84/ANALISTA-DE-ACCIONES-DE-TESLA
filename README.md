# TSLA Analista — Analista de Acciones de Tesla

> **PWA instalable** para vigilar el precio de Tesla (TSLA) en tiempo real desde cualquier dispositivo.

![Vista previa](https://img.shields.io/badge/TSLA-Analista-e31937?style=for-the-badge&logo=tesla&logoColor=white)
![GitHub Pages](https://img.shields.io/badge/Deploy-GitHub%20Pages-0a0a0f?style=for-the-badge&logo=github)

---

## ✨ Características

| Función | Detalle |
|---|---|
| 📈 **Precio en tiempo real** | Consulta Finnhub cada 15s/30s/1min/5min |
| 📊 **Métricas del día** | Apertura, cierre anterior, máximo y mínimo |
| 📉 **Sparkline de sesión** | Historial visual de precios de la sesión actual |
| 🔺 **Indicador de tendencia** | Alcista / Bajista / Lateral según variación % |
| 🔔 **Alertas push** | Notificaciones cuando el precio cruza tus umbrales |
| ⚙️ **API key in-app** | Configura tu clave Finnhub sin tocar el código |
| 🌙 **Modo oscuro/claro** | Toggle de tema persistente |
| 📱 **Instalable** | PWA con soporte offline (service worker) |

---

## 🚀 Instalación y uso

### 1. Obtener clave de Finnhub

1. Crea cuenta gratuita en [finnhub.io](https://finnhub.io)
2. Copia tu API key desde el dashboard

### 2. Publicar la app

**Opción A — GitHub Pages (recomendado, gratis)**

Este repositorio incluye un workflow de GitHub Actions que publica automáticamente en GitHub Pages:

1. Ve a **Settings → Pages** en tu repo
2. En **Source**, selecciona `GitHub Actions`
3. El workflow `.github/workflows/deploy.yml` se ejecuta en cada push a `main`
4. Tu app estará disponible en `https://JHONDANIEL84.github.io/ANALISTA-DE-ACCIONES-DE-TESLA/`

**Opción B — Netlify Drop**

1. Abre [app.netlify.com/drop](https://app.netlify.com/drop)
2. Arrastra esta carpeta
3. Obtienes una URL pública al instante

### 3. Ingresar la clave en la app

Una vez publicada, abre la app, ve a **Configuración** e ingresa tu API key de Finnhub. Se guarda localmente en el dispositivo.

### 4. Instalar en el móvil

- **Android (Chrome)**: Toca los tres puntos → *Añadir a pantalla de inicio*
- **iOS (Safari)**: Toca compartir → *Agregar a la pantalla de inicio*

---

## 📋 Alertas de precio

Las alertas se revisan en cada actualización mientras la app está abierta. Por defecto tienen un **cooldown de 5 minutos** para evitar spam de notificaciones.

> **Nota**: Las alertas no funcionan si el teléfono cierra la app. Para alertas 24/7 se necesita un backend.

---

## 🛠 Tecnologías

- HTML5 + CSS3 + JavaScript vanilla (sin frameworks)
- [Finnhub API](https://finnhub.io) — cotizaciones de bolsa
- [TradingView Widget](https://www.tradingview.com) — gráfico interactivo
- PWA: Service Worker + Web App Manifest

---

## ⚠️ Aviso legal

Esta aplicación es **exclusivamente informativa**. Los precios pueden tener retraso según el plan de Finnhub. No constituye asesoría financiera, de inversión ni recomendación de compra/venta.
