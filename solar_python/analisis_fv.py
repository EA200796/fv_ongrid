# Librerias
import pandas as pd
import numpy as np
import numpy_financial as npf
from numpy_financial import irr, npv
import streamlit as st
import rasterio
import glob
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_folium import folium_static
from streamlit_folium import st_folium
import folium
from carga_datos import subida_tabla, subida_checkbox, subida_formato
from datetime import datetime
import io # para crear buffer en memoria
from xhtml2pdf import pisa
import base64
import plotly.io as pio



# Configuración inicial
## Titulo de la pestaña y configuracion de la bara lateral
st.set_page_config(page_title= 'Solar OnGrid', layout= 'wide', initial_sidebar_state= "collapsed")


def main ():
    # Título de pagina
    st.title('Factibilidad de Sistema On-Grid Fotovoltaico en Ecuador')
    
    # Configutación de barra lateral
    st.sidebar.header('🧾 Ingreso de datos') # título

    ################

    # Cargador de archivos

    archivo_datos = None

    # menu de opciones de carga
    menu = ['Subir archivo', 'Llenar tabla', 'Selecciona los aparatos en tu hogar']
    
    # boton de radio para opcion de carga
    choice = st.sidebar.radio("📥 Carga tus datos aquí",menu)
    st.sidebar.info('Escoge una de las siguientes opciones para hacerlo.',icon='ℹ️')
    
    if choice == "Subir archivo":
        subida_formato()
    elif choice == "Llenar tabla":
        subida_tabla()
    elif choice == "Selecciona los aparatos en tu hogar":
        subida_checkbox()
    else:
        st.subheader("Saludos, selecciona una opción de carga")

    archivo_datos = st.session_state.get("archivo_datos",None)
   

    #######
    with st.popover("Selecciona tus coordenadas"):
        # Carpeta con el archivo raster GHI (.tif)
        ruta_ghi = 'solar_python/ghi/GHI.tif'

        ##############
        # --- Inicializar estado ---
        if "lat" not in st.session_state:
            st.session_state["lat"] = -0.22985
        if "lon" not in st.session_state:
            st.session_state["lon"] = -78.52495

        # --- Función para actualizar coordenadas manuales ---
        def actualizar_lat():
            st.session_state["lat"] = st.session_state["lat_input"]

        def actualizar_lon():
            st.session_state["lon"] = st.session_state["lon_input"]

        # --- Entradas manuales desde la barra lateral ---
        st.sidebar.markdown("### 🌍 Coordenadas manuales o desde el mapa")
        lat = st.sidebar.number_input("Latitud (manual):",
                                min_value=-5.0, max_value=5.0,
                                value=st.session_state["lat"],
                                key="lat_input",
                                format="%.10f",
                                on_change=actualizar_lat)

        lon = st.sidebar.number_input("Longitud (manual):",
                                min_value=-100.0, max_value=100.0,
                                value=st.session_state["lon"],
                                key="lon_input",
                                format="%.10f",
                                on_change=actualizar_lon)

        # --- Mapa con clic para capturar coordenadas ---
        m = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=7)
        folium.Marker(location=[st.session_state["lat"], st.session_state["lon"]],
                    tooltip="Coordenada actual",
                    icon=folium.Icon(color="blue")).add_to(m)
        m.add_child(folium.LatLngPopup())

        # --- Mostrar el mapa e interactuar ---
        st.write("📍 Haz clic en el mapa o usa la barra lateral para ingresar coordenadas:")
        map_data = st_folium(m, width=700, height=500)

        # --- Actualizar si hubo clic ---
        if map_data.get("last_clicked"):
            st.session_state["lat"] = round(map_data["last_clicked"]["lat"], 10)
            st.session_state["lon"] = round(map_data["last_clicked"]["lng"], 10)

        # --- Mostrar coordenadas actuales finales ---
        st.success(f"✅ Coordenadas seleccionadas: lat = {st.session_state['lat']}, lon = {st.session_state['lon']}")
            
    #############

    # Validar si se ingresaron valores distintos de cero (como señal de entrada válida)
    if lat == 0.0 and lon == 0.0:
        st.sidebar.warning("🔔 Por favor, ingresa la latitud y longitud válidas.")
        st.stop()          

    ########333
    # 🔍 Abrir el raster y extraer el valor en la coordenada
    try:
        with rasterio.open(ruta_ghi) as src:
            # Verifica si las coordenadas están en el mismo CRS que el raster
            coords = [(lon, lat)]
            radiacion_diaria = list(src.sample(coords))[0][0]
        
        # Validar si el valor es numérico y no NaN o inf
        if np.isnan(radiacion_diaria) or np.isinf(radiacion_diaria):
            st.error(f"⚠️ La radiación solar en ({lat}, {lon}) es inválida (NaN o Inf).")
            st.info("Asegúrate de que las coordenadas estén dentro del área válida del raster.")
            st.stop()        

    except Exception as e:
        st.sidebar.error(f"❌ Error al acceder a los datos del raster: {e}")
        st.sidebar.info("Verifica que las coordenadas estén dentro del área válida.")
        st.stop()
    # Ingreso de datos de cobertura consumo y factor de perdidas
    # Generar opciones de 0% a 100% en pasos de 0.5
    opciones_porcentaje = np.round(np.arange(0, 100, 1), 1).tolist()

    objetivo_cobertura = st.sidebar.select_slider(
        "✅ Objetivo de cobertura (%):", 
        options= opciones_porcentaje,
        value= 75.0 # valor predeterminado
        )
    st.session_state['objetivo_cobertura'] = objetivo_cobertura/100
    factor_perdidas = st.sidebar.select_slider(
        "✅ Factor de pérdidas (%):",
        options= opciones_porcentaje,
        value= 20
        )
    factor_perdidas = (100 - factor_perdidas)/100

    vida_util = st.sidebar.number_input('⌛ Vida útil (años):',
        min_value= 0,
        max_value= 30,
        value=25)

    años_proyecto = st.sidebar.number_input('⌛ Horizonte financiero (años):',
        min_value= 0,
        max_value= 20,
        value=20,
        help="El número de años que decides analizar para calcular la rentabilidad financiera (15 - 20 años es recomendable)")
    
    mantenimiento_anual = st.sidebar.number_input('🔧 Mantenimiento anual ($):',
        min_value= 0,
        max_value= 100, 
        value=20)
    
    tasa_descuento = st.sidebar.number_input(
        label="💸 Tasa de descuento o Tasa de oportunidad",
        min_value= 0.00,
        max_value= 1.00,
        step= 0.01,
        value= 0.08,
        format= "%0.002f",
        help="Tasa de oportunidad que estás usando como referencia para evaluar si el proyecto es financieramente conveniente.")
    
    costo_Wp = st.sidebar.number_input("💸 Costo por Wp", value=1.2, help="Cuánto cuesta instalar 1 watt de potencia nominal del sistema solar.")
    ########
    ### trabajando datos
 #########            
 # Procesar si se subió o creó un DataFrame
    if archivo_datos is not None:
        
        # Si es un archivo subido
        if hasattr(archivo_datos, "type"):  # ← Verifica si es un archivo (tiene tipo MIME)
            tipo_archivo = archivo_datos.type

            try:
                if tipo_archivo == "text/csv":
                    df = pd.read_csv(archivo_datos)
                elif tipo_archivo == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    df = pd.read_excel(archivo_datos)
                else:
                    st.warning("⚠️ Formato de archivo no compatible")
                    df = pd.DataFrame()
            except Exception as e:
                st.error(f"❌ Error al leer el archivo: {e}")
                df = pd.DataFrame()
        else:
            # Si ya es un DataFrame (como en tabla editable o checkbox futuro)
            df = archivo_datos

        # Guardar en session_state para otros módulos
        st.session_state["df"] = df
        st.success("✅ Datos cargados correctamente")
        
         
        # Trabajando con el DataFrame
        # Obtener el año actual (por ejemplo, 2024)
        anio_actual = datetime.now().year
        if not df.empty:
                      
            # Elimnación de espacios innecesarios (principio y final)
            df.columns = df.columns.str.strip()

            # Se cambia la columna 'Fecha' a tipo datetime
            if choice != "Selecciona los aparatos en tu hogar":
                df['Fecha']=pd.to_datetime(df['Fecha'], format = 'mixed')
            else:
                # Crear 12 fechas: primer día de cada mes del año actual
                fechas = pd.date_range(start=f"{anio_actual}-01-01", periods=12, freq="MS")
                
                # Tomando en cuenta que df contiene el consumo diario estimado de checkbox
                # Repetimos el consumo diario total por cada mes
                consumo_diario = df["Consumo subtotal"].sum()
                consumo_mensual_estimado = consumo_diario * 30  # aproximación mensual

                # Crear nuevo DataFrame de 12 meses
                df = pd.DataFrame({
                    "Fecha": fechas,
                    "Consumo subtotal": [consumo_mensual_estimado] * 12,
                    "Monto": df["Monto"].sum() * 12,
                    "Total_pagar": df['Total_pagar'].sum() * 12
                })

                        # Convertir DataFrae a archivo Excel en memoria
                st.session_state["df"] = df
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Datos")

                # Reposicionar el cursor al inicio del buffer
                output.seek(0)

                # Boton de descarga
                st.download_button(
                    label="📤 Descargar archivo Excel",
                    data=output,
                    file_name="formato_ingresado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Lista de columnas a limpiar y redondear
            columnas = ["Monto", "Total_pagar"]

            
            # Limpieza de caracteres y redondeo a 2 decimales
            for col in columnas:
                df[col] = df[col].replace(r'[\$,]', '', regex=True).astype(float).round(2)
            
            # Periodo de analisis
            # Diccionario de meses en español (completos)
            meses_es = {
                1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
            }

            # Extraer año y número de mes
            df['Año'] = df['Fecha'].dt.year
            df['Mes_num'] = df['Fecha'].dt.month
            df['Mes'] = df['Mes_num'].map(meses_es)

            # Ordenar cronológicamente
            df = df.sort_values(by=['Año', 'Mes_num'])

            # Cantidad de meses y años
            cant_meses = df['Mes'].count()
            año_min = df['Año'].min()
            año_max = df['Año'].max()

            # Estadisticas descriptivas
            consumo_promedio_kWh = df["Consumo subtotal"].mean()
            consumo_min_kWh = df["Consumo subtotal"].min()
            consumo_max_kWh = df["Consumo subtotal"].max()
            consumo_std_kWh = df["Consumo subtotal"].std()
            
            st.session_state['consumo_promedio_kWh'] = consumo_promedio_kWh

            #---
            monto_promedio = df["Monto"].mean()
            monto_max = df["Monto"].max()
            Total_pagar_promedio = df["Total_pagar"].mean()
            pago_promedio_usd = df["Monto"].mean()
            pago_total_promedio_usd = df["Total_pagar"].mean()
            tarifa_promedio_usd_kWh = pago_promedio_usd / consumo_promedio_kWh
            
            tarifa_mas_impuestos = pago_total_promedio_usd / consumo_promedio_kWh
            st.session_state['tarifa_mas_impuestos'] = tarifa_mas_impuestos
            
            #tarifa_mas_impuestos_ctvs = (pago_total_promedio_usd / consumo_promedio_kWh)*100
            
            st.session_state['tarifa_promedio_usd_kWh'] = tarifa_promedio_usd_kWh
            
            
            ##############
            # Descripción de consumo
            def variacion ():
                
                porcentaje_variacion = consumo_std_kWh/consumo_promedio_kWh 
                clasificacion_variacion = ""
                
                if porcentaje_variacion < 0.10:
                    clasificacion_variacion = "muy estable, consumo mensual constante."
                elif porcentaje_variacion > 0.10 and porcentaje_variacion < 0.20:
                    clasificacion_variacion = "moderadamente estable, pequeñas fluctuaciones esperadas."
                elif porcentaje_variacion > 0.20 and porcentaje_variacion < 0.30:
                    clasificacion_variacion = "inestable, cambios mensuales notables."
                else:
                    clasificacion_variacion = "altamente inestable, alta variación: revisar hábitos."
                
                descripcion_variacion = f"\nVariación anual de consumo: ±{consumo_std_kWh:.2f} kWh ({porcentaje_variacion*100:.2f}%) {clasificacion_variacion}"
                return descripcion_variacion
            #---
            # Descripción del usuario
            def tipo_usuario():
                class_usuario = ""
                if consumo_promedio_kWh >50 and consumo_promedio_kWh < 120:
                    class_usuario = "Residencial urbano, inyección cero recomendada."
                elif consumo_promedio_kWh > 120 and consumo_promedio_kWh < 800:
                    class_usuario = "Comercio mediano, Net billing posible."
                elif consumo_promedio_kWh > 800 and consumo_promedio_kWh < 5000:
                    class_usuario = "Industrial pequeño, requiere memoria técnica detallada."
                elif consumo_promedio_kWh < 50:
                    class_usuario = "Rural aislado, preferencia por autonomía energética."
                else:
                    class_usuario = "Fuera del rango para pequeño consumidor"
                descripcion_usuario = f"\n📈 Tipo de usuario: {class_usuario}"
                return descripcion_usuario
        
            ##########
            # Carpeta con los 12 archivos raster mensuales (.tif)
            ruta_rasters = 'solar_python/monthly_pvout'
            archivos_raster = sorted(glob.glob(os.path.join(ruta_rasters, '*.tif')))
            # Función para extraer valor de un punto en cada raster
            valores_mensuales = []

            for path in archivos_raster:
                with rasterio.open(path) as src:
                    coords = [(lon, lat)]
                    for val in src.sample(coords):
                        valores_mensuales.append(val[0])

            # Calcular promedio anual y factores relativos
            valores_mensuales = np.array(valores_mensuales)
            promedio_anual = np.mean(valores_mensuales)
            factores_relativos = valores_mensuales / promedio_anual

            st.session_state['valores_mensuales']= valores_mensuales

            
            # Cálculos base
            # --------------------------
            # Producción mensual esperada por cada kWp instalado
            produccion_por_kWp = promedio_anual * factor_perdidas # ya está en kWh/kWp


            # Calcular el consumo promedio mensual
            consumo_promedio_kWh = df['Consumo subtotal'].mean()
            st.session_state['consumo_promedio_kWh']=consumo_promedio_kWh

            # Tamaño del sistema necesario
            tamano_sistema_kWp_completo = consumo_promedio_kWh / produccion_por_kWp

            # Tamaño del sistema necesario para cubrir el porcentaje deseado
            tamano_sistema_kWp = tamano_sistema_kWp_completo * objetivo_cobertura
            st.session_state['tamano_sistema_kWp'] = tamano_sistema_kWp
            
            # Producción mensual estimada (misma para todos los meses)
            produccion_mensual_real  = tamano_sistema_kWp * valores_mensuales
            produccion_mensual_prom = produccion_mensual_real.mean()

            ##########
            # Análisis económico
            tarifa_promedio_usd_kWh = st.session_state.get('tarifa_promedio_usd_kWh')
            
            inversion_usd = tamano_sistema_kWp * 1000 * costo_Wp

            ahorro_mensual = consumo_promedio_kWh * tarifa_promedio_usd_kWh
            ahorro_anual = ahorro_mensual * 12
            
            ############
            # Proyección a largo plazo
            # Parámetros de entrada
            incremento_tarifa = 0.02
            
            # Cálculos base
            produccion_prom_kWp_mes = radiacion_diaria * 30 * factor_perdidas
                        
            # Producción mensual por año
            produccion_anual = []
            tarifa_actual = tarifa_mas_impuestos

            for anio in range(1, años_proyecto + 1):
                produccion_mensual = tamano_sistema_kWp * produccion_prom_kWp_mes * factores_relativos  * (1 - 0.005) ** (anio - 1)
                produccion_anual_kwh = np.sum(produccion_mensual)
                
                ingreso_anual = produccion_anual_kwh * tarifa_actual
                ahorro_neto = ingreso_anual - mantenimiento_anual
                produccion_anual.append(ahorro_neto)
                
                tarifa_actual *= (1 + incremento_tarifa)

            # Indicadores económicos
            flujo_de_caja = [-inversion_usd] + produccion_anual

            # Verifica que no haya NaN ni Inf
            van = None
            if np.any(np.isnan(flujo_de_caja)) or np.any(np.isinf(flujo_de_caja)):
                st.error("⚠️ El flujo de caja contiene valores inválidos (NaN o Inf).")
                tir = None
            else:
                tir = npf.irr(flujo_de_caja)
                van = npf.npv(tasa_descuento, flujo_de_caja)
                flujo_acumulado = np.cumsum(flujo_de_caja)
                payback_anio = next((i for i, val in enumerate(flujo_acumulado) if val >= 0), "Más de 20 años")
                st.session_state['van']=van
                st.session_state['tir']=tir            

            interpretacion_van = ""
            if tir is not None and not np.isnan(tir) and not np.isinf(tir):
                if van > 0:
                    interpretacion_van = f"✅ Proyecto rentable (genera más de lo que cuesta)."
                elif van == 0:
                    interpretacion_van = f"🔄 Proyecto justo rentable."
                else:
                    interpretacion_van = f"❌ No rentable a esa tasa de descuento."

                interpretacion_tir = ""
                if tir > 0.08:
                    interpretacion_tir = f"✅ Rentable - Adelante con el proyecto."
                elif tir == 0.08:
                    interpretacion_tir = f"🔄 Rentabilidad justa - Evaluar con otros criterios."
                else:
                    interpretacion_tir = f"❌ No rentable - No se recomienda invertir."
                    st.markdown(f"**Payback:** {payback_anio} años")
            
            else:
                st.error("⚠️ El TIR contiene valores inválidos (NaN o Inf). Revisa los cálculos anteriores.")
            ########## Diseño de dashboard
            # Columnas
            left, right = st.columns([0.4, 0.6], vertical_alignment="top", border=True)

            left.markdown("## 📍 ¡Tu proyecto se encuetra aquí!")
            def mapa_ubic():
                mi_mapa = folium.Map(location = [lat, lon],tiles = 'OpenStreetMap', zoom_start=15)

                # Crear el contenido del popup como HTML con saltos de línea
                popup_html = (
                    f"🔢 Consumo mensual promedio: {consumo_promedio_kWh:.2f} kWh<br>"
                    f"📉 Mínimo: {consumo_min_kWh:.2f} kWh<br>"
                    f"📈 Máximo: {consumo_max_kWh:.2f} kWh<br>"
                    f"✅ Objetivo de cobertura: {objetivo_cobertura*100:.0f}%<br>"
                    f"☀️ Radiación solar diaria media: {radiacion_diaria:.2f} kWh/m²/día<br>"
                    f"🔧 Tamaño recomendado del sistema para cubrir el {objetivo_cobertura*100:.0f}% del consumo: {tamano_sistema_kWp:.2f} kWp<br>"
                    f"✅ Producción mensual estimada ({tamano_sistema_kWp:.2f} kWp): {produccion_mensual_prom:.2f} kWh<br>"
                    f"💸 Inversión inicial: ${inversion_usd:.2f}"
                )

                # Agregar un marcador con resumen de consumo
                mi_mapa.add_child(
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_html, max_width=1000),
                        icon=folium.Icon(color="blue")
                    )
                )

                return mi_mapa
            ##############################
            # Celdas del lado izquierdo
            # Mostrar mapa
            with left:
                folium_static(mapa_ubic())

            # Descripción de resultados
            with st.expander("📌 Resumen de resultados"):
                st.title('⚙️ Perfil de Consumo Eléctrico')
                st.subheader(f"\nPeriodo de análisis: {cant_meses} meses ({año_min}-{año_max})")
                st.write(f"\n🔢 Consumo mensual promedio: {consumo_promedio_kWh:.2f} kWh, con un mínimo de {consumo_min_kWh:.2f} kWh y un máximo de {consumo_max_kWh:.2f} kWh.")
                st.write(variacion())
                st.write(tipo_usuario())
                st.markdown(f"""
                <div style="font-size:17px;">
                    💵 Monto promedio por consumo: ${monto_promedio:.2f}, con un máximo de ${monto_max:.2f}.<br>
                </div>
                """, unsafe_allow_html=True)
                st.write(f"\n💸 Total promedio a pagar (incluye impuestos y tasas municipales): ${Total_pagar_promedio:.2f}.")
                st.write(f"\n💸 Tarifa promedio por el consumo: ${tarifa_promedio_usd_kWh:.3f}/kWh. En base a los datos.")
                st.write(f"\n💸 Tarifa promedio + impuestos: ${tarifa_mas_impuestos:.3f}/kWh. En base a los datos.\n")
                
                st.title('☀️ Condiciones Solares y Técnicas')
                st.write(f"✅ Radiación solar diaria media: {radiacion_diaria:.2f} kWh/m²/día)")
                st.write(f"\n✅ Producción mensual esperada por kWp: {produccion_por_kWp:.2f} kWh.")
                st.write(f"\n✅ Factor de pérdidas considerado: {(1-factor_perdidas)*100:.0f}% ({factor_perdidas} eficiencia).")
                
                st.title("📐 Dimensionamiento Recomendado")
                st.write(f"\n✅ Para satisfacer el 100% de la demanda se recomienda un sistema de aproximadamente {tamano_sistema_kWp_completo:.2f} kWp.")
                st.write(f"\n✅ Tamaño recomendado del sistema para cubrir el {objetivo_cobertura*100:.0f}% del consumo: {tamano_sistema_kWp:.2f} kWp.")
                st.write(f"\n✅ Producción mensual estimada ({tamano_sistema_kWp:.2f} kWp): {produccion_mensual_prom:.2f} kWh para todos los meses.")

                st.title('💸 Análisis Económico')
                st.write(f"\n✅ Costo referencial (USD/Wp): ${costo_Wp:.2f}")
                st.write(f"\n✅ Inversión estimada ({tamano_sistema_kWp:.2f} kWp): ${inversion_usd:,.2f}")
                st.write(f"\n✅ Ahorro anual: ${ahorro_anual:.2f}")

                st.title('📈 Proyección a Largo Plazo')
                st.write(f"\n🔧 Tamaño del sistema: {tamano_sistema_kWp:.2f} kWp")
                st.write(f"\n💸 Inversión inicial: ${inversion_usd:.2f}")
                if van != None:
                    st.write(f"\n📈 Valor Actual Neto - VAN (8%): ${van:.2f} {interpretacion_van}")
                    st.write(f"\n📊 Tasa Interna de Retorno - TIR: {tir*100:.1f}% {interpretacion_tir}")
                st.write(f"\n💰 Ahorro total neto en {vida_util} años: ${sum(produccion_anual):.2f}")
            
##############  CONVERSION DE GRAFICOS A PNG

            #def convertir_plotly_a_base64(fig):
            #    img_bytes = fig.to_image(format="png", width=800, height=400, engine="kaleido")
            #    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            #    return img_b64

##########################
            def crear_graficos_interactivos(df):
                df['Total_pagar']=df['Total_pagar'].fillna(0)
                df['Monto'] = df['Monto'].fillna(0)
                
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.15,
                    subplot_titles=("Costo mensual por año", "Consumo mensual por año")
                )

                # --- Gráfico 1: Total_pagar ---
                for año in df['Año'].unique():
                    data = df[df['Año'] == año]
                    fig.add_trace(
                        go.Scatter(
                            x=data['Mes'],
                            y=data['Total_pagar'],
                            mode='lines+markers',
                            name=f"Año {año} - $",
                            hovertemplate='Mes: %{x}<br>Monto: %{y:.2f} USD',
                        ),
                        row=1, col=1
                    )

                # Línea de promedio de pago
                promedio_pago = df['Total_pagar'].mean()
                fig.add_trace(
                    go.Scatter(
                        x=df['Mes'].unique(),
                        y=[promedio_pago]*len(df['Mes'].unique()),
                        mode='lines',
                        name=f"Promedio: {promedio_pago:.2f} USD",
                        line=dict(color='gray', dash='dash')
                    ),
                    row=1, col=1
                )

                # --- Gráfico 2: Consumo subtotal ---
                for año in df['Año'].unique():
                    data = df[df['Año'] == año]
                    fig.add_trace(
                        go.Scatter(
                            x=data['Mes'],
                            y=data['Consumo subtotal'],
                            mode='lines+markers',
                            name=f"Año {año} - kWh",
                            hovertemplate='Mes: %{x}<br>Consumo: %{y:.0f} kWh',
                        ),
                        row=2, col=1
                    )

                # Línea de promedio de consumo
                promedio_consumo = df['Consumo subtotal'].mean()
                fig.add_trace(
                    go.Scatter(
                        x=df['Mes'].unique(),
                        y=[promedio_consumo]*len(df['Mes'].unique()),
                        mode='lines',
                        name=f"Promedio: {promedio_consumo:.0f} kWh",
                        line=dict(color='gray', dash='dash')
                    ),
                    row=2, col=1
                )

                # Configuración general
                fig.update_layout(
                    height=500,
                    width=900,
                    #title_text="Análisis de Consumo y Costos Mensuales",
                    legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
                    margin=dict(t=80, b=30),
                )

                fig.update_xaxes(title_text="", row=2, col=1, tickangle=45, tickvals=list(range(1,13)), ticktext=[meses_es[i+1] for i in range(12)])
                fig.update_yaxes(title_text="Monto ($)", row=1, col=1)
                fig.update_yaxes(title_text="Consumo (kWh)", row=2, col=1)

                return fig

            #################
            # Gráfico de flujo de caja
            def mostrar_flujo_de_caja(flujo_de_caja, vida_util):
                años = list(range(vida_util + 1))
                flujo_acumulado = np.cumsum(flujo_de_caja)

                # Calcular indicadores financieros
     
                beneficio_total = sum(flujo_de_caja[1:])  # omitimos inversión inicial
                inversion_inicial = -flujo_de_caja[0]
                #b_c_ratio = beneficio_total / inversion_inicial if inversion_inicial != 0 else None

                # Calcular punto de equilibrio (Payback)
                flujo_acum = 0
                payback_anio = None
                for i, f in enumerate(flujo_de_caja):
                    flujo_acum += f
                    if flujo_acum >= 0:
                        payback_anio = i
                        break

                # Crear figura interactiva
                fig = go.Figure()

                # Flujo de caja por año (barras)
                fig.add_trace(go.Bar(
                    x=años,
                    y=flujo_de_caja,
                    name="Flujo de Caja",
                    marker_color='teal',
                    hovertemplate='Año %{x}<br>USD: %{y:,.2f}<extra></extra>'
                ))

                # Flujo de caja acumulado (línea)
                fig.add_trace(go.Scatter(
                    x=años,
                    y=flujo_acumulado,
                    mode='lines+markers',
                    name='Flujo Acumulado',
                    line=dict(color='orange', dash='dash'),
                    hovertemplate='Año %{x}<br>Acumulado: %{y:,.2f}<extra></extra>'
                ))

                # Línea de cero
                fig.add_shape(type='line',
                    x0=años[0], x1=años[-1], y0=0, y1=0,
                    line=dict(color='black', dash='dash')
                )

                # Línea vertical de payback
                if payback_anio is not None:
                    fig.add_vline(
                        x=payback_anio,
                        line_dash="dot",
                        line_color="red",
                        annotation_text=f"Payback Año {payback_anio}",
                        annotation_position="top left"
                    )

                # Diseño del gráfico
                fig.update_layout(
                    title=f"💰 Flujo de Caja del Proyecto Fotovoltaico ({vida_util} años)",
                    xaxis_title="Año",
                    yaxis_title="USD",
                    template='plotly_white',
                    height=450
                )

                return fig
            # Mostrar indicadores financieros clave
            if van != None:
                st.subheader("📊 Indicadores Financieros")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("VAN", f"${van:,.2f}")
                col2.metric("TIR", f"{tir:.2%}")
                col3.metric("Payback", f"Año {payback_anio}" if payback_anio is not None else "No recuperado")
                
            ##################
            def cobertura_solar():
                # Convertir los valores mensuales a un diccionario: {mes: generación promedio}
                generacion_por_mes = {i+1: val for i, val in enumerate(valores_mensuales)}

                # Asignar la generación estimada por fila, según el mes correspondiente
                df['Generacion estimada (kWh)'] = df['Mes_num'].map(generacion_por_mes) * tamano_sistema_kWp

                # Calcular cobertura y excedente
                df['Cobertura (%)'] = (df['Generacion estimada (kWh)'] / df['Consumo subtotal']) * 100
                df['Excedente (kWh)'] = df['Generacion estimada (kWh)'] - df['Consumo subtotal']
                df['Excedente (kWh)'] = df['Excedente (kWh)'].apply(lambda x: x if x > 0 else 0)

                # Crear figura
                fig = go.Figure()

                # Cobertura mensual (%)
                fig.add_trace(go.Bar(
                    x=df['Fecha'],
                    y=df['Cobertura (%)'],
                    name='Cobertura mensual (%)',
                    marker_color='green',
                    text=df['Cobertura (%)'].round(1).astype(str) + '%',
                    textposition='outside',
                ))

                # Excedente mensual (kWh)
                fig.add_trace(go.Bar(
                    x=df['Fecha'],
                    y=df['Excedente (kWh)'],
                    name='Excedente mensual (kWh)',
                    marker_color='rgba(255, 100, 100, 0.7)',
                    text=df['Excedente (kWh)'].round(1),
                    textposition='outside',
                ))

                # Diseño del gráfico
                fig.update_layout(
                    title='☀️ Cobertura solar y excedente mensual',
                    xaxis_title=None,
                    yaxis_title='Porcentaje (%) / Energía (kWh)',
                    barmode='group',
                    bargap=0.2,
                    uniformtext_minsize=8,
                    uniformtext_mode='hide',
                    legend=dict(x=0.5, xanchor='center', orientation='h')
                )
                st.plotly_chart(fig, use_container_width=True, key="grafico_cobertura_solar")
                ################### 
            def cobertura_solar_para_pdf():
                df = st.session_state.get("df").copy()
                valores_mensuales = st.session_state.get("valores_mensuales")
                tamano_sistema_kWp = st.session_state.get("tamano_sistema_kWp")

                # Convertir a diccionario mes → valor
                generacion_por_mes = {i + 1: val for i, val in enumerate(valores_mensuales)}

                # Agregar columnas al DataFrame
                df['Generacion estimada (kWh)'] = df['Mes_num'].map(generacion_por_mes) * tamano_sistema_kWp
                df['Cobertura (%)'] = (df['Generacion estimada (kWh)'] / df['Consumo subtotal']) * 100
                df['Excedente (kWh)'] = (df['Generacion estimada (kWh)'] - df['Consumo subtotal']).clip(lower=0)

                # Guardar en session_state por si hace falta
                st.session_state["df"] = df

                # Crear gráfico
                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=df['Mes'],
                    y=df['Cobertura (%)'],
                    name='Cobertura mensual (%)',
                    marker_color='green',
                    text=df['Cobertura (%)'].round(1).astype(str) + '%',
                    textposition='outside',
                ))

                fig.add_trace(go.Bar(
                    x=df['Mes'],
                    y=df['Excedente (kWh)'],
                    name='Excedente mensual (kWh)',
                    marker_color='rgba(255, 100, 100, 0.7)',
                    text=df['Excedente (kWh)'].round(1),
                    textposition='outside',
                ))

                fig.update_layout(
                    title='☀️ Cobertura solar y excedente mensual',
                    xaxis_title='',
                    yaxis_title='Porcentaje (%) / Energía (kWh)',
                    barmode='group',
                    bargap=0.2,
                    height=400,
                    margin=dict(t=40, b=40),
                    legend=dict(x=0.5, xanchor='center', orientation='h')
                )

                return fig


############### OBTENER GRAFICOS PNG
            # Obtener y convertir los gráficos
            fig1 = crear_graficos_interactivos(st.session_state["df"])
            fig2 = mostrar_flujo_de_caja(flujo_de_caja, vida_util)
            fig3 = cobertura_solar_para_pdf()

            grafico_consumo_b64 = fig1.to_html(full_html=False, include_plotlyjs='cdn')
            grafico_flujo_b64 = fig2.to_html(full_html=False, include_plotlyjs='cdn')
            grafico_cobertura_b64 = fig3.to_html(full_html=False, include_plotlyjs='cdn')


            ###############
            def interpretacion_tecnica():
                cobertura = int(st.session_state.get("objetivo_cobertura", 0) * 100)
                tamano = st.session_state.get("tamano_sistema_kWp", 0)
                consumo = st.session_state.get("consumo_promedio_kWh", 0)
                ahorro = st.session_state.get("tarifa_promedio_usd_kWh", 0) * consumo * 12
                tir = st.session_state.get("tir", None)
                van = st.session_state.get("van", None)

                df = st.session_state.get("df")
                excedente = 0
                if df is not None and "Excedente (kWh)" in df.columns:
                    excedente = df["Excedente (kWh)"].mean()

                frases = []

                # 1. Cobertura del sistema
                if cobertura >= 90:
                    frases.append(f"El sistema propuesto está diseñado para cubrir casi la totalidad del consumo eléctrico anual ({cobertura}%), brindando alta independencia energética.")
                elif cobertura >= 50:
                    frases.append(f"El sistema cubrirá aproximadamente el {cobertura}% del consumo eléctrico, lo que permite una reducción significativa en la factura de electricidad.")
                else:
                    frases.append(f"Se ha dimensionado un sistema que cubre el {cobertura}% del consumo, ideal para usuarios que buscan reducir costos sin realizar una inversión total.")

                # 2. Tamaño del sistema
                if tamano <= 2:
                    frases.append("La potencia del sistema es baja, lo cual lo hace económicamente accesible y adecuado para residencias pequeñas o con espacio limitado.")
                elif tamano <= 5:
                    frases.append("El sistema tiene un tamaño intermedio, adecuado para hogares de consumo medio o familias de 3 a 5 personas.")
                else:
                    frases.append("Se requiere un sistema de mayor capacidad, lo que sugiere un consumo elevado o la posibilidad de ampliar la infraestructura.")

                # 3. Ahorro estimado
                if ahorro >= 300:
                    frases.append(f"Se estima un ahorro anual de aproximadamente ${ahorro:.2f}, lo cual contribuye significativamente a la economía familiar a mediano plazo.")
                else:
                    frases.append(f"El ahorro anual estimado es de unos ${ahorro:.2f}, útil para reducir gastos, aunque el retorno de inversión puede ser moderado.")

                # 4. Recomendación de tipo de conexión
                if cobertura < 50:
                    tipo_conexion = "Autoconsumo simple (inyección cero)"
                elif cobertura >= 50 and excedente < 20:
                    tipo_conexion = "Net Billing (facturación neta con baja inyección)"
                elif excedente >= 20:
                    tipo_conexion = "Net Metering (compensación total con saldo energético)"
                else:
                    tipo_conexion = "Autoconsumo parcial con mínima inyección"
                frases.append(f"Recomendación técnica: se sugiere optar por <strong>{tipo_conexion}</strong> considerando el perfil de consumo y excedente estimado.")            
                # 5. Evaluación financiera (TIR y VAN)
                if tir is not None and van is not None:
                    tir_pct = tir * 100
                    if tir > 0.08 and van > 0:
                        frases.append(f"El proyecto es <strong>financieramente viable</strong>, con un TIR del {tir_pct:.1f}% y un VAN positivo de ${van:,.2f}.")
                    elif tir > 0.05:
                        frases.append(f"La rentabilidad es <strong>moderada</strong> (TIR: {tir_pct:.1f}%, VAN: ${van:,.2f}), puede mejorar con incentivos o ajustes.")
                    else:
                        frases.append(f"<strong>No se recomienda la inversión</strong> bajo condiciones actuales (TIR: {tir_pct:.1f}%, VAN: ${van:,.2f}).")

                # Unir y devolver
                return " ".join(frases)
######
            def glosario_conexion_solar(interpretacion_texto):
                glosario = ""

                definiciones = {
                    "Autoconsumo simple": "🔌 <strong>Autoconsumo simple (inyección cero):</strong> Usas directamente la energía solar que produces, pero no inyectas nada a la red eléctrica. Ideal para reducir la factura sin acuerdos adicionales.",
                    "Net Billing": "<strong>Net Billing (facturación neta):</strong> La energía solar que no consumes se inyecta a la red, y la empresa eléctrica te descuenta un valor en tu factura. Te pagan por lo que aportas, aunque a menor tarifa.",
                    "Net Metering": "<strong>Net Metering (medición neta):</strong> Permite guardar el excedente como un 'saldo de energía' para usarlo después. Muy justo, pero requiere acuerdos y medidor especial.",
                    "Autoconsumo parcial con mínima inyección": "<strong>Autoconsumo parcial con mínima inyección:</strong> Tu sistema cubre parte del consumo y genera muy poco excedente. Útil si tienes poco espacio o deseas una solución balanceada."
                }

                # Verificar qué términos aparecen en la interpretación
                for clave, definicion in definiciones.items():
                    if clave in interpretacion_texto:
                        glosario += f"<p>{definicion}</p>\n"

                return glosario

##############
            
            variacion = variacion()
            st.session_state['variacion'] = variacion
            def generar_reporte_pdf_con_xhtml2pdf():
                df = st.session_state.get("df")
                valores_mensuales = st.session_state.get("valores_mensuales", [])
                tamano_sistema_kWp = st.session_state.get("tamano_sistema_kWp", 0)
                tarifa_promedio = st.session_state.get("tarifa_promedio_usd_kWh", 0)
                produccion_total = tamano_sistema_kWp * sum(valores_mensuales)
                consumo_promedio = st.session_state.get("consumo_promedio_kWh", 0)
                ahorro_anual = tarifa_promedio * consumo_promedio * 12

                lat = st.session_state.get("lat")
                lon = st.session_state.get("lon")
                interpretacion = interpretacion_tecnica()
                glosario = glosario_conexion_solar(interpretacion)
                variacion = st.session_state.get("variacion")

                html = f"""
                <html>
                <head>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            font-size: 12px;
                            padding: 10px;
                        }}
                        h1 {{
                            color: #003366;
                        }}
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                            margin-top: 15px;
                        }}
                        th, td {{
                            border: 1px solid #ccc;
                            padding: 8px;
                            text-align: left;
                        }}
                        th {{
                            background-color: #f2f2f2;
                        }}
                    </style>
                </head>
                <body>
                    <h1>Reporte Técnico - Sistema Fotovoltaico On-Grid</h1>

                    <h4>Periodo de análisis: {cant_meses} meses ({año_min}-{año_max})</h4>
                    <p>Consumo mensual promedio: {consumo_promedio_kWh:.2f} kWh, con un mínimo de {consumo_min_kWh:.2f} kWh y un máximo de {consumo_max_kWh:.2f} kWh.<br>
                    {variacion}</p>
                    <h2>Ubicación</h2>
                    <p><strong>Latitud:</strong> {lat}<br>
                    <strong>Longitud:</strong> {lon}<br>
                    Radiación solar diaria media: {radiacion_diaria:.2f} kWh/m²/día)</p>

                    <h2>Datos de Entrada</h2>
                    <ul>
                        <li>Consumo mensual promedio: <strong>{consumo_promedio:.2f} kWh</strong></li>
                        <li>Tarifa promedio (incl. impuestos): <strong>${tarifa_promedio:.3f}/kWh</strong></li>
                        <li>Objetivo de cobertura: <strong>{int(st.session_state.get('objetivo_cobertura', 0)*100)}%</strong></li>
                    </ul>
                    
                    <h2>Análisis de Consumo Eléctrico Mensual</h2>
                    <img src="data:image/png;base64,{grafico_consumo_b64}" width="700"/>

                    <h2>Dimensionamiento</h2>
                    <ul>
                        <li>Tamaño del sistema: <strong>{tamano_sistema_kWp:.2f} kWp</strong></li>
                        <li>Producción mensual estimada: <strong>{produccion_total:.2f} kWh</strong></li>
                        <li>Ahorro anual estimado: <strong>${ahorro_anual:.2f}</strong></li>
                    </ul>
                    <h2>Flujo de Caja del Proyecto</h2>
                    <img src="data:image/png;base64,{grafico_flujo_b64}" width="700"/>

                    <h2>Interpretación Técnica</h2>
                    <img src="data:image/png;base64,{grafico_cobertura_b64}" width="700"/>
                    <p>{interpretacion}</p>
                    
                    <h2>Glosario</h2>
                    {glosario}

                    <p style="margin-top: 30px;">Generado automáticamente por la app <strong>Solar OnGrid</strong> - Alejandro H.</p>
                </body>
                </html>
                """

                # Convertir HTML a PDF en memoria
                result_pdf = io.BytesIO()
                pisa_status = pisa.CreatePDF(io.StringIO(html), dest=result_pdf)

                if not pisa_status.err:
                    result_pdf.seek(0)
                    b64_pdf = base64.b64encode(result_pdf.read()).decode("utf-8")
                    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="reporte_solar.pdf">📄 Descargar reporte PDF</a>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.error("❌ Error al generar el PDF.")


            ################
            
            with right:
                # Mostrar gráfico
                right.markdown("## 📊 Análisis de Consumo Eléctrico Mensual")
                with st.container():
                    fig_consumo_energia = crear_graficos_interactivos(df)
                    st.plotly_chart(fig_consumo_energia, use_container_width=True, key="grafico_consumo_mensual")

            st.title('📈 Proyección a futuro')
            with st.container(border=True):
                # Mostrar el gráfico
                fig_flujo_caja=mostrar_flujo_de_caja(flujo_de_caja, vida_util)
                # Mostrar gráfico
                st.plotly_chart(fig_flujo_caja, use_container_width=True, key="grafico_flujo_caja_proyecto")

            with st.container(border=True):    
                cobertura_solar()

            with st.container(border=True):
                st.subheader("📄 Generar Reporte en PDF")
                if st.button("✅ Crear reporte técnico PDF"):
                    generar_reporte_pdf_con_xhtml2pdf()

            
        else:
            st.warning("⚠️ El archivo está vacío o no se pudo procesar.")
    else:
        st.info("📭 Aún no se han cargado datos.")
    





if __name__=='__main__':
    main()
