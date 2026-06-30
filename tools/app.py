import streamlit as st
import sqlite3

# Configuração da página
st.set_page_config(
    page_title="FarmacoMatch",
    page_icon="💊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def busca_lista_medicamentos():
    conn = sqlite3.connect('med.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM medicamentos ORDER BY nome")
    lista = cursor.fetchall()
    conn.close()
    return [row[0] for row in lista]

def busca_classificacao_remedio(nome_remedio: str) -> str:
    conn = sqlite3.connect('med.db')
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT classificacao 
        FROM medicamentos 
        WHERE nome = '{nome_remedio}'
        LIMIT 1
    """)
    try:
        data = cursor.fetchall()
        if data:
            classificao_remedio = data[0][0]
        else:
            classificao_remedio = None
    except Exception:
        classificao_remedio = None
    conn.close()
    return classificao_remedio

def busca_contra_indicacao(classificacao_1, classificacao_2) -> str | None:
    conn = sqlite3.connect('med.db')
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT risco 
        FROM interacao_classes 
        WHERE class_1 = '{classificacao_1}' AND class_2 = '{classificacao_2}' 
        OR 
        class_1 = '{classificacao_2}' AND class_2 = '{classificacao_1}'
    """)
    
    result = cursor.fetchall()
    if result:
        return result[0][0]
    else:
        return None

# Custom CSS for modern look
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Header Styling */
    .main-header {
        text-align: center;
        padding: 3rem 0 2rem 0;
    }
    
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        color: #2C3E50;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }

    .subtitle {
        font-size: 1.1rem;
        color: #7F8C8D;
        font-weight: 400;
    }

    /* Form Container Styling */
    .stSelectbox label {
        font-size: 1rem;
        font-weight: 600;
        color: #34495E;
    }
    
    .stSelectbox > div > div {
        border-radius: 12px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    /* Button Styling */
    div.stButton > button {
        width: 100%;
        background-color: #3498DB;
        color: white;
        font-weight: 600;
        padding: 0.6rem 1rem;
        border-radius: 12px;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 10px rgba(52, 152, 219, 0.2);
        margin-top: 1rem;
    }
    
    div.stButton > button:hover {
        background-color: #2980B9;
        box-shadow: 0 6px 15px rgba(52, 152, 219, 0.3);
        transform: translateY(-2px);
    }

    /* Result Cards */
    .result-card {
        margin-top: 2rem;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        animation: fadeInUp 0.5s ease-out;
    }
    
    .success-card {
        background-color: #D4EDDA;
        color: #155724;
        border: 1px solid #C3E6CB;
    }
    
    .error-card {
        background-color: #F8D7DA;
        color: #721C24;
        border: 1px solid #F5C6CB;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Disclaimer Banner Fixo */
    .disclaimer-banner {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #FFF3CD;
        color: #856404;
        border-top: 2px solid #FFEEBA;
        padding: 0.55rem 1rem;
        font-size: 0.78rem;
        text-align: center;
        z-index: 9999;
        font-weight: 600;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.1);
    }
    .disclaimer-banner strong { color: #B71C1C; }

    /* espaço para não sobrepor o banner */
    .block-container { padding-bottom: 3rem !important; }
    </style>
""", unsafe_allow_html=True)

# Banner de aviso fixo no rodapé da tela
st.markdown(
    '<div class="disclaimer-banner">'
    '⚠️ <strong>AVISO:</strong> Não nos responsabilizamos pelo uso desta ferramenta. '
    'As informações são retiradas de fontes da internet e podem conter erros. '
    'NÃO use para tratamentos ou uso de medicamentos — consulte sempre um médico.'
    '</div>',
    unsafe_allow_html=True
)

# UI Layout
st.markdown('<div class="main-header"><div class="main-title">FarmacoMatch 💊</div><div class="subtitle">Verificação de compatibilidade medicamentosa</div></div>', unsafe_allow_html=True)

medicamentos = busca_lista_medicamentos()
medicamentos.insert(0, "Selecione um medicamento")

# Main Form
with st.container():
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        remedio1 = st.selectbox(
            "Primeiro Medicamento",
            medicamentos,
            key="remedio1"
        )
    with col2:
        remedio2 = st.selectbox(
            "Segundo Medicamento",
            medicamentos,
            key="remedio2"
        )

    # Centered Check Button
    b_col1, b_col2, b_col3 = st.columns([1, 2, 1])
    with b_col2:
        check_btn = st.button("Verificar Compatibilidade")

# Logic & Results
if check_btn:
    if remedio1 == "Selecione um medicamento" or remedio2 == "Selecione um medicamento":
        st.warning("⚠️ Por favor, selecione os dois medicamentos para análise.")
    else:
        classificao_remedio_1 = busca_classificacao_remedio(remedio1)
        classificao_remedio_2 = busca_classificacao_remedio(remedio2)
        mensagem = busca_contra_indicacao(classificao_remedio_1, classificao_remedio_2)
        
        if mensagem is None:
            st.markdown("""
                <div class="result-card success-card">
                    <h3>✅ Pode misturar😁!!!</h3>
                    <p>Não foram encontradas contraindicações diretas na base de dados.</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="result-card error-card">
                    <h3>❌ Não pode misturar💀</h3>
                    <p>Existe uma contraindicação registrada para esta combinação.</p>
                </div>
            """, unsafe_allow_html=True)