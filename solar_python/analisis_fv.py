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

# Configuración inicial
## Titulo de la pestaña y configuracion de la bara lateral
st.set_page_config(page_title= 'Solar OnGrid', layout= 'wide', initial_sidebar_state= "collapsed")


def main ():
    # Título de pagina
    st.title('Factibilidad de Sistema On-Grid Fotovoltaico en Ecuador')
    
    # Configutación de barra lateral
    st.sidebar.header('🧾 Ingreso de datos') # título

    ################
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
    opciones_porcentaje = np.round(np.arange(0, 100.5, 0.5), 1).tolist()

    objetivo_cobertura = st.sidebar.select_slider(
        "✅ Objetivo de cobertura (%):", 
        options= opciones_porcentaje,
        value= 75.0 # valor predeterminado
        )
    objetivo_cobertura = objetivo_cobertura/100
    factor_perdidas = st.sidebar.select_slider(
        "✅ Factor de pérdidas (%):",
        options= opciones_porcentaje,
        value= 20
        )
    factor_perdidas = (100 - factor_perdidas)/100

    vida_util = st.sidebar.number_input('Vida útil (años):',
        min_value= 0,
        max_value= 30,
        value=25)

    mantenimiento_anual = st.sidebar.number_input('Mantenimiento anual ($):',
        min_value= 0,
        max_value= 100, 
        value=20)
       
    # Cargador de archivos
    archivo_datos = st.sidebar.file_uploader("Subir CSV o Excel:", type = ["csv", "xlsx"])
    
    if archivo_datos is not None:
        tipo_archivo = archivo_datos.type
        
        # Verificar el tipo de archivo y cargarlo
        if tipo_archivo == "text/csv":
            df = pd.read_csv(archivo_datos)
        elif tipo_archivo == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            df = pd.read_excel(archivo_datos)
        else:
            st.warning("Formato de archivo no compatible")
            df = pd.DataFrame()
        
        # Guardar el DataFrame en `session_state`
        st.session_state['df'] = df
         
        # Mostrar el DataFrame
        if not df.empty:
                      
            # Elimnación de espacios innecesarios (principio y final)
            df.columns = df.columns.str.strip()

            # Se cambia la columna 'Fecha' a tipo datetime
            df['Fecha']=pd.to_datetime(df['Fecha'], format = 'mixed')

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
            
            tarifa_mas_impuestos_ctvs = (pago_total_promedio_usd / consumo_promedio_kWh)*100
            
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
                
                descripcion_variacion = f"\n📈 Variación anual de consumo: ±{consumo_std_kWh:.2f} kWh ({porcentaje_variacion*100:.2f}%) {clasificacion_variacion}"
                return descripcion_variacion
            #---
            # Descripción del usuario
            def tipo_usuario():
                class_usuario = ""
                if consumo_promedio_kWh >50 and consumo_promedio_kWh < 120:
                    class_usuario = "Residencial urbano, inyección cero recomendada."
                elif consumo_promedio_kWh > 120 and class_usuario < 800:
                    class_usuario = "Comercio mediano, Net billing posible."
                elif consumo_promedio_kWh > 800 and class_usuario < 5000:
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
            costo_Wp = 1.20
            inversion_usd = tamano_sistema_kWp * 1000 * costo_Wp

            ahorro_mensual = consumo_promedio_kWh * tarifa_promedio_usd_kWh
            ahorro_anual = ahorro_mensual * 12
            payback = inversion_usd / ahorro_anual

            ############
            # Proyección a largo plazo
            # Parámetros de entrada
            #vida_util = 25
            incremento_tarifa = 0.02
            #mantenimiento_anual = 20

            # Cálculos base
            produccion_prom_kWp_mes = radiacion_diaria * 30 * factor_perdidas
            sistema_kwp = (consumo_promedio_kWh * objetivo_cobertura) / produccion_prom_kWp_mes
            costo_total = sistema_kwp * 1000 * costo_Wp

            # Producción mensual por año
            produccion_anual = []
            tarifa_actual = tarifa_mas_impuestos

            for anio in range(1, vida_util + 1):
                produccion_mensual = sistema_kwp * produccion_prom_kWp_mes * factores_relativos  * (1 - 0.005) ** (anio - 1)
                produccion_anual_kwh = np.sum(produccion_mensual)
                
                ingreso_anual = produccion_anual_kwh * tarifa_actual
                ahorro_neto = ingreso_anual - mantenimiento_anual
                produccion_anual.append(ahorro_neto)
                
                tarifa_actual *= (1 + incremento_tarifa)

            # Indicadores económicos
            flujo_de_caja = [-costo_total] + produccion_anual

            # Verifica que no haya NaN ni Inf
            if np.any(np.isnan(flujo_de_caja)) or np.any(np.isinf(flujo_de_caja)):
                st.error("⚠️ El flujo de caja contiene valores inválidos (NaN o Inf).")
                tir = None
            else:
                tir = npf.irr(flujo_de_caja)

            van = npf.npv(0.08, flujo_de_caja)
            

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
            else:
                st.error("⚠️ El TIR contiene valores inválidos (NaN o Inf). Revisa los cálculos anteriores.")
            ########## Diseño de dashboard
            # Columnas
            left, right = st.columns(2, vertical_alignment="top", border=True)

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
                    f"💸 Inversión inicial: ${costo_total:.2f}"
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
                st.write(f"\n💸 Tarifa promedio por el consumo: ${tarifa_promedio_usd_kWh:.3f}/kWh.")
                st.write(f"\n💸 Tarifa promedio + impuestos: ${tarifa_mas_impuestos:.3f}/kWh.\n")
                
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
                st.write(f"\n✅Tiempo de retorno de inversión (payback): {payback:.1f} años")

                st.title('📈 Proyección a Largo Plazo')
                st.write(f"\n🔧 Tamaño del sistema: {sistema_kwp:.2f} kWp")
                st.write(f"\n💸 Inversión inicial: ${costo_total:.2f}")
                st.write(f"\n📈 Valor Actual Neto - VAN (8%): ${van:.2f} {interpretacion_van}")
                st.write(f"\n📊 Tasa Interna de Retorno - TIR: {tir*100:.1f}% {interpretacion_tir}")
                st.write(f"\n💰 Ahorro total neto en 25 años: ${sum(produccion_anual):.2f}")
            

            def crear_graficos_interactivos(df):
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

                fig.update_xaxes(title_text="Mes", row=2, col=1, tickangle=45, tickvals=list(range(1,13)), ticktext=[meses_es[i+1] for i in range(12)])
                fig.update_yaxes(title_text="Monto ($)", row=1, col=1)
                fig.update_yaxes(title_text="Consumo (kWh)", row=2, col=1)

                return fig

            #################
            # Gráfico de flujo de caja
            def mostrar_flujo_de_caja(flujo_de_caja, vida_util, tasa_descuento=0.08):
                años = list(range(vida_util + 1))
                flujo_acumulado = np.cumsum(flujo_de_caja)

                # Calcular indicadores financieros
     
                beneficio_total = sum(flujo_de_caja[1:])  # omitimos inversión inicial
                inversion_inicial = -flujo_de_caja[0]
                b_c_ratio = beneficio_total / inversion_inicial if inversion_inicial != 0 else None

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

                # Mostrar gráfico
                st.plotly_chart(fig, use_container_width=True)

                # Mostrar indicadores financieros clave
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
                st.plotly_chart(fig, use_container_width=True)


            ###############
            
            with right:
                # Mostrar gráfico
                right.markdown("## 📊 Análisis de Consumo Eléctrico Mensual")
                with st.container():
                    fig1 = crear_graficos_interactivos(df)
                    st.plotly_chart(fig1, use_container_width=True)

            st.title('📈 Proyección a futuro')
            with st.container(border=True):
                # Mostrar el gráfico
                mostrar_flujo_de_caja(flujo_de_caja, vida_util)
            with st.container(border=True):    
                cobertura_solar()
        else:
            st.warning("El archivo está vacío o no se pudo procesar.")
    else:
        st.info("No se ha cargado ningún archivo.")
    





if __name__=='__main__':
    main()
