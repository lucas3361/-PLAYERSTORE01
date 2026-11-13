from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# =========================================================
# DINHEIRO (REAIS COM 2 CASAS, SEM RUÍDO DE FLOAT)
# =========================================================
# O banco guarda valores em REAL (reais). O problema do float
# não é guardar, é deixar entrar valores com mais de 2 casas
# (ex.: 10.999) ou com ruído (0.1 + 0.2 = 0.30000000000000004)
# e depois comparar/somar. Por isso TODO valor em reais passa
# por normalizar() antes de ser gravado: arredonda para
# centavos (meio pra cima) usando Decimal, não float.


def normalizar(valor):
    """Devolve o valor em reais arredondado a 2 casas.
    Levanta ValueError para nan/inf ou texto inválido."""

    try:
        decimal = Decimal(
            str(valor).strip().replace(",", ".")
        )
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Valor monetário inválido: {valor!r}")

    if not decimal.is_finite():
        raise ValueError(f"Valor monetário inválido: {valor!r}")

    return float(
        decimal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


def em_centavos(valor):
    """Valor em reais -> inteiro em centavos."""

    return int(
        (Decimal(str(normalizar(valor))) * 100)
        .to_integral_value()
    )


def de_centavos(centavos):
    """Inteiro em centavos -> valor em reais (2 casas)."""

    return normalizar(Decimal(int(centavos)) / 100)
