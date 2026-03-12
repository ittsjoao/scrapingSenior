"""
Lê um arquivo validacao_*.json e exibe um relatório resumido.

Uso:
    python validador/relatorio_validacao.py [validacao_*.json] [--detalhes] [--so-alertas]

    --detalhes    Exibe rubricas e alertas de cada empresa
    --so-alertas  Exibe apenas empresas com alertas ou não encontrados
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DADOS_SAIDA = Path(__file__).parent.parent / "dados" / "saida"


def _json_mais_recente(prefixo: str) -> str | None:
    arquivos = sorted(DADOS_SAIDA.glob(f"{prefixo}_*.json"), reverse=True)
    return str(arquivos[0]) if arquivos else None


def _carregar_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def formatar_cnpj(cnpj: str) -> str:
    c = cnpj.zfill(14)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    detalhes = "--detalhes" in flags
    so_alertas = "--so-alertas" in flags

    path = args[0] if args else _json_mais_recente("validacao")
    if not path:
        print("[ERRO] Nenhum validacao_*.json encontrado em dados/saida/")
        sys.exit(1)

    print(f"[Relatório] {path}\n")
    data = _carregar_json(path)

    total = len(data)
    com_alerta = 0
    nao_auditadas = 0

    linhas = []
    for cnpj, emp in data.items():
        nome = emp.get("nome", "?")
        auditado_em = emp.get("auditado_em", "")
        rubricas = emp.get("rubricas", [])
        nao_enc = emp.get("nao_encontrados", [])
        alertas = emp.get("alertas", [])

        if not auditado_em:
            nao_auditadas += 1

        tem_problema = bool(nao_enc or alertas)
        if tem_problema:
            com_alerta += 1

        if so_alertas and not tem_problema:
            continue

        status = "OK" if not tem_problema else f"ALERTAS({len(alertas)}) NAO_ENC({len(nao_enc)})"
        linhas.append((cnpj, nome, auditado_em, rubricas, nao_enc, alertas, status))

    # Exibe por empresa
    for cnpj, nome, auditado_em, rubricas, nao_enc, alertas, status in linhas:
        data_str = auditado_em[:19].replace("T", " ") if auditado_em else "não auditado"
        print(f"{'─'*70}")
        print(f"  CNPJ : {formatar_cnpj(cnpj)}")
        print(f"  Nome : {nome}")
        print(f"  Data : {data_str}")
        print(f"  Status: {status}")
        print(f"  Rubricas OK : {len(rubricas)}")

        if nao_enc:
            print(f"  Não encontrados ({len(nao_enc)}):")
            for item in nao_enc:
                print(f"    • {item}")

        if detalhes and alertas:
            print(f"  Alertas ({len(alertas)}):")
            for alerta in alertas:
                print(f"    ⚠ {alerta}")

        if detalhes and rubricas:
            print(f"  Rubricas ({len(rubricas)}):")
            for r in rubricas:
                irrf_ok = r.get("irrf_atual") == r.get("irrf_esperado")
                marca = "✓" if irrf_ok else "✗"
                print(f"    {marca} [{r.get('tabela')}] {r.get('nome_evento')} "
                      f"| IRRF atual={r.get('irrf_atual')} esperado={r.get('irrf_esperado')} "
                      f"| {r.get('status')}")

    # Resumo final
    print(f"\n{'═'*70}")
    print(f"  Total empresas   : {total}")
    print(f"  Com alertas      : {com_alerta}")
    print(f"  Sem alertas      : {total - com_alerta - nao_auditadas}")
    print(f"  Não auditadas    : {nao_auditadas}")
    print(f"{'═'*70}")


if __name__ == "__main__":
    main()
