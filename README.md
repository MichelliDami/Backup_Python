# Backup_Python
Documentação – Processo de Backup em Python

Este projeto foi desenvolvido em Python com o objetivo de implementar um processo simples e automatizado de backup.

🔹 Funcionalidades do Programa

Limpeza de dados (VACUUM):

Antes de iniciar o backup, é executado o VACUUM FULL ou VACUUM FULL ANALYZE, conforme regras estabelecidas.

O controle de execução é feito por tabela, evitando execuções desnecessárias.

Criptografia e Backup:

Os dados são exportados e gravados na pasta de destino definida.

O backup é compactado em .zip com senha.

Exclusão de Backups Antigos:

Mantém apenas a quantidade configurada de arquivos.

Quando o limite é atingido, o mais antigo é excluído automaticamente.

Cópia Adicional (opcional):

O backup pode ser duplicado para um diretório adicional.

Logs e Finalização:

Todo o processo gera logs por etapas.

Em caso de falha, um e-mail é enviado automaticamente com os registros.

Ao finalizar com sucesso, os logs antigos são removidos.



Passo a Passo de Implantação

1) Criar tabelas de exemplo no banco

-- Tabela principal para simulação
CREATE TABLE exemplo_vacuo (
    id bigserial PRIMARY KEY,
    codigo text,
    quantidade int,    -- ex: código do item (antes era 'sku' ou 'qty')
    marcado boolean    -- antes era 'flag'
);

-- Inserir 1 milhão de linhas
INSERT INTO exemplo_vacuo (codigo, quantidade, marcado)
SELECT 'ITEM-' || g, (random() * 100)::int, (random() > 0.5)
FROM generate_series(1, 1000000) AS g;

-- Criar tuplas mortas (~30% atualização, ~20% exclusão)
UPDATE exemplo_vacuo
SET quantidade = quantidade + 1
WHERE id % 10 IN (1,2,3);

DELETE FROM exemplo_vacuo
WHERE id % 5 = 0;

Criar tabela de controle do VACUUM:

CREATE TABLE IF NOT EXISTS controle_vacuum (
    id serial PRIMARY KEY,
    tabela_nome text NOT NULL,
    ultima_execucao timestamp NOT NULL,
    tipo_vacuum text
);


2) Configuração de Banco no Python

DB_CONFIG = {
    "dbname": "meu_banco",
    "user": "postgres",
    "password": "daminelli",  # usar variável de ambiente em produção
    "host": "localhost",
    "port": "5432"
}

3) Parâmetros do Backup

PARAMS = {
    "caminho_destino": "C:\\Temp\\Backup\\",        # Pasta principal
    "quantidade_manter": 5,                         # Nº de arquivos a manter
    "caminho_copia_adicional": "Z:\\",              --> Aqui criamos uma pasta compartilhada na rede em outro computador e configuramos o acesso na maquina, onde importa a cópia do beckup.
    "vacuum": "S",                                  # Executar VACUUM? (S/N)
    "full": "S",                                    # Usar FULL? (S/N)
    "criptografia": "S",                            # Ativar criptografia AES
    "compactar": "S",                               # Compactar em ZIP
    "senha_aes": "1234"                             # Senha AES/ZIP
}

4) Configuração do pg_dump

PG_DUMP_PATH = r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"

6) Configuração de Envio de E-mail

EMAIL_CONFIG = {
    "servidor": "smtp.gmail.com",   # Para Gmail
    "porta": 587,
    "usuario": "teste@gmail.com",   # Usuário
    "senha": "senha_de_app",        # Senha de aplicativo do Gmail
    "remetente": "teste@gmail.com",
    "destinatario": "michelli.daminelli2004@gmail.com"
}



Regras do VACUUM

O controle de execução segue a seguinte lógica:

if row is None:
    comando = f"VACUUM FULL ANALYZE {tabela};"
else:
    dias_diferenca = (date.today() - row[0].date()).days
    if dias_diferenca < 5:
        registrar_log(f" Último VACUUM foi há {dias_diferenca} dias. Não é necessário executar novamente.")
    elif 5 <= dias_diferenca <= 10:
        comando = f"VACUUM {tabela};"
    elif dias_diferenca > 10:
        comando = f"VACUUM FULL ANALYZE {tabela};"

**Menor que 5 dias → Não executa, apenas registra log.
**Entre 5 e 10 dias → Executa VACUUM.
**Maior que 10 dias → Executa VACUUM FULL ANALYZE.

Fluxo Resumido:

1-Verifica se precisa rodar VACUUM.

2-Gera dump com pg_dump.

3-Criptografa e compacta em .zip protegido por senha.

4-Aplica política de retenção (mantém últimos N backups).

5-Faz cópia adicional, neste exemplo criamos uma pasta compartilhada na rede onde importa o arquivo zip. Também deve-se realizar as configurações de conexão.

7-Registra logs de cada etapa.

8-Em caso de falha → envia e-mail com erro.

9-Em sucesso → remove logs antigos.




