import os
import subprocess
import psycopg2
from datetime import datetime, date
import shutil
import pyAesCrypt
import pyminizip
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import subprocess

# -------------------------------
# Configurações do banco
# -------------------------------
DB_CONFIG = {
    "dbname": "meu_banco",
    "user": "postgres",
    "password": "daminelli",   # usado apenas na variável de ambiente
    "host": "localhost",
    "port": "5432"
}



# -------------------------------
# Configurações de backup
# -------------------------------
PARAMS = {
    "caminho_destino": "C:\\Temp\\Backup\\",
    "quantidade_manter": 5,
    "caminho_copia_adicional": "Z:\\",
    "vacuum": "S",
    "full": "S",
    "criptografia": "S",  # AES
    "compactar": "S",
    "senha_aes": "1234"   # senha usada tanto para AES quanto ZIP
}


# Caminho completo para o pg_dump
PG_DUMP_PATH = r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"

# Arquivo de log
LOG_FILE = os.path.join(PARAMS["caminho_destino"], "backup_log.txt")

BUFFER_SIZE = 64 * 1024  # buffer para pyAesCrypt

# -------------------------------
# Função para registrar log
# -------------------------------
def registrar_log(mensagem):
    os.makedirs(PARAMS["caminho_destino"], exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - {mensagem}\n")
    print(mensagem)


EMAIL_CONFIG = {
    "servidor": "smtp.gmail.com",
    "porta": 587,
    "usuario": "teste@gmail.com",
    "senha": "senhadoapgmail",  
    "remetente": "teste@gmail.com",
    "destinatario": "michelli.daminelli2004@gmail.com"
}

def emailErroEnviar(mensagem):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["remetente"]
        msg["To"] = EMAIL_CONFIG["destinatario"]
        msg["Subject"] = "❌ Erro no Backup"

        msg.attach(MIMEText(mensagem, "plain"))

        with smtplib.SMTP(EMAIL_CONFIG["servidor"], EMAIL_CONFIG["porta"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["usuario"], EMAIL_CONFIG["senha"])
            server.send_message(msg)

        print("Email de erro enviado com sucesso!")

    except Exception as e:
        print(f"Falha ao enviar email: {e}")


def executar_vacuum(tabela="exemplo_vacuo", forcar=False):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()

   
        cur.execute("""
        CREATE TABLE IF NOT EXISTS controle_vacuum (
            id serial PRIMARY KEY,
            tabela_nome text NOT NULL,
            ultima_execucao timestamp NOT NULL,
            tipo_vacuum text
        );
        """)


        cur.execute(
            "SELECT ultima_execucao FROM controle_vacuum WHERE tabela_nome = %s "
            "ORDER BY ultima_execucao DESC LIMIT 1;",
            [tabela]
        )
        row = cur.fetchone()

        comando = None
        tipo = None

        if row is None:
            comando = f"VACUUM FULL ANALYZE {tabela};"
        else:
            dias_diferenca = (date.today() - row[0].date()).days
            if dias_diferenca < 5:
                registrar_log(f"Último VACUUM foi há {dias_diferenca} dias. Não é necessário executar novamente.")
            elif 5 <= dias_diferenca <= 10:
                comando = f"VACUUM {tabela};"
            elif dias_diferenca > 10:
                comando = f"VACUUM FULL ANALYZE {tabela};"

        if comando:
            registrar_log(f"Executando: {comando}")
            cur.execute(comando)
            cur.execute(
                "INSERT INTO controle_vacuum(tabela_nome, ultima_execucao, tipo_vacuum) "
                "VALUES (%s, CURRENT_TIMESTAMP, %s);",
                [tabela, tipo]
            )

        cur.close()
        conn.close()

    except Exception as e:
        emailErroEnviar(f"Falha no VACUUM: {e}")
        raise


def processoIniciar():
    try:
        os.makedirs(PARAMS["caminho_destino"], exist_ok=True)
        data = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{DB_CONFIG['dbname']}_{data}.backup"
        caminho_arquivo = os.path.join(PARAMS["caminho_destino"], nome_arquivo)

        comando = [
            PG_DUMP_PATH,
            "-U", DB_CONFIG["user"],
            "-F", "c",  
            "-b",
            "-f", caminho_arquivo,
            DB_CONFIG["dbname"]
        ]

        registrar_log(f"Iniciando backup: {caminho_arquivo}")

        env = os.environ.copy()
        env['PGPASSWORD'] = DB_CONFIG["password"]

        subprocess.run(comando, check=True, env=env)
        return caminho_arquivo
    except Exception as e:
        emailErroEnviar(f"Falha no processoIniciar: {e}")
        raise


def backupCriptografar(caminho_arquivo):
    try:
        if PARAMS["criptografia"] == "S":
            caminho_cripto = caminho_arquivo + ".aes"
            registrar_log(f"Criptografando backup para {caminho_cripto}")
            pyAesCrypt.encryptFile(caminho_arquivo, caminho_cripto, PARAMS["senha_aes"], BUFFER_SIZE)
            os.remove(caminho_arquivo)
            return caminho_cripto
        return caminho_arquivo
    except Exception as e:
        emailErroEnviar(f"Falha na criptografia: {e}")
        raise


def backupCompactar(caminho_arquivo):
    try:
        if PARAMS["compactar"] == "S":
            zip_path = os.path.splitext(caminho_arquivo)[0] + ".zip"
            registrar_log(f"Compactando backup em ZIP protegido por senha: {zip_path}")
            pyminizip.compress(caminho_arquivo, None, zip_path, PARAMS["senha_aes"], 5)
            os.remove(caminho_arquivo)
            return zip_path
        return caminho_arquivo
    except Exception as e:
        emailErroEnviar(f"Falha na compactação: {e}")
        raise


def antigosExcluir():
    try:
        arquivos = sorted(
            [f for f in os.listdir(PARAMS["caminho_destino"]) if f.endswith(".zip")],
            key=lambda x: os.path.getctime(os.path.join(PARAMS["caminho_destino"], x))
        )
        while len(arquivos) > PARAMS["quantidade_manter"]:
            apagar = arquivos.pop(0)
            os.remove(os.path.join(PARAMS["caminho_destino"], apagar))
            registrar_log(f"Backup antigo removido: {apagar}")
    except Exception as e:
        emailErroEnviar(f"Falha ao excluir antigos: {e}")
        raise


def backupCopiar(caminho_arquivo):
    try:
        if PARAMS["caminho_copia_adicional"]:
            destino = os.path.join(PARAMS["caminho_copia_adicional"], os.path.basename(caminho_arquivo))
            shutil.copy2(caminho_arquivo, destino)
            registrar_log(f"Cópia adicional salva em: {destino}")
    except Exception as e:
        emailErroEnviar(f"Falha ao copiar backup: {e}")
        raise


def processoFinalizar():
    try:
        registrar_log("✅ Processo concluído com sucesso.")
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)  
            print("Arquivo de log removido após conclusão bem-sucedida.")
    except Exception as e:
        emailErroEnviar(f"Falha ao finalizar processo: {e}")


if __name__ == "__main__":
    try:
        if PARAMS["vacuum"] == "S":
            executar_vacuum("exemplo_vacuo", forcar=(PARAMS["full"] == "S"))
            
        caminho = processoIniciar()
        caminho = backupCriptografar(caminho)
        caminho = backupCompactar(caminho)
        antigosExcluir()
        backupCopiar(caminho)
        processoFinalizar()

    except Exception as e:
        emailErroEnviar(f"Erro inesperado: {e}")
