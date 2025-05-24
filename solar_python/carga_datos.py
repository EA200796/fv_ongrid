import streamlit as st
import pandas as pd
import datetime
import io # para crear buffer en memoria

def subida_formato():
    st.subheader("Sube un archivo con tu información")
    st.info("Utiliza el formato a continuación, en donde podrás ingresar tus datos de consumo de energía mensuales obtenidos de tus facturas.",icon="ℹ️")
    ruta_archivo = 'C:/Users/Dell/Documents/Analisis_Datos/VCode/solar_python/formato_ingreso_datos.xlsx'
    st.session_state["archivo_datos"] = None
    with open(ruta_archivo, "rb") as f:
        st.download_button(
            label='Descargar formato de archivo',
            data= f,
            file_name= "formato.xlsx",
            mime= "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            on_click="ignore",
            icon="📥"
            )
    # uploader    
    archivo_datos = st.file_uploader("Subir tu archivo CSV o Excel:", type = ["csv", "xlsx"])
    if archivo_datos:
        st.session_state["archivo_datos"] = archivo_datos
    
    return archivo_datos


def subida_tabla():
    st.title('Tabla de datos')
    st.info('En la siguiente tabla podrás ingresar tus datos de consumo de energía mensuales obtenidos de tus facturas.',icon='ℹ️')
    
    # Inicializar estado si es necesario
    st.session_state["archivo_datos"] = None
    
    # DataFrame de ejemplo
    df_default = pd.DataFrame({
        "Factura": [f"FACT_2023_{i+1}" for i in range(12)],
        "Fecha": [datetime.date(2023, i+1, 24 if i != 1 else 28) for i in range(12)],
        "Consumo subtotal": [82, 71, 73, 70, 67, 63, 77, 81, 64, 62, 65, 62],
        "Monto": [7.53, 6.5, 6.69, 6.41, 6.13, 5.75, 7.06, 7.43, 5.85, 5.67, 5.95, 5.67],
        "Total_pagar": [8.66, 7.95, 8.08, 7.88, 7.69, 8.03, 8.82, 9.05, 8.08, 7.97, 8.14, 7.97]
    })

    # Mostrar editor de tabla editable
    edited_df = st.data_editor(
        df_default,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Fecha": st.column_config.DateColumn(
                help="Fecha de emisión de la factura",
                format="DD.MM.YYYY"
            ),
            "Consumo subtotal": st.column_config.NumberColumn(
                help= "Consumo de energía en kWh"

            ),
            "Monto": st.column_config.NumberColumn(
                help="Costo del servicio eléctrico sin impuestos"
            ),
            "Total_pagar": st.column_config.NumberColumn(
                help="Costo del servicio eléctrico con impuestos"
            )
        }
    )

    # Guardar el DataFrame editado en session_state
    st.session_state["df"] = edited_df
    
    archivo_datos = edited_df
    
    # Convertir DataFrame a archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        archivo_datos.to_excel(writer, index=False, sheet_name="Datos")

    # Reposicionar el cursor al inicio del buffer
    output.seek(0)

    # Botón de descarga
    st.download_button(
        label="📤 Descargar archivo Excel",
        data=output,
        file_name="formato_ingresado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.session_state["archivo_datos"] = archivo_datos
    return archivo_datos

        
def subida_checkbox():
    st.title('🧰 Selección de aparatos eléctricos en el hogar')
    st.info('Selecciona los aparatos que usas en tu hogar e ingresa cuántas horas al día los usas.',icon='ℹ️')
    st.session_state["archivo_datos"] = None
    precio_sin_impuesto = st.number_input(
        label="💸 Precio de electricidad (sin impuestos)",
        min_value= 0.000,
        max_value= 10.000,
        step=0.001,
        format= "%0.003f",
        help="Este valor lo puedes encontrar en tu factura",
        value= 0.092
        )
    precio_impuesto = st.number_input(
        label="💸 Precio de electricidad (con impuestos)",
        min_value= 0.000,
        max_value= 10.000,
        step=0.001,
        format= "%0.003f",
        help="Este valor lo puedes encontrar en tu factura",
        value= 0.117
        )

    # Diccionario con aparatos y su potencia (en watts)
    aparatos_comunes = {
        "Foco LED": 10,
        "TV (LED)": 80,
        "Refrigeradora (familiar)": 150,
        "Ventilador": 50,
        "Cargador de celular": 5,
        "Computadora portátil": 65,
        "Computadora de escritorio": 200,
        "Microondas": 1200,
        "Licuadora": 400,
        "Plancha de ropa": 1200,
        "Lavadora (sin calentador)": 500,
        "Lavadora (con calentador)": 2000,
        "Secadora de ropa": 3000,
        "Hervidor eléctrico": 1800,
        "Cafetera": 900,
        "Aspiradora": 1400,
        "Tostadora": 800,
        "Estufa eléctrica (1 hornilla)": 1200,
        "Estufa eléctrica (4 hornillas)": 4000,
        "Ducha eléctrica": 3500,
        "Calefactor": 1500,
        "Aire acondicionado (pequeño)": 900,
        "Aire acondicionado (grande)": 1800,
        "Congelador": 200,
        "Módem de internet": 10,
        "Impresora (doméstica)": 60
    }

    # Recoger selección
    consumo = []
    st.markdown("### Selección de aparatos y horas de uso:")
    for aparato, potencia in aparatos_comunes.items():
        if st.checkbox(f"{aparato} ({potencia} W)", key=aparato):
            cantidad = st.number_input(f"🔢 Cantidad de {aparato}", min_value=1, step=1, key=f"cantidad_{aparato}")
            horas = st.number_input(f"⏱️ Horas de uso diario para {aparato}", min_value=0.0, max_value=24.0, step=0.5, key=f"horas_{aparato}")
            consumo_diario_kWh = (potencia * horas * cantidad) / 1000  # Wh a kWh
            Monto = (consumo_diario_kWh * precio_sin_impuesto)
            Total_pagar = (consumo_diario_kWh * precio_impuesto)
            consumo.append({
                "Aparato": aparato,
                "Potencia_W": potencia,
                "Cantidad": cantidad,
                "Horas_día": horas,
                "Consumo subtotal": consumo_diario_kWh,
                "Monto": Monto,
                "Total_pagar": Total_pagar
            })

    # Mostrar resultados si hay selección
    if consumo:
        df_consumo = pd.DataFrame(consumo)
        total = df_consumo["Consumo subtotal"].sum()
        st.markdown("### 📊 Consumo estimado diario")
        st.dataframe(df_consumo, use_container_width=True)
        st.metric(label="🔋 Consumo total estimado", value=f"{total:.2f} kWh/día")

        # Guardar en session_state para uso posterior
        archivo_datos = df_consumo
        
        st.session_state["archivo_datos"] = archivo_datos
        st.session_state["df"] = df_consumo

        st.session_state["archivo_datos"] = archivo_datos
        return archivo_datos
    
    else:
        st.info("Selecciona al menos un aparato para calcular el consumo.")
        return None