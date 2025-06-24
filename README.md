# ☀️ Solar OnGrid: Herramienta de análisis técnico y económico de sistemas fotovoltaicos residenciales

**Solar OnGrid** es una aplicación desarrollada en Python con Streamlit que permite analizar, dimensionar y generar reportes técnicos de sistemas fotovoltaicos residenciales conectados a la red (on-grid). Es una herramienta abierta, educativa y técnica que empodera a los usuarios para evaluar su consumo eléctrico, estimar su potencial solar y tomar decisiones informadas hacia una transición energética justa.

---

## 🚀 Características principales

- 📊 Carga de datos de consumo eléctrico mensual (desde Excel o tabla editable).
- 📍 Análisis personalizado por ubicación (latitud y longitud) y radiación solar.
- ⚡ Cálculo automático del tamaño óptimo del sistema FV según cobertura deseada.
- 💰 Simulación de ahorro anual, flujo de caja, TIR, VAN y payback.
- 📄 Generación de un reporte técnico profesional en PDF con interpretación automatizada.
- 🔁 Alternancia entre opciones de autoconsumo, Net Billing y Net Metering.
- 🎓 Enfoque educativo, con glosario técnico y explicaciones amigables.

---

## 📂 Estructura del proyecto

```bash
📦 solar_python/
├── analisis_fv.py           # Script principal de la aplicación Streamlit
├── carga_datos.py           # Funciones para cargar y limpiar datos de consumo
├── requirements.txt         # Dependencias necesarias
├── README.md                # Documentación del proyecto
````

---

## 💻 Cómo usar el programa

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu_usuario/solar-ongrid.git
cd solar-ongrid
```

### 2. Crear entorno virtual (opcional pero recomendado)

```bash
python -m venv env
source env/bin/activate      # En Linux/macOS
env\Scripts\activate         # En Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```bash
streamlit run analisis_fv.py
```

---

## 📝 Requisitos

* Python 3.9 o superior
* Navegador web moderno (Chrome, Firefox, Edge)
* Conexión a internet para obtener coordenadas si usas ubicación por mapa (opcional)

---

## 📘 Aplicaciones y contexto

Esta aplicación fue diseñada para apoyar:

* Proyectos de electrificación sostenible.
* Consultorías técnicas en eficiencia energética.
* Educación técnica en energía solar.
* Gobiernos locales y ONGs que promueven el acceso equitativo a la energía.
* Usuarios residenciales interesados en instalar paneles solares.

Su uso contribuye a:

* Democratizar el conocimiento energético.
* Apoyar decisiones informadas y técnicas.
* Mitigar la pobreza energética.
* Fomentar la transición hacia una matriz energética limpia y justa.

---

## 📌 Limitaciones actuales

* No considera inclinación, orientación o pérdidas eléctricas detalladas.
* Análisis basado en datos mensuales (no horarios).
* Aún no incluye simulación de baterías o almacenamiento.

---

## 🔧 Posibles mejoras futuras

* Análisis con curvas de carga horaria.
* Simulación de sistemas híbridos con baterías.
* Estimación de emisiones evitadas (huella de carbono).
* Acceso desde dispositivos móviles.
* Integración con bases de datos de irradiación satelital.

---

## 📄 Licencia

Este proyecto es de código abierto bajo licencia MIT. Puedes usarlo, modificarlo y compartirlo libremente citando su origen.

---

## 🤝 Autoría

Desarrollado por **Alejandro Haro**, con el apoyo de OpenAI y la comunidad de software libre.
