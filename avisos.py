import re

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from database import (
    obter_configuracao,
    consultar_usuario,
    registrar_mensagem_grupo_anuncios,
)
from log import log_info, log_erro


# =========================================================
# AVISOS PÚBLICOS DE VENDA / SALDO NO GRUPO DE ANÚNCIOS
# Ligados por padrão; o admin liga/desliga pelo /admin.
# =========================================================

CONFIG_AVISOS_VENDAS = "avisos_vendas_grupo_ativo"


def avisos_vendas_ativos():
    return (
        obter_configuracao(CONFIG_AVISOS_VENDAS, "1") == "1"
    )


def _identificacao(nome, usuario_id):
    """Só um pedaço do nome ('Ana…') ou 'Cliente #1234'.
    Nunca expõe nome completo nem @username."""

    nome_limpo = re.sub(
        r"[*_\[\]]",
        "",
        (nome or "").strip(),
    )

    if len(nome_limpo) >= 2:
        return f"{nome_limpo[:3]}…"

    return f"Cliente #{str(usuario_id)[-4:]}"


async def anunciar_saldo_grupo(
    bot,
    usuario_id,
    valor,
):
    """Avisa no grupo que um cliente adicionou saldo."""

    try:
        if not avisos_vendas_ativos():
            return

        grupo_id = obter_configuracao("grupo_anuncios_id")

        if not grupo_id:
            return

        try:
            grupo_id_int = int(grupo_id)
        except ValueError:
            return

        usuario = consultar_usuario(usuario_id)
        nome = usuario[1] if usuario else None

        me = await bot.get_me()

        mensagem = await bot.send_message(
            chat_id=grupo_id_int,
            text=(
                "💳 *SALDO ADICIONADO!*\n\n"
                f"👤 {_identificacao(nome, usuario_id)} "
                f"adicionou R$ {float(valor):.2f} "
                "de saldo\n"
                "⚡ Bora garantir o seu antes que "
                "acabe! 🛒🔥"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🤖 Acessar o bot",
                            url=f"https://t.me/{me.username}",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        registrar_mensagem_grupo_anuncios(
            grupo_id_int,
            mensagem.message_id,
        )

        log_info(
            f"✅ Saldo anunciado no grupo {grupo_id_int}"
        )

    except Exception as erro:
        log_erro(
            "ERRO AO ANUNCIAR SALDO:",
            repr(erro),
        )
