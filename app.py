"""Interface web do Sistema de Gestão de Vendas."""

from datetime import date, datetime

import pandas as pd
import streamlit as st

from logica import (
    calcular_faturamento,
    calcular_faturamento_mensal,
    calcular_total_vendas,
    calcular_unidades_vendidas,
    cadastrar_produto,
    carregar_produtos,
    carregar_vendas,
    filtrar_vendas_por_mes,
    gerar_ranking_financeiro,
    gerar_ranking_produtos,
    registrar_venda,
)


st.set_page_config(
    page_title="Gestão de Vendas Online",
    page_icon="🛒",
    layout="wide",
)

NOMES_MESES = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def formatar_moeda(valor):
    """Transforma 1234.5 em R$ 1.234,50."""
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    return f"R$ {texto}"


def formatar_mes(mes):
    """Transforma AAAA-MM em Nome do mês/AAAA."""
    ano, numero_mes = mes.split("-")
    return f"{NOMES_MESES[int(numero_mes) - 1]}/{ano}"


def opcoes_meses(vendas):
    """Obtém os meses existentes sem repetições, do mais novo ao mais antigo."""
    meses = set()

    for venda in vendas:
        meses.add(venda["data_hora"][:7])

    return sorted(meses, reverse=True)


def pagina_produtos():
    st.header("Cadastro de produtos")
    st.write("Cadastre os produtos que poderão ser selecionados nas vendas.")

    with st.form("formulario_produto", clear_on_submit=True):
        nome = st.text_input("Nome do produto", placeholder="Ex.: Smartphone Galaxy")
        categoria = st.text_input("Categoria", placeholder="Ex.: Smartphones")
        preco = st.number_input(
            "Preço padrão (R$)",
            min_value=0.01,
            value=1.00,
            step=0.01,
            format="%.2f",
        )
        enviar = st.form_submit_button("Cadastrar produto", type="primary")

    if enviar:
        try:
            produto = cadastrar_produto(nome, categoria, preco)
            st.success(f"Produto “{produto['nome']}” cadastrado com sucesso.")
        except ValueError as erro:
            st.error(str(erro))

    produtos = carregar_produtos()
    st.subheader("Produtos cadastrados")

    if not produtos:
        st.info("Nenhum produto foi cadastrado ainda.")
        return

    tabela = pd.DataFrame(produtos).rename(
        columns={"id": "ID", "nome": "Produto", "categoria": "Categoria", "preco": "Preço"}
    )
    st.dataframe(
        tabela,
        hide_index=True,
        use_container_width=True,
        column_config={"Preço": st.column_config.NumberColumn(format="R$ %.2f")},
    )


def pagina_vendas():
    st.header("Registrar venda")
    produtos = carregar_produtos()

    if not produtos:
        st.warning("Cadastre pelo menos um produto antes de registrar uma venda.")
        return

    produtos_por_id = {produto["id"]: produto for produto in produtos}
    selecionados = st.multiselect(
        "Produtos da compra",
        options=list(produtos_por_id),
        format_func=lambda identificador: produtos_por_id[identificador]["nome"],
        placeholder="Selecione um ou mais produtos",
    )

    itens = []
    total_previsto = 0

    for produto_id in selecionados:
        produto = produtos_por_id[produto_id]
        coluna_produto, coluna_quantidade = st.columns([3, 1])
        coluna_produto.write(
            f"**{produto['nome']}**  \n"
            f"{produto['categoria']} · {formatar_moeda(produto['preco'])}"
        )
        quantidade = coluna_quantidade.number_input(
            "Quantidade",
            min_value=1,
            value=1,
            step=1,
            key=f"quantidade_{produto_id}",
        )
        subtotal = produto["preco"] * quantidade
        total_previsto += subtotal
        itens.append({"produto_id": produto_id, "quantidade": quantidade})
        st.caption(f"Subtotal: {formatar_moeda(subtotal)}")

    coluna_data, coluna_hora = st.columns(2)
    data_venda = coluna_data.date_input("Data da venda", value=date.today(), format="DD/MM/YYYY")
    hora_venda = coluna_hora.time_input(
        "Hora da venda",
        value=datetime.now().time().replace(second=0, microsecond=0),
        step=60,
    )
    st.metric("Valor final da compra", formatar_moeda(total_previsto))
    enviar = st.button("Registrar venda", type="primary", disabled=not itens)

    if enviar:
        try:
            venda = registrar_venda(itens, datetime.combine(data_venda, hora_venda))
            st.success(
                f"Venda nº {venda['id_venda']} registrada com "
                f"{len(venda['itens'])} produto(s). "
                f"Total: {formatar_moeda(venda['total'])}."
            )
        except ValueError as erro:
            st.error(str(erro))


def seletor_mes(vendas, chave):
    """Cria um filtro de mês e devolve None para a opção Todos."""
    meses = opcoes_meses(vendas)
    opcoes = [None] + meses
    return st.selectbox(
        "Filtrar por mês",
        options=opcoes,
        format_func=lambda mes: "Todos os meses" if mes is None else formatar_mes(mes),
        key=chave,
    )


def pagina_dashboard():
    st.header("Dashboard de vendas")
    vendas = carregar_vendas()

    if not vendas:
        st.info("Registre vendas para visualizar os indicadores e gráficos.")
        return

    mes = seletor_mes(vendas, "mes_dashboard")
    vendas_filtradas = filtrar_vendas_por_mes(vendas, mes)

    faturamento = calcular_faturamento(vendas_filtradas)
    total_vendas = calcular_total_vendas(vendas_filtradas)
    unidades = calcular_unidades_vendidas(vendas_filtradas)
    ranking = gerar_ranking_produtos(vendas_filtradas)
    ranking_financeiro = gerar_ranking_financeiro(vendas_filtradas)
    mais_vendido = ranking[0]["produto"] if ranking else "—"

    coluna1, coluna2, coluna3, coluna4 = st.columns(4)
    coluna1.metric("Faturamento", formatar_moeda(faturamento))
    coluna2.metric("Vendas realizadas", total_vendas)
    coluna3.metric("Unidades vendidas", unidades)
    coluna4.metric("Produto mais vendido", mais_vendido)

    st.subheader("Faturamento mensal")
    faturamento_mensal = calcular_faturamento_mensal(vendas_filtradas)
    dados_mensais = []

    for chave_mes, valor in faturamento_mensal.items():
        dados_mensais.append({"Mês": formatar_mes(chave_mes), "Faturamento": valor})

    tabela_mensal = pd.DataFrame(dados_mensais).set_index("Mês")
    st.line_chart(tabela_mensal, y="Faturamento")

    grafico1, grafico2 = st.columns(2)

    with grafico1:
        st.subheader("Ranking por unidades")
        tabela_ranking = pd.DataFrame(ranking).rename(
            columns={"produto": "Produto", "quantidade": "Unidades"}
        )
        st.bar_chart(tabela_ranking.set_index("Produto"), y="Unidades")

    with grafico2:
        st.subheader("Ranking por faturamento")
        tabela_financeira = pd.DataFrame(ranking_financeiro).rename(
            columns={"produto": "Produto", "faturamento": "Faturamento"}
        )
        st.bar_chart(tabela_financeira.set_index("Produto"), y="Faturamento")

    st.caption("Os indicadores são recalculados a partir dos registros salvos em vendas.csv.")


def pagina_historico():
    st.header("Histórico de vendas")
    vendas = carregar_vendas()

    if not vendas:
        st.info("Nenhuma venda foi registrada ainda.")
        return

    mes = seletor_mes(vendas, "mes_historico")
    vendas_filtradas = filtrar_vendas_por_mes(vendas, mes)
    tabela = pd.DataFrame(vendas_filtradas).rename(
        columns={
            "id_venda": "Venda",
            "data_hora": "Data e hora",
            "produto_id": "ID do produto",
            "produto": "Produto",
            "categoria": "Categoria",
            "preco_unitario": "Preço unitário",
            "quantidade": "Quantidade",
            "subtotal": "Subtotal",
        }
    )
    tabela["Data e hora"] = pd.to_datetime(tabela["Data e hora"]).dt.strftime("%d/%m/%Y %H:%M")

    st.dataframe(
        tabela,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Preço unitário": st.column_config.NumberColumn(format="R$ %.2f"),
            "Subtotal": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )


st.title("📱 Loja de Celulares e Periféricos")
st.caption("Cadastro, processamento e análise de vendas em Python")

pagina = st.sidebar.radio(
    "Navegação",
    ("Dashboard", "Cadastrar produtos", "Registrar venda", "Histórico"),
)

if pagina == "Cadastrar produtos":
    pagina_produtos()
elif pagina == "Registrar venda":
    pagina_vendas()
elif pagina == "Histórico":
    pagina_historico()
else:
    pagina_dashboard()
