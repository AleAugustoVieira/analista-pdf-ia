import streamlit as st
import os
import json
import csv
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader # <--- NOVO: Biblioteca de PDF

# Configurações iniciais
st.set_page_config(page_title="Analista de Documentos IA", page_icon="📑")
load_dotenv()

# Verificação de segurança
if not os.getenv("OPENAI_API_KEY"):
    st.error("❌ Chave API não encontrada no arquivo .env")
    st.stop()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
arquivo_excel = "pedidos_pdf.csv"

st.title("📑 Analista de Documentos IA")
st.markdown("Faça upload de um PDF (pedido, nota fiscal, orçamento) e extraia os dados.")

# --- MUDANÇA 1: CAMPO DE UPLOAD ---
# Aceita apenas arquivos PDF
arquivo_upload = st.file_uploader("Arraste seu PDF aqui", type=["pdf"])

texto_para_ia = ""

# Se o usuário enviou um arquivo
if arquivo_upload is not None:
    try:
        # --- MUDANÇA 2: LER O PDF ---
        leitor = PdfReader(arquivo_upload)
        n_paginas = len(leitor.pages)
        st.info(f"Arquivo carregado com sucesso! Contém {n_paginas} página(s).")
        
        # Extrai texto de todas as páginas
        for pagina in leitor.pages:
            texto_para_ia += pagina.extract_text()
            
        # Mostra uma prévia do texto extraído (opcional, bom para debug)
        with st.expander("Ver texto cru extraído do PDF"):
            st.text(texto_para_ia[:1000] + "...") # Mostra só os primeiros 1000 caracteres

    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")

# Botão de processar (só aparece se tiver texto)
if texto_para_ia and st.button("Extrair Dados do Documento 🚀"):
    with st.spinner('A IA está analisando o documento...'):
        try:
            resposta = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um especialista em extração de dados de documentos. "
                            "Analise o texto extraído de um PDF e retorne APENAS JSON. "
                            "Tente encontrar: cliente, data, valor_total e itens. "
                            "Formato: {'cliente': '...', 'data': 'DD/MM/AAAA', 'valor_total': '0.00', 'itens': [{'produto': '...', 'qtd': 0}]}"
                        )
                    },
                    {"role": "user", "content": texto_para_ia}
                ],
                temperature=0
            )
            
            # Processamento
            dados = json.loads(resposta.choices[0].message.content)
            
            # Exibição Visual
            st.success("Dados Extraídos!")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Cliente", dados.get('cliente', 'N/A'))
            col2.metric("Data", dados.get('data', 'N/A'))
            col3.metric("Valor Total", dados.get('valor_total', 'N/A'))
            
            st.subheader("📦 Itens Identificados")
            st.table(dados.get('itens', []))
            
            # Salvar no Excel
            novo_arquivo = not os.path.exists(arquivo_excel)
            with open(arquivo_excel, mode='a', newline='', encoding='utf-8') as f:
                escritor = csv.writer(f)
                if novo_arquivo:
                    escritor.writerow(['Cliente', 'Data', 'Valor Total', 'Produto', 'Qtd'])
                
                if 'itens' in dados:
                    for item in dados['itens']:
                        escritor.writerow([
                            dados.get('cliente', '-'),
                            dados.get('data', '-'),
                            dados.get('valor_total', '-'),
                            item.get('produto', '-'),
                            item.get('qtd', '-')
                        ])
            
            st.toast("Documento salvo na base de dados!", icon="✅")

        except Exception as e:
            st.error(f"Erro na IA: {e}")