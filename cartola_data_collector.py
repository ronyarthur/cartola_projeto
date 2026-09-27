import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne


# ============================================================
# CONFIGURAÇÕES
# ============================================================

load_dotenv()

API_URL = "https://api.cartola.globo.com/atletas/mercado"
DATABASE_NAME = "cartola_fc_db"


# ============================================================
# CONEXÃO COM O MONGODB
# ============================================================

def conectar_mongodb():
    """
    Conecta ao MongoDB utilizando a variável MONGO_URI
    definida no arquivo .env.
    """

    print("Conectando ao MongoDB...")

    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        raise ValueError(
            "A variável MONGO_URI não foi encontrada no arquivo .env."
        )

    try:
        client = MongoClient(mongo_uri)

        # Testa a conexão
        client.admin.command("ping")

        db = client[DATABASE_NAME]

        print("MongoDB conectado com sucesso!")

        return db

    except Exception as erro:
        print(f"Erro ao conectar ao MongoDB: {erro}")
        raise


# ============================================================
# EXTRAÇÃO DOS DADOS
# ============================================================

def buscar_dados_mercado():
    """
    Busca os dados do mercado do Cartola FC através da API.
    Retorna o conteúdo JSON recebido.
    """

    print("\nBuscando dados na API do Cartola FC...")

    try:
        resposta = requests.get(
            API_URL,
            timeout=30
        )

        # Gera uma exceção caso a API retorne erro HTTP
        resposta.raise_for_status()

        dados = resposta.json()

        print("Dados recebidos com sucesso!")

        return dados

    except requests.exceptions.RequestException as erro:
        print(f"Erro ao acessar a API do Cartola FC: {erro}")
        raise

    except ValueError as erro:
        print(f"Erro ao interpretar o JSON recebido: {erro}")
        raise


# ============================================================
# TRANSFORMAÇÃO E CARGA
# ============================================================

def processar_e_gravar_dados(db, dados_mercado):
    """
    Processa os dados recebidos da API e grava as informações
    nas collections do MongoDB.
    """

    # Timestamp no padrão UTC/ISO 8601
    timestamp_coleta = datetime.now(timezone.utc).isoformat()

    # ========================================================
    # CLUBES
    # ========================================================

    print("\nGravando dados dos clubes...")

    clubes = dados_mercado.get("clubes", {})

    operacoes_clubes = []

    for clube_id, clube in clubes.items():

        documento_clube = {
            "_id": int(clube_id),
            "nome": clube.get("nome"),
            "abreviacao": clube.get("abreviacao"),
            "escudos": clube.get("escudos", {}),
            "nome_fantasia": clube.get("nome_fantasia")
        }

        operacoes_clubes.append(
            UpdateOne(
                {"_id": int(clube_id)},
                {"$set": documento_clube},
                upsert=True
            )
        )

    if operacoes_clubes:

        resultado = db.clubes_rodada_atual.bulk_write(
            operacoes_clubes
        )

        print(
            f"{len(operacoes_clubes)} clube(s) processado(s)."
        )

    else:
        print("Nenhum clube encontrado.")


    # ========================================================
    # ATLETAS
    # ========================================================

    print("\nGravando dados dos atletas...")

    atletas = dados_mercado.get("atletas", [])

    atletas_processados = []

    for atleta in atletas:

        # Cria uma cópia para não modificar o JSON original
        documento_atleta = atleta.copy()

        # Adiciona o horário da coleta
        documento_atleta["timestamp_coleta"] = timestamp_coleta

        atletas_processados.append(documento_atleta)

    # Limpa a collection para manter apenas a rodada atual
    db.atletas_rodada_atual.delete_many({})

    if atletas_processados:

        db.atletas_rodada_atual.insert_many(
            atletas_processados
        )

        print(
            f"{len(atletas_processados)} atleta(s) gravado(s)."
        )

    else:
        print("Nenhum atleta encontrado.")


    # ========================================================
    # STATUS DO MERCADO
    # ========================================================

    print("\nGravando status do mercado...")

    status = dados_mercado.get("status")

    # Alguns retornos da API podem disponibilizar informações
    # relacionadas ao mercado também no nível principal.
    documento_mercado = {
        "status_mercado": status,
        "rodada_atual": dados_mercado.get("rodada_atual"),
        "aviso": dados_mercado.get("aviso"),
        "fechamento": dados_mercado.get("fechamento"),
        "timestamp_coleta": timestamp_coleta
    }

    # Mantém apenas o status mais recente
    db.mercado_rodada_atual.delete_many({})

    db.mercado_rodada_atual.insert_one(
        documento_mercado
    )

    print("Status do mercado gravado com sucesso!")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():

    print("=" * 55)
    print("COLETOR CARTOLA FC -> MONGODB")
    print("=" * 55)

    # Conecta ao banco
    db = conectar_mongodb()

    # Busca os dados da API
    dados_mercado = buscar_dados_mercado()

    # Processa e grava no MongoDB
    processar_e_gravar_dados(
        db,
        dados_mercado
    )

    print("\n" + "=" * 55)
    print("FINALIZADO COM SUCESSO!")
    print("=" * 55)

    print("\nBanco utilizado:")
    print(DATABASE_NAME)

    print("\nCollections:")
    print("- clubes_rodada_atual")
    print("- atletas_rodada_atual")
    print("- mercado_rodada_atual")


# ============================================================
# INÍCIO DO PROGRAMA
# ============================================================

if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print("\nExecução interrompida pelo usuário.")

    except Exception as erro:
        print(f"\nErro durante a execução: {erro}")