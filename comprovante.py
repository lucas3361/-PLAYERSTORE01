from datetime import datetime, timedelta, timezone

from config import NOME_DA_LOJA

# =========================================================
# COMPROVANTE DE COMPRA (TEXTO PRONTO PARA O TELEGRAM)
# =========================================================
# Um único lugar monta o comprovante, para que a mensagem de
# entrega (compra direta e carrinho) e o "Detalhes da compra"
# do histórico tenham SEMPRE o mesmo visual e mostrem data e
# hora no horário de Brasília (o banco guarda em UTC).

try:
    from zoneinfo import ZoneInfo

    FUSO = ZoneInfo("America/Sao_Paulo")
except Exception:
    # Sem tzdata no servidor: o Brasil não tem horário de
    # verão desde 2019, então UTC-3 fixo é equivalente.
    FUSO = timezone(timedelta(hours=-3))

LINHA = "━━━━━━━━━━━━━━━━━━"


def agora():
    return datetime.now(FUSO)


def de_utc(texto):
    """'2026-11-13 07:49:46' (UTC, como vem do banco) ->
    datetime no horário de Brasília. None se não der."""

    if texto is None:
        return None

    try:
        momento = datetime.fromisoformat(
            str(texto).strip().replace("Z", "")
        )
    except ValueError:
        return None

    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)

    return momento.astimezone(FUSO)


def data_hora(momento):
    """-> ('13/11/2026', '04:49')"""

    return (
        momento.strftime("%d/%m/%Y"),
        momento.strftime("%H:%M"),
    )


def data_hora_curta(texto_utc):
    """Para botões: '13/11 04:49'. Se a data for inválida,
    devolve os 16 primeiros caracteres do que veio."""

    momento = de_utc(texto_utc)

    if not momento:
        return str(texto_utc or "")[:16]

    return momento.strftime("%d/%m %H:%M")


def _esc(texto):
    """Escapa caracteres do Markdown do Telegram."""

    texto = str(texto)

    for caractere in ("\\", "_", "*", "`", "["):
        texto = texto.replace(caractere, "\\" + caractere)

    return texto


def _item(item, quando):
    linhas = ""

    pedido_id = item.get("pedido_id")

    if pedido_id:
        linhas += f"🔖 *Pedido:* #{pedido_id}\n"

    quantidade = int(item["quantidade"])
    unitario = float(item["preco_unitario"])

    linhas += (
        f"🛒 *Produto:* {_esc(item['nome'])}\n"
        f"📦 *Quantidade:* {quantidade}\n"
        f"💰 *Valor unitário:* R$ {unitario:.2f}\n"
        f"💵 *Subtotal:* R$ {unitario * quantidade:.2f}\n"
    )

    dias = item.get("duracao_dias")

    if dias:
        dias = int(dias)
        vence = quando + timedelta(days=dias)
        linhas += (
            f"⏳ *Validade:* {dias} dia(s)\n"
            f"📆 *Vence em:* {vence.strftime('%d/%m/%Y')}\n"
        )

    linhas += "\n🎁 *DADOS DE ACESSO*\n"

    contas = item.get("contas") or []

    if not contas:
        linhas += (
            "⚠️ Nenhum dado de acesso encontrado — "
            "fale com o suporte.\n"
        )

    for indice, dados in enumerate(contas, start=1):
        linhas += (
            f"🔐 *Conta {indice}*\n"
            f"```\n{dados}\n```\n"
        )

    return linhas


def montar_comprovante(
    itens,
    quando=None,
    total=None,
    novo_saldo=None,
    agradecer=True,
    rodape=True,
):
    """Monta o comprovante.

    `itens`: lista de dicts com nome, quantidade,
    preco_unitario, contas e, opcionais, pedido_id e
    duracao_dias.
    `quando`: datetime da compra (Brasília). Padrão: agora.
    `total`/`novo_saldo`: se informados, aparecem no fim."""

    quando = quando or agora()

    data, hora = data_hora(quando)

    texto = ""

    if agradecer:
        texto += "🙏 *Obrigado pela sua compra!*\n\n"

    texto += (
        "🧾 *COMPROVANTE DE COMPRA*\n"
        f"🏪 *{_esc(NOME_DA_LOJA)}*\n"
        f"{LINHA}\n"
        f"📅 *Data:* {data}\n"
        f"🕐 *Hora:* {hora} (Brasília)\n"
        f"{LINHA}\n"
    )

    for item in itens:
        texto += _item(item, quando)
        texto += f"{LINHA}\n"

    if total is not None:
        texto += f"💵 *Total pago:* R$ {float(total):.2f}\n"

    if novo_saldo is not None:
        texto += (
            f"💳 *Saldo restante:* R$ {float(novo_saldo):.2f}\n"
        )

    if total is not None or novo_saldo is not None:
        texto += f"{LINHA}\n"

    if rodape:
        texto += (
            "\n⚡ Entrega realizada automaticamente.\n"
            "🔒 Guarde este comprovante: ele fica salvo no "
            "seu *Histórico de compras*.\n"
            "💬 Qualquer dúvida, é só chamar o suporte!"
        )

    return texto
