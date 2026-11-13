import os
import sqlite3
import tempfile
import shutil

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID, DATABASE_NAME
from log import log_erro


# =========================================================
# /restaurar (SÓ ADMIN, SÓ NO PRIVADO)
# Recebe um bot.db pelo Telegram e carrega no banco do bot.
# =========================================================

TABELAS_OBRIGATORIAS = {
    "usuarios",
    "produtos",
    "pedidos",
    "pagamentos",
    "logins",
    "configuracoes",
}

CHAVE = "aguardando_restauracao"


def _eh_admin(user_id):
    try:
        return int(user_id) == int(ADMIN_ID)
    except (ValueError, TypeError):
        return False


def restaurar_de_arquivo(caminho_origem, destino=None):
    """
    Valida o arquivo e copia o conteúdo para o banco em uso,
    usando a API de backup do SQLite (segura com WAL).
    Devolve um dict com contagens ou levanta ValueError.
    """

    destino = destino or DATABASE_NAME

    try:
        origem = sqlite3.connect(
            f"file:{caminho_origem}?mode=ro",
            uri=True,
        )
        tabelas = {
            linha[0]
            for linha in origem.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            )
        }
        integridade = origem.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
    except sqlite3.DatabaseError:
        raise ValueError(
            "Esse arquivo não é um banco SQLite válido."
        )

    if integridade != "ok":
        origem.close()
        raise ValueError(
            "O banco enviado está corrompido."
        )

    faltando = TABELAS_OBRIGATORIAS - tabelas

    if faltando:
        origem.close()
        raise ValueError(
            "Esse não parece ser o banco do bot "
            "(faltam tabelas: "
            + ", ".join(sorted(faltando))
            + ")."
        )

    # Cópia de segurança do banco atual, dentro do mesmo
    # volume, antes de sobrescrever.
    if os.path.exists(destino):
        try:
            atual = sqlite3.connect(destino, timeout=30)
            seguranca = sqlite3.connect(
                destino + ".antes_restaurar"
            )
            atual.backup(seguranca)
            seguranca.close()
            atual.close()
        except sqlite3.DatabaseError:
            pass

    alvo = sqlite3.connect(destino, timeout=30)

    try:
        origem.backup(alvo)
        resumo = {
            nome: alvo.execute(
                f'SELECT COUNT(*) FROM "{nome}"'
            ).fetchone()[0]
            for nome in (
                "usuarios",
                "produtos",
                "pedidos",
                "logins",
            )
        }
    finally:
        alvo.close()
        origem.close()

    return resumo


async def comando_restaurar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    if not usuario or not update.message:
        return

    if not _eh_admin(usuario.id):
        return

    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "❌ Use o /restaurar só no privado com o bot."
        )
        return

    try:
        conn = sqlite3.connect(DATABASE_NAME, timeout=30)
        qtd = conn.execute(
            "SELECT COUNT(*) FROM usuarios"
        ).fetchone()[0]
        conn.close()
    except sqlite3.DatabaseError:
        qtd = 0

    context.user_data[CHAVE] = True

    aviso = (
        f"⚠️ O banco atual tem {qtd} usuário(s) e será "
        "SUBSTITUÍDO pelo arquivo que você enviar.\n\n"
        if qtd > 1
        else ""
    )

    await update.message.reply_text(
        aviso
        + "📥 Envie agora o arquivo bot.db aqui no chat "
        "(como documento). Para cancelar, mande /cancelar."
    )


async def cancelar_restauracao(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if context.user_data.pop(CHAVE, None):
        await update.message.reply_text(
            "Restauração cancelada."
        )


async def receber_banco_restaurar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    if not usuario or not update.message:
        return

    if not _eh_admin(usuario.id):
        return

    if update.effective_chat.type != "private":
        return

    if not context.user_data.get(CHAVE):
        return

    documento = update.message.document

    if not documento:
        return

    if documento.file_size and documento.file_size > 15_000_000:
        await update.message.reply_text(
            "❌ Arquivo grande demais."
        )
        return

    pasta = tempfile.mkdtemp()
    caminho = os.path.join(pasta, "recebido.db")

    try:
        arquivo = await documento.get_file()
        await arquivo.download_to_drive(caminho)

        resumo = restaurar_de_arquivo(caminho)

        context.user_data.pop(CHAVE, None)

        await update.message.reply_text(
            "✅ Banco restaurado com sucesso!\n\n"
            f"👤 Usuários: {resumo['usuarios']}\n"
            f"📦 Produtos: {resumo['produtos']}\n"
            f"🧾 Pedidos: {resumo['pedidos']}\n"
            f"🔑 Logins: {resumo['logins']}\n\n"
            "Apague a mensagem com o arquivo deste chat, "
            "pois ele contém dados dos clientes."
        )

    except ValueError as erro:
        await update.message.reply_text(f"❌ {erro}")

    except Exception as erro:
        log_erro("ERRO AO RESTAURAR BANCO:", repr(erro))
        await update.message.reply_text(
            "❌ Não foi possível restaurar o banco."
        )

    finally:
        shutil.rmtree(pasta, ignore_errors=True)
