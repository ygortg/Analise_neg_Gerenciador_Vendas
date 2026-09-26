"""Regras de negócio e persistência do sistema de vendas.

Este arquivo não cria elementos visuais. Ele concentra as funções que leem os
arquivos CSV, validam os dados e calculam os relatórios usados no dashboard.
"""

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


# A pasta é calculada a partir da localização deste arquivo. Assim, o programa
# funciona mesmo quando for iniciado por outro diretório.
DIRETORIO_DADOS = Path(__file__).resolve().parent / "dados"

CAMPOS_PRODUTOS = ("id", "nome", "categoria", "preco")
CAMPOS_VENDAS = (
    "id_venda",
    "data_hora",
    "produto_id",
    "produto",
    "categoria",
    "preco_unitario",
    "quantidade",
    "subtotal",
)


def _caminho_produtos():
    return DIRETORIO_DADOS / "produtos.csv"


def _caminho_vendas():
    return DIRETORIO_DADOS / "vendas.csv"


def _garantir_arquivo(caminho, campos):
    """Cria a pasta e um CSV com cabeçalho quando ainda não existirem."""
    DIRETORIO_DADOS.mkdir(parents=True, exist_ok=True)

    if not caminho.exists() or caminho.stat().st_size == 0:
        with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=campos)
            escritor.writeheader()


def _proximo_id(registros, campo="id"):
    """Encontra o maior ID existente e soma um."""
    maior_id = 0

    for registro in registros:
        if registro[campo] > maior_id:
            maior_id = registro[campo]

    return maior_id + 1


def _decimal_positivo(valor, nome_campo):
    """Converte um valor para Decimal e exige que seja maior que zero."""
    try:
        numero = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as erro:
        raise ValueError(f"{nome_campo} deve ser um número válido.") from erro

    if numero <= 0:
        raise ValueError(f"{nome_campo} deve ser maior que zero.")

    return numero


def _normalizar_data_hora(data_venda):
    """Aceita data/hora do Python e devolve AAAA-MM-DD HH:MM:SS."""
    if isinstance(data_venda, datetime):
        return data_venda.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(data_venda, date):
        return datetime.combine(data_venda, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")

    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(data_venda), formato).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue

    raise ValueError("Informe uma data e hora válidas.")


def carregar_produtos():
    """Lê produtos.csv e devolve uma lista de dicionários tipados."""
    caminho = _caminho_produtos()
    _garantir_arquivo(caminho, CAMPOS_PRODUTOS)
    produtos = []

    with caminho.open("r", newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)

        for linha in leitor:
            produtos.append(
                {
                    "id": int(linha["id"]),
                    "nome": linha["nome"],
                    "categoria": linha["categoria"],
                    "preco": float(linha["preco"]),
                }
            )

    return produtos


def cadastrar_produto(nome, categoria, preco):
    """Valida e salva um novo produto; devolve o produto cadastrado."""
    nome_limpo = str(nome).strip()
    categoria_limpa = str(categoria).strip()

    if not nome_limpo:
        raise ValueError("Informe o nome do produto.")

    if not categoria_limpa:
        raise ValueError("Informe a categoria do produto.")

    preco_decimal = _decimal_positivo(preco, "O preço")
    produtos = carregar_produtos()

    # casefold permite comparar textos sem diferenciar maiúsculas e minúsculas.
    for produto in produtos:
        if produto["nome"].casefold() == nome_limpo.casefold():
            raise ValueError("Já existe um produto com esse nome.")

    novo_produto = {
        "id": _proximo_id(produtos),
        "nome": nome_limpo,
        "categoria": categoria_limpa,
        "preco": float(preco_decimal),
    }

    with _caminho_produtos().open("a", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_PRODUTOS)
        linha = novo_produto.copy()
        linha["preco"] = f"{preco_decimal:.2f}"
        escritor.writerow(linha)

    return novo_produto


def carregar_vendas():
    """Lê vendas.csv; cada linha representa um item de uma venda."""
    caminho = _caminho_vendas()
    _garantir_arquivo(caminho, CAMPOS_VENDAS)
    vendas = []

    with caminho.open("r", newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)

        for linha in leitor:
            vendas.append(
                {
                    "id_venda": int(linha["id_venda"]),
                    "data_hora": linha["data_hora"],
                    "produto_id": int(linha["produto_id"]),
                    "produto": linha["produto"],
                    "categoria": linha["categoria"],
                    "preco_unitario": float(linha["preco_unitario"]),
                    "quantidade": int(linha["quantidade"]),
                    "subtotal": float(linha["subtotal"]),
                }
            )

    return vendas


def registrar_venda(itens, data_venda=None):
    """Registra vários produtos com o mesmo ID e devolve o total da compra."""
    if not itens:
        raise ValueError("Selecione pelo menos um produto.")

    produtos = {produto["id"]: produto for produto in carregar_produtos()}
    itens_preparados = []
    total_venda = Decimal("0.00")

    for item in itens:
        try:
            produto_id = int(item["produto_id"])
            quantidade_decimal = Decimal(str(item["quantidade"]))
        except (KeyError, InvalidOperation, ValueError, TypeError) as erro:
            raise ValueError("Produto ou quantidade inválidos.") from erro

        if quantidade_decimal != quantidade_decimal.to_integral_value():
            raise ValueError("A quantidade deve ser um número inteiro.")

        quantidade = int(quantidade_decimal)
        produto = produtos.get(produto_id)

        if produto is None:
            raise ValueError("Produto não encontrado.")
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        preco = Decimal(str(produto["preco"]))
        subtotal = (preco * quantidade).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_venda += subtotal
        itens_preparados.append(
            {
                "produto_id": produto_id,
                "produto": produto["nome"],
                "categoria": produto["categoria"],
                "preco_unitario": preco,
                "quantidade": quantidade,
                "subtotal": subtotal,
            }
        )

    vendas = carregar_vendas()
    id_venda = _proximo_id(vendas, "id_venda")
    data_hora = _normalizar_data_hora(data_venda or datetime.now())

    with _caminho_vendas().open("a", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_VENDAS)

        for item in itens_preparados:
            escritor.writerow(
                {
                    "id_venda": id_venda,
                    "data_hora": data_hora,
                    "produto_id": item["produto_id"],
                    "produto": item["produto"],
                    "categoria": item["categoria"],
                    "preco_unitario": f"{item['preco_unitario']:.2f}",
                    "quantidade": item["quantidade"],
                    "subtotal": f"{item['subtotal']:.2f}",
                }
            )

    return {
        "id_venda": id_venda,
        "data_hora": data_hora,
        "itens": itens_preparados,
        "total": float(total_venda.quantize(Decimal("0.01"))),
    }


def filtrar_vendas_por_mes(vendas, mes=None):
    """Filtra por AAAA-MM; sem mês, devolve todas as vendas."""
    if not mes:
        return list(vendas)

    filtradas = []
    for venda in vendas:
        if venda["data_hora"][:7] == mes:
            filtradas.append(venda)

    return filtradas


def calcular_faturamento(vendas):
    """Soma o valor total de todas as vendas recebidas."""
    faturamento = Decimal("0.00")

    for venda in vendas:
        faturamento += Decimal(str(venda["subtotal"]))

    return float(faturamento.quantize(Decimal("0.01")))


def calcular_faturamento_mensal(vendas):
    """Agrupa o faturamento por mês e devolve um dicionário ordenado."""
    totais = {}

    for venda in vendas:
        mes = venda["data_hora"][:7]
        valor = Decimal(str(venda["subtotal"]))

        if mes in totais:
            totais[mes] += valor
        else:
            totais[mes] = valor

    totais_ordenados = {}
    for mes in sorted(totais):
        totais_ordenados[mes] = float(totais[mes].quantize(Decimal("0.01")))

    return totais_ordenados


def gerar_ranking_produtos(vendas):
    """Soma unidades por produto e ordena do maior para o menor."""
    quantidades = {}

    for venda in vendas:
        produto = venda["produto"]

        if produto in quantidades:
            quantidades[produto] += venda["quantidade"]
        else:
            quantidades[produto] = venda["quantidade"]

    ranking = []
    for produto, quantidade in quantidades.items():
        ranking.append({"produto": produto, "quantidade": quantidade})

    ranking.sort(key=lambda item: (-item["quantidade"], item["produto"].casefold()))
    return ranking


def gerar_ranking_financeiro(vendas):
    """Soma o faturamento de cada produto e ordena do maior para o menor."""
    totais = {}

    for venda in vendas:
        produto = venda["produto"]
        totais[produto] = totais.get(produto, 0) + venda["subtotal"]

    ranking = []
    for produto, faturamento in totais.items():
        ranking.append({"produto": produto, "faturamento": round(faturamento, 2)})

    ranking.sort(key=lambda item: (-item["faturamento"], item["produto"].casefold()))
    return ranking


def calcular_total_vendas(vendas):
    """Conta transações únicas, mesmo quando possuem vários produtos."""
    identificadores = set()

    for venda in vendas:
        identificadores.add(venda["id_venda"])

    return len(identificadores)


def calcular_unidades_vendidas(vendas):
    """Soma as quantidades de todos os registros de venda."""
    total = 0

    for venda in vendas:
        total += venda["quantidade"]

    return total
