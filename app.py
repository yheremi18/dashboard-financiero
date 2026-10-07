import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Configuración de página y CSS
st.set_page_config(page_title="FCF Sensibilidad", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .kpi-container { display: flex; justify-content: space-between; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
    .kpi-card {
        background-color: #121826; border-top: 3px solid #00d2ff;
        border-radius: 8px; padding: 15px; flex: 1 1 calc(33% - 15px); min-width: 250px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 10px;
    }
    .kpi-title { color: #94a3b8; font-size: 0.85rem; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 5px; }
    .kpi-val { color: #00d2ff; font-size: 1.8rem; font-weight: 700; margin-bottom: 5px; }
    .kpi-sub { color: #64748b; font-size: 0.75rem; }
    .kpi-delta { color: #10b981; font-size: 0.75rem; font-weight: 600; margin-top: 8px; }
    .main-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 30px; }
    .main-title { color: #ffffff; font-size: 2rem; font-weight: 700; margin: 0; }
    .main-subtitle { color: #94a3b8; font-size: 0.9rem; margin: 0; }
    [data-testid="stSidebar"] { background-color: #0b111a; border-right: 1px solid #1e293b; }
    </style>
""", unsafe_allow_html=True)

# 2. Gestión de Estados y Escenarios
escenarios_dict = {
    'Optimista': {'crec': 7.0, 'precio': 1050.0, 'share': 14.0, 'mp': 33.0, 'mod': 12.0},
    'Base': {'crec': 4.0, 'precio': 900.0, 'share': 10.0, 'mp': 37.0, 'mod': 14.0},
    'Pesimista': {'crec': 2.0, 'precio': 850.0, 'share': 9.0, 'mp': 40.0, 'mod': 15.5}
}

if 'crec' not in st.session_state:
    for k, v in escenarios_dict['Base'].items():
        st.session_state[k] = v

def update_escenario():
    esc = st.session_state.escenario_sel
    for k, v in escenarios_dict[esc].items():
        st.session_state[k] = v

# 3. Panel Lateral (Sidebar)
with st.sidebar:
    st.markdown("### ⚙️ Controles de Escenario")
    st.selectbox("Escenario Operativo", ["Base", "Optimista", "Pesimista"], key="escenario_sel", on_change=update_escenario)
    
    st.markdown("### 💰 Inversión y Activos")
    inv_inicial = st.number_input("Inversión Inicial (US$)", value=12000000, step=1000000)
    cap_adic = st.number_input("Inversión Anual Adicional (US$)", value=1000000, step=100000)
    anios_cap = st.slider("Años con inversión adicional", 0, 7, 5)
    valor_rescate = st.number_input("Valor venta de activo (Año 7)", value=4780000, step=100000)

    st.markdown("### 📊 Parámetros de Sensibilidad")
    crec = st.slider("Crecimiento de Mercado (%)", -5.0, 15.0, key="crec", step=0.5)
    precio = st.slider("Precio (US$/Tn)", 700.0, 1200.0, key="precio", step=10.0)
    share = st.slider("Share de Mercado (%)", 5.0, 25.0, key="share", step=0.5)
    mp = st.slider("Costo de MP (% ventas)", 20.0, 55.0, key="mp", step=0.5)
    mod = st.slider("Costo de MOD (% ventas)", 5.0, 30.0, key="mod", step=0.5)
    
    with st.expander("🔄 EFE (Capital de Trabajo)", expanded=False):
        ppc = st.number_input("Inversión en clientes (PPC días)", value=90)
        ppi = st.number_input("Inventarios (PPI días)", value=60)
        ppp = st.number_input("Proveedores (PPP días)", value=80)
        pct_efectivo = st.number_input("Efectivo (% de ventas)", value=1.80) / 100
        dias_base = st.number_input("Base de cálculo anual (días)", value=360)
        recup_wk = st.number_input("Recupero Capital de trabajo (%)", value=90.0) / 100

    with st.expander("🏦 Estructura de Capital y Tasas", expanded=False):
        pct_pasivo = st.number_input("Pasivo (%)", value=60.0) / 100
        plazo_credito = st.number_input("Plazo crédito (años)", value=7)
        kd = st.number_input("Costo deuda antes imp. (%)", value=8.0) / 100
        tasa_imp = st.number_input("Tasa Impositiva (%)", value=30.0) / 100
        r_pais = st.number_input("Riesgo País (%)", value=2.25) / 100
        rf = st.number_input("Rentabilidad activo sin riesgo (%)", value=3.0) / 100
        prima = st.number_input("Prima de mercado (%)", value=5.3) / 100
        beta_desapalancada = st.number_input("Beta desapalancada", value=1.11)

    with st.expander("⚙️ Gastos Operativos", expanded=False):
        gg_base = st.number_input("Gastos Generales Año 1 ($)", value=800000.0)
        gg_crec = st.number_input("Crecimiento Gastos Grales (%)", value=5.0) / 100
        pct_ventas = st.number_input("Comisiones de ventas (%)", value=3.0) / 100
        pct_transp = st.number_input("Gastos Transporte (%)", value=2.0) / 100

def calc_tir(flujos):
    min_r, max_r, guess = -0.99, 2.0, 0.1
    for _ in range(100):
        npv = sum(cf / ((1 + guess) ** i) for i, cf in enumerate(flujos))
        if abs(npv) < 0.0001: return guess
        if npv > 0: min_r = guess
        else: max_r = guess
        guess = (min_r + max_r) / 2
    return guess

# 4. Motor Matemático
def calcular_modelo(p_crec, p_precio, p_share, p_mp, p_mod):
    pct_patrimonio = 1 - pct_pasivo
    d_e = pct_pasivo / pct_patrimonio if pct_patrimonio > 0 else 0
    beta_apalancada = beta_desapalancada * (1 + (1 - tasa_imp) * d_e)
    ke = rf + (beta_apalancada * prima) + r_pais
    kd_post = kd * (1 - tasa_imp)
    wacc = (ke * pct_patrimonio) + (kd_post * pct_pasivo)

    flujo_caja, acumulado, resultados, detalle_efe, amortizacion = [-inv_inicial], [-inv_inicial], [], [], []
    
    # ESTRUCTURA EXACTA DE TABLA PARA EL DASHBOARD
    datos_tabla = {
        'Concepto': [
            'Ingresos', 'Costo de Materias Primas', 'Costo de Mano de Obra Directa', 'Margen bruto',
            'Gastos Generales', 'Gastos de Ventas', 'Gastos de Transporte', 'EBITDA',
            'Depreciación', 'EBIT', 'Impuestos', 'Depreciacion', 'NOPAT', 'CAPEX',
            'Inversion en Capital de trabajo', 'Valor de rescate', 'Recuperacion capital de trabajo',
            'FCF', 'valor presente flujo', 'Recupero descontado'
        ]
    }
    for i in range(8):
        datos_tabla[f'Año {i}'] = [None] * 20
        
    datos_tabla['Año 0'][13] = inv_inicial
    datos_tabla['Año 0'][17] = -inv_inicial
    
    recupero_desc = inv_inicial

    fondo_maniobra_prev = 0
    mercado_prev = 120000 / (1 + (p_crec/100))
    depr_base_anual = inv_inicial / 10
    depr_capex_acum = 0
    
    monto_prestamo = inv_inicial * pct_pasivo
    cuota = (monto_prestamo * kd) / (1 - (1 + kd)**-plazo_credito) if kd > 0 else monto_prestamo/plazo_credito
    saldo = monto_prestamo

    for t in range(1, 8):
        mercado = 120000 if t == 1 else mercado_prev * (1 + (p_crec/100))
        vol_share = mercado * (p_share/100)
        ingresos = vol_share * p_precio
        
        c_mp = ingresos * (p_mp/100)
        c_mod = ingresos * (p_mod/100)
        g_grales = gg_base * ((1 + gg_crec) ** (t-1))
        g_ventas = ingresos * pct_ventas
        g_transp = ingresos * pct_transp
        
        depr_actual = depr_base_anual + depr_capex_acum
        
        ebitda = ingresos - c_mp - c_mod - g_grales - g_ventas - g_transp
        ebit = ebitda - depr_actual
        impuestos = ebit * tasa_imp if ebit > 0 else 0
        nopat = (ebit - impuestos) + depr_actual
        
        cxc = ingresos * (ppc / dias_base)
        inv = c_mp * (ppi / dias_base)
        efectivo = ingresos * pct_efectivo
        cxp = c_mp * (ppp / dias_base)
        fondo_maniobra = cxc + inv + efectivo - cxp
        
        inversion_wk = fondo_maniobra if t == 1 else (fondo_maniobra - fondo_maniobra_prev)
        
        capex_t = cap_adic if t <= anios_cap else 0
        rescate_t = valor_rescate if t == 7 else 0
        recup_wk_t = fondo_maniobra * recup_wk if t == 7 else 0
        
        fcf = nopat - capex_t - inversion_wk + rescate_t + recup_wk_t
        vp = fcf / ((1 + wacc) ** t)
        
        # Llenar la matriz visual con los datos del periodo
        datos_tabla[f'Año {t}'][0] = ingresos
        datos_tabla[f'Año {t}'][1] = c_mp
        datos_tabla[f'Año {t}'][2] = c_mod
        datos_tabla[f'Año {t}'][3] = ingresos - c_mp - c_mod
        datos_tabla[f'Año {t}'][4] = g_grales
        datos_tabla[f'Año {t}'][5] = g_ventas
        datos_tabla[f'Año {t}'][6] = g_transp
        datos_tabla[f'Año {t}'][7] = ebitda
        datos_tabla[f'Año {t}'][8] = depr_actual
        datos_tabla[f'Año {t}'][9] = ebit
        datos_tabla[f'Año {t}'][10] = impuestos
        datos_tabla[f'Año {t}'][11] = depr_actual
        datos_tabla[f'Año {t}'][12] = nopat
        datos_tabla[f'Año {t}'][13] = capex_t if capex_t > 0 else None
        datos_tabla[f'Año {t}'][14] = inversion_wk if inversion_wk != 0 else None
        datos_tabla[f'Año {t}'][15] = rescate_t if rescate_t > 0 else None
        datos_tabla[f'Año {t}'][16] = recup_wk_t if recup_wk_t > 0 else None
        datos_tabla[f'Año {t}'][17] = fcf
        
        recupero_desc = recupero_desc - vp
        
        datos_tabla[f'Año {t}'][18] = vp
        datos_tabla[f'Año {t}'][19] = recupero_desc
        
        # Mantener los registros para los demás gráficos
        flujo_caja.append(fcf)
        acum = acumulado[t-1] + vp
        acumulado.append(acum)
        
        resultados.append({
            'Año': f'Año {t}', 'Ingresos': ingresos, 'Costo MP': c_mp, 'Costo MOD': c_mod,
            'Gastos Operativos': g_grales + g_ventas + g_transp,
            'Flujo de Caja Libre (FCF)': fcf
        })
        
        detalle_efe.append({
            'Año': f'Año {t}', 'Cuentas por cobrar': cxc, 'Inventarios': inv, 'Efectivo': efectivo,
            'Cuentas por pagar': cxp, 'Fondo de maniobra': fondo_maniobra, 'Inversiones (Var. WK)': inversion_wk
        })
        
        interes = saldo * kd
        amortizacion_prin = cuota - interes if t <= plazo_credito else 0
        saldo_final = saldo - amortizacion_prin if t <= plazo_credito else 0
        amortizacion.append({
            'Año': f'Año {t}', 'Saldo Inicial': saldo, 'Cuota': cuota if t <= plazo_credito else 0,
            'Intereses': interes if t <= plazo_credito else 0, 'Amortización': amortizacion_prin, 'Saldo Final': saldo_final
        })
        
        mercado_prev = mercado
        fondo_maniobra_prev = fondo_maniobra
        saldo = saldo_final
        if t <= anios_cap: depr_capex_acum += (cap_adic / 10)

    tir = calc_tir(flujo_caja)
    fcf_acum = sum(flujo_caja[1:])
    ingresos_totales = sum(r['Ingresos'] for r in resultados)
    
    return {
        'van': acumulado[7], 'tir': tir, 'wacc': wacc, 'fcf_acum': fcf_acum, 'ingresos_tot': ingresos_totales,
        'flujos': flujo_caja, 'res_df': pd.DataFrame(resultados), 'efe_df': pd.DataFrame(detalle_efe), 
        'amort_df': pd.DataFrame(amortizacion), 'df_exacto': pd.DataFrame(datos_tabla)
    }

res_actual = calcular_modelo(crec, precio, share, mp, mod)
b_dict = escenarios_dict['Base']
res_base = calcular_modelo(b_dict['crec'], b_dict['precio'], b_dict['share'], b_dict['mp'], b_dict['mod'])

# 5. Cabecera y KPIs
st.markdown("""
    <div class="main-header">
        <div>
            <h1 class="main-title">📊 Flujo de Caja Libre (FCF)</h1>
            <p class="main-subtitle">Evalúa el impacto de inversiones y escenarios en la rentabilidad de tu proyecto</p>
        </div>
    </div>
""", unsafe_allow_html=True)

def calc_delta(act, base):
    if base == 0: return ""
    pct = ((act / base) - 1) * 100
    color = "#10b981" if pct >= 0 else "#ef4444"
    sign = "▲ +" if pct >= 0 else "▼ "
    return f'<div class="kpi-delta" style="color: {color};">{sign}{pct:.1f}% frente al escenario base</div>'

st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-title">↗️ VAN del Proyecto</div>
            <div class="kpi-val">$ {res_actual['van']:,.0f}</div>
            <div class="kpi-sub">Valor Actual Neto</div>
            {calc_delta(res_actual['van'], res_base['van'])}
        </div>
        <div class="kpi-card">
            <div class="kpi-title">📈 TIR del Proyecto</div>
            <div class="kpi-val">{res_actual['tir']*100:,.1f}%</div>
            <div class="kpi-sub">Tasa Interna de Retorno</div>
            {calc_delta(res_actual['tir'], res_base['tir'])}
        </div>
        <div class="kpi-card">
            <div class="kpi-title">🥞 FCF Acumulado (7 años)</div>
            <div class="kpi-val">$ {res_actual['fcf_acum']:,.0f}</div>
            <div class="kpi-sub">Sin descontar WACC</div>
            {calc_delta(res_actual['fcf_acum'], res_base['fcf_acum'])}
        </div>
        <div class="kpi-card">
            <div class="kpi-title">💰 Ingresos Totales</div>
            <div class="kpi-val">$ {res_actual['ingresos_tot']:,.0f}</div>
            <div class="kpi-sub">Ventas proyectadas (7 años)</div>
            {calc_delta(res_actual['ingresos_tot'], res_base['ingresos_tot'])}
        </div>
        <div class="kpi-card">
            <div class="kpi-title">🏦 Inversión Total (Capex)</div>
            <div class="kpi-val">$ {(inv_inicial + (cap_adic * anios_cap)):,.0f}</div>
            <div class="kpi-sub">Año 0 + Años adicionales</div>
            <div class="kpi-delta" style="color: #64748b;">(Métrica absoluta)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">% WACC Aplicado</div>
            <div class="kpi-val">{res_actual['wacc']*100:.1f}%</div>
            <div class="kpi-sub">Tasa de descuento</div>
            <div class="kpi-delta" style="color: #64748b;">— Dinámico</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 6. Gráficos Plotly
col1, col2 = st.columns([1, 1.5])
df_res = res_actual['res_df']

layout_dark = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'),
    margin=dict(t=30, b=20, l=20, r=20), xaxis=dict(showgrid=True, gridcolor='#1e293b'), yaxis=dict(showgrid=True, gridcolor='#1e293b')
)

with col1:
    st.markdown('**Distribución de Egresos del Año 1**')
    fig_pie = go.Figure(data=[go.Pie(
        labels=['Materia Prima', 'Mano de Obra', 'Gastos Generales'],
        values=[df_res.loc[0, 'Costo MP'], df_res.loc[0, 'Costo MOD'], df_res.loc[0, 'Gastos Operativos']],
        hole=0.6, marker_colors=['#00d2ff', '#9d4edd', '#3b82f6'], textinfo='percent'
    )])
    fig_pie.update_layout(**layout_dark, showlegend=True, legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown('**Evolución del FCF Simulado**')
    fig_bar = go.Figure(data=[go.Bar(
        x=[f"Año {i}" for i in range(1, 8)], y=df_res['Flujo de Caja Libre (FCF)'], 
        marker_color='#00d2ff', text=[f"${val:,.0f}" for val in df_res['Flujo de Caja Libre (FCF)']], 
        textposition='outside'
    )])
    fig_bar.update_layout(**layout_dark)
    st.plotly_chart(fig_bar, use_container_width=True)

# 7. Tablas de Excel
st.markdown('---')
st.markdown('### 📋 Detalle Financiero del Modelo')

tab1, tab2, tab3 = st.tabs([" Flujo de Caja Libre (FCF)", " Capital de Trabajo (EFE)", " Amortización de Deuda"])
with tab1:
    # Aplicar estilos para remarcar filas importantes tal cual el excel
    def style_rows(row):
        if row.name in ['Margen bruto', 'EBITDA', 'EBIT', 'NOPAT', 'FCF']:
            return ['background-color: #0b111a; color: #00d2ff; font-weight: bold'] * len(row)
        return [''] * len(row)
        
    df_show = res_actual['df_exacto'].set_index('Concepto')
    st.dataframe(
        df_show.style.apply(style_rows, axis=1).format("{:,.0f}", na_rep=""), 
        use_container_width=True, height=750
    )

with tab2:
    st.dataframe(res_actual['efe_df'].set_index('Año').T.style.format("{:,.0f}"), use_container_width=True)
with tab3:
    st.dataframe(res_actual['amort_df'].set_index('Año').style.format("{:,.0f}"), use_container_width=True)