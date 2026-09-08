#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera a dashboard estatica (index.html) para a Thata Junqueira (funil "Sessao
Estrategica" / "Sala Secreta"). Diferente do template padrao (1 planilha com
4 abas prontas), este cliente tem DUAS planilhas Google Sheets distintas:

  1) Planilha "Meta Ads" (SPREADSHEET_ID_META), aba unica (GID_META):
     investimento/impressoes/cliques/leads do gerenciador de midia. Valores de
     gasto ("Amount Spent") vem NATIVOS EM USD (a conta e' americana) — o
     Python NAO converte, so' grava o valor cru em meta[].sp; a conversao pro
     toggle de moeda (BRL/USD) acontece no app.js, no navegador, ao vivo (ver
     "Conversao de moeda" abaixo).

  2) Planilha "Central de Eventos - 2026" (SPREADSHEET_ID_LEADS), com 3 abas:
       - "Central de Leads" (GID_LEADS): fonte PRINCIPAL de leads (todas as
         campanhas, prefixos OPN/OPNF tratados como 1 cliente so', sem filtro).
         Criterio de MQL: coluna "Qualificacao" == "qualificado" (is_mql).
         Criterio de "Lead A" (subconjunto MAIS qualificado, METRICA PARALELA
         ao MQL, nunca substituta): coluna "Lead Scoring" == "A" (is_lead_a).
         So' comecou a ser preenchida em 03/08/2026 em diante — datas
         anteriores ficam com Lead A = 0 (coluna vazia).
       - "Agendamentos" (GID_AGENDAMENTOS): 1 linha por agendamento no
         Calendly. Cruzada com a Central de Leads por TELEFONE (canon_phone)
         E, quando o telefone nao bate, por E-MAIL normalizado (fallback) —
         diferente do template padrao (so' telefone) porque o comercial desse
         cliente usa e-mail com frequencia. Alimenta DATA.agendamentos[], um
         registro por agendamento (nao agregado), no MESMO padrao de sales[]:
         data REAL do agendamento, camp/adset/ad vem da 1a conversa (lead)
         daquele telefone/e-mail.
       - "Compradores" (GID_SALES): vendas. Cruzada por telefone OU e-mail
         (mesma logica). Usa "Fat. liquido (USD)" como faturamento (decisao
         do cliente: liquido em dolar, nao o bruto em BRL) — NATIVO EM USD,
         mesmo padrao do gasto do Meta Ads; o toggle de moeda multiplica/
         divide pela cotacao ao vivo no app.js.

Nao ha' imposto de midia para este cliente (TAX_FACTOR = 1.0).

Conversao de moeda (USD->BRL): a cotacao e' buscada 1x por build (funcao
fetch_usd_brl_rate(), com fallback fixo se todas as APIs falharem — o build
NUNCA quebra por causa disso) e gravada em data["build"]["usd_brl_rate"]. O
gasto (meta[].sp) continua nativo em USD no JSON; o toggle "BRL/USD" da
topbar (STATE.currency em app.js) e' quem multiplica/divide pela taxa ao
vivo no navegador — igual ao toggle de imposto (STATE.tax) ja existente.

Este script apenas LE as planilhas (export CSV publico) e emite os REGISTROS
BRUTOS (leads[], meta[], sales[], agendamentos[]) dentro do HTML. sales[] e
agendamentos[] tem um registro POR LINHA (nunca agregado), com a DATA REAL do
evento — camp/adset/ad vem da 1a conversa (lead) daquele telefone/e-mail
(atribuicao do anuncio de origem), mas a data nunca e' a da conversa. Todos
os filtros, agregacoes, KPIs, tabelas e graficos sao calculados no navegador
(client-side). Nunca escreve nada de volta nas planilhas.

Teste local: --leads-file / --meta-file / --agendamentos-file / --sales-file
apontando para CSVs baixados (ver README / CLAUDE.md p/ os cabecalhos exatos).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

# --------------------------------------------------------------------------- #
# Planilhas do cliente
# --------------------------------------------------------------------------- #
SPREADSHEET_ID_META = "14yy7dhldcjPC2VzkXOfzGaS-kdqn5c3y3GWOm4vGj3c"   # planilha "Meta Ads"
SPREADSHEET_ID_LEADS = "1v3mc-Z3lUYzGGkyIIYdK9PL3M-O6cgIBTlUWHQDboGU"  # "Central de Eventos - 2026"

GID_META = "0"                  # aba unica da planilha Meta Ads
GID_LEADS = "0"                 # aba "Central de Leads" (fonte principal)
GID_AGENDAMENTOS = "1722749521"  # aba "Agendamentos" (Calendly)
GID_SALES = "86137300"          # aba "Compradores"

EXPORT_URL = "https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"

# Identificacao do cliente/conta (usada so' em textos/relatorios — nao afeta o cruzamento de dados).
CLIENT_NAME = "Thata Junqueira"
MAIN_PRODUCT = "Sessão Estratégica"
# Prefixo mais comum das campanhas (documental/label apenas — NAO filtra nada:
# o cliente usa "OPN" e "OPNF" nas campanhas e a decisao foi tratar tudo como
# 1 cliente so', sem filtrar por prefixo em lugar nenhum do codigo).
MAIN_PRODUCT_PREFIX = "OPN"

BRT = timezone(timedelta(hours=-3))   # horario de Brasilia (exibicao)
TAX_FACTOR = 1.0   # sem imposto de midia para este cliente

# --------------------------------------------------------------------------- #
# Regras da aba Relatório (Top/Piores anúncios)
# --------------------------------------------------------------------------- #
SAMPLE_MIN_SPEND = 100.0   # gasto mínimo (R$) para amostra relevante
SAMPLE_MIN_MQLS = 3        # MQLs mínimos para julgar qualidade profunda
TOP_ADS_N = 10             # nº de linhas em Top / Piores anúncios

META_CPMQL = None          # meta de CPMQL (R$/MQL); None = não definida
META_CAC = None            # meta de CAC (R$/venda); None = não definida
VOLUME_MIN_AMOSTRAL = SAMPLE_MIN_MQLS
N_DIAS_CORTE = 5

# --------------------------------------------------------------------------- #
# Cambio USD -> BRL
# --------------------------------------------------------------------------- #
USD_BRL_FALLBACK = 5.30   # usado só se TODAS as APIs abaixo falharem
# APIs publicas gratuitas, sem chave. Tentadas em ordem; a 1a que responder
# com um numero valido vence. Nunca deixa o build quebrar por causa da cotação.
_FX_APIS = [
    ("https://economia.awesomeapi.com.br/last/USD-BRL", lambda o: float(o["USDBRL"]["bid"])),
    ("https://api.frankfurter.app/latest?from=USD&to=BRL", lambda o: float(o["rates"]["BRL"])),
    ("https://api.exchangerate-api.com/v4/latest/USD", lambda o: float(o["rates"]["BRL"])),
]


def fetch_usd_brl_rate() -> float:
    for url, extract in _FX_APIS:
        for attempt in range(1, 3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "dash-template-bot/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    obj = json.loads(resp.read().decode("utf-8", errors="replace"))
                rate = extract(obj)
                if rate and rate > 0:
                    return round(float(rate), 4)
            except Exception as exc:  # nunca deixar a cotação quebrar o build
                print(f"[fx] {url} tentativa {attempt}/2 falhou: {exc!r}", file=sys.stderr)
                if attempt < 2:
                    time.sleep(3)
    print(f"[fx] todas as APIs de câmbio falharam; usando fallback fixo USD/BRL={USD_BRL_FALLBACK}",
          file=sys.stderr)
    return USD_BRL_FALLBACK


# --------------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------------- #
FETCH_RETRIES = 3       # tentativas totais em caso de timeout/erro de rede no export CSV
FETCH_RETRY_DELAY = 15  # segundos entre tentativas (o Google Sheets às vezes trava a resposta)


def fetch_csv(url: str) -> list[list[str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "dash-template-bot/1.0"})
    last_err: Exception | None = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            return list(csv.reader(io.StringIO(raw)))
        except (TimeoutError, urllib.error.URLError) as exc:
            last_err = exc
            if attempt < FETCH_RETRIES:
                print(f"[fetch_csv] tentativa {attempt}/{FETCH_RETRIES} falhou ({exc!r}); "
                      f"tentando de novo em {FETCH_RETRY_DELAY}s...", file=sys.stderr)
                time.sleep(FETCH_RETRY_DELAY)
    raise last_err


def read_csv_file(path: str) -> list[list[str]]:
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.reader(f))


def load_rows(url: str, local: str | None) -> list[list[str]]:
    return read_csv_file(local) if local else fetch_csv(url)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str | None) -> str:
    return strip_accents((s or "").strip().lower())


def to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v).strip())
    if not s:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_date(v: str) -> str | None:
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d/%m/%y", "%b %d, %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def is_test_lead(rowtext: str) -> bool:
    return "<test lead" in rowtext.lower()


# --------------------------------------------------------------------------- #
# Critérios de qualificação (Thata Junqueira)
# --------------------------------------------------------------------------- #
def is_mql(v: str | None) -> bool:
    """MQL: coluna "Qualificação" (Central de Leads) == "qualificado"."""
    return norm(v) == "qualificado"


def is_lead_a(v: str | None) -> bool:
    """Lead A: coluna "Lead Scoring" (Central de Leads) == "A" — subconjunto
    MAIS qualificado que o MQL, métrica PARALELA (nunca substitui o MQL).
    Só começou a ser preenchida em 03/08/2026 em diante; vazio/outra letra = não."""
    return norm(v) == "a"


def is_mba_sale(v: str | None) -> bool:
    """Filtro de produto em "Compradores": esta dash considera SÓ as vendas do
    MBA (coluna "Produto" contendo "mba", case/acento-insensitive) — outras
    ofertas na mesma aba (ex.: Sessão Estratégica, Sala Secreta) ficam de
    fora do funil de vendas/faturamento (decisão do cliente)."""
    return "mba" in norm(v)


def is_reuniao_realizada(status: str | None) -> bool:
    """Sem confirmação dos valores exatos da coluna "Status" da aba
    Agendamentos — trata qualquer status que contenha "realiz" (normalizado,
    sem acento: cobre "Realizada"/"Realizado"/etc.) como Reunião Realizada."""
    return "realiz" in norm(status)


def pretty_dim(v: str) -> str:
    s = (v or "").strip()
    return s if s else "Sem resposta"


def mask_email(e: str) -> str:
    e = (e or "").strip()
    if "@" not in e:
        return "—"
    user, dom = e.split("@", 1)
    keep = user[:2] if len(user) > 2 else user[:1]
    return f"{keep}****@{dom}"


def mask_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p or "")
    return f"…{digits[-4:]}" if len(digits) >= 4 else "—"


def norm_phone(p: str) -> str:
    return re.sub(r"\D", "", p or "")


def canon_phone(p: str) -> str:
    """Chave CANÔNICA de telefone p/ cruzar Agendamentos/Compradores × Central
    de Leads, robusta a DDI "55" presente/ausente e ao 9º dígito do celular.
    DDD (2 díg.) + ÚLTIMOS 8 DÍGITOS. Números curtos/estrangeiros (< 10 díg.
    após limpar) voltam como estão, pra não colidir à toa."""
    d = norm_phone(p)
    if len(d) > 11 and d.startswith("55"):
        d = d[2:]
    if len(d) >= 10:
        return d[:2] + d[-8:]
    return d


def norm_email(e: str) -> str:
    return (e or "").strip().lower()


def first_last_initial(name: str) -> str:
    parts = (name or "").strip().split()
    if not parts:
        return "—"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][:1]}."


def valid_utm(campaign: str) -> bool:
    c = norm(campaign)
    return bool(c) and c not in ("-", "—", "nao encontrado")


# --------------------------------------------------------------------------- #
# Indexacao das colunas
# --------------------------------------------------------------------------- #
def header_index(header, wanted, fallback):
    idx = {}
    hn = [norm(h) for h in header]
    for key, aliases in wanted.items():
        found = None
        for a in aliases:
            a = norm(a)
            for i, h in enumerate(hn):
                if h == a or (a and a in h):
                    found = i
                    break
            if found is not None:
                break
        idx[key] = found if found is not None else fallback.get(key)
    return idx


def cell(row, i):
    if i is None or i < 0 or i >= len(row):
        return ""
    return (row[i] or "").strip()


# --------------------------------------------------------------------------- #
# Central de Leads -> lista de leads + índices de atribuição (telefone/e-mail)
# --------------------------------------------------------------------------- #
def read_leads(leads_rows):
    """Lê a aba "Central de Leads". Colunas (nesta ordem):
    Data, Nome, Email, Telefone, Funil, Página, Qualificação, Lead Scoring,
    UTM Source, UTM Medium, UTM Campaign, UTM Content, UTM Term, UTM id,
    Agendamento.
    UTM Campaign == Campaign Name do Meta Ads; UTM Content == Ad Name;
    UTM Medium usado como "Conjunto" (aproximação combinada com o cliente —
    a coluna real de Ad Set Name não existe nesta planilha)."""
    header = leads_rows[0] if leads_rows else []
    idx = header_index(
        header,
        {"created": ["data"], "name": ["nome"], "email": ["email", "e-mail"],
         "phone": ["telefone"], "funil": ["funil"], "pagina": ["pagina", "página"],
         "qualif": ["qualificacao", "qualificação"], "scoring": ["lead scoring"],
         "utm_source": ["utm source"], "utm_medium": ["utm medium"],
         "campaign": ["utm campaign"], "ad": ["utm content"],
         "utm_term": ["utm term"], "utm_id": ["utm id"]},
        {"created": 0, "name": 1, "email": 2, "phone": 3, "funil": 4, "pagina": 5,
         "qualif": 6, "scoring": 7, "utm_source": 8, "utm_medium": 9,
         "campaign": 10, "ad": 11, "utm_term": 12, "utm_id": 13},
    )

    leads = []
    # atribuição do ANÚNCIO/campanha (agendamentos/vendas) por telefone E por
    # e-mail: a 1ª conversa (linha) daquele contato é quem define camp/adset/ad
    # (mesma lógica do template padrão para telefone, estendida a e-mail porque
    # o comercial deste cliente casa boa parte dos agendamentos só por e-mail).
    rows_sorted = sorted(
        [r for r in leads_rows[1:] if any((c or "").strip() for c in r)],
        key=lambda r: parse_date(cell(r, idx["created"])) or "",
    )
    phone_attrib: dict[str, dict] = {}
    email_attrib: dict[str, dict] = {}
    for row in rows_sorted:
        if is_test_lead(" ".join(str(c) for c in row)):
            continue
        campaign_raw = cell(row, idx["campaign"])
        campaign_valid = valid_utm(campaign_raw)
        src = "meta" if campaign_valid else "org"
        phone = canon_phone(cell(row, idx["phone"]))
        email = norm_email(cell(row, idx["email"]))
        camp = campaign_raw if campaign_valid else "(sem campanha)"
        adset = cell(row, idx["utm_medium"]) if campaign_valid else "(sem conjunto)"
        if not adset:
            adset = "(sem conjunto)"
        ad = cell(row, idx["ad"]) if campaign_valid else "(sem anúncio)"
        lead_date = parse_date(cell(row, idx["created"]))
        attrib = {"src": src, "camp": camp, "adset": adset, "ad": ad, "d": lead_date}
        if phone and phone not in phone_attrib:
            phone_attrib[phone] = attrib
        if email and email not in email_attrib:
            email_attrib[email] = attrib
        funil = pretty_dim(cell(row, idx["funil"]))
        pagina = pretty_dim(cell(row, idx["pagina"]))
        leads.append({
            "d": lead_date,
            "src": src,
            "plat": "ig" if src == "meta" else "—",
            "camp": camp,
            "adset": adset,
            "ad": ad,
            # sem coluna de especialidade nesta planilha: usamos "Funil"/"Página"
            # como as dimensões de agrupamento (gráficos "Leads por Funil"/"por Página").
            "prof": pagina,
            "bucket": funil,
            "q": 1 if is_mql(cell(row, idx["qualif"])) else 0,
            "a": 1 if is_lead_a(cell(row, idx["scoring"])) else 0,
            "utm": 1 if campaign_valid else 0,
            "nm": first_last_initial(cell(row, idx["name"])),
            "em": "—",
            "ph": mask_phone(cell(row, idx["phone"])),
        })
    return leads, phone_attrib, email_attrib


def attrib_for(phone_attrib, email_attrib, phone, email, no_attrib):
    """Telefone primeiro, e-mail como fallback (pedido explícito do cliente —
    diferente do template padrão, que só cruza por telefone)."""
    return phone_attrib.get(phone) or (email and email_attrib.get(email)) or no_attrib


# --------------------------------------------------------------------------- #
# Agendamentos (Calendly) -> registros por agendamento (não agregado)
# --------------------------------------------------------------------------- #
def read_agendamentos(agd_rows, phone_attrib, email_attrib):
    """Lê a aba "Agendamentos". Colunas:
    ID Calendly, Data, Dia da Semana, Hora Início, Hora Fim, Consultora,
    Tipo de Evento, Convidado, Email, Telefone/WhatsApp, Status, Cancelado
    Por, Motivo do Cancelamento, Plataforma, Link da Reunião, Criado em,
    Funil Nota.
    Cada linha vira 1 registro em DATA.agendamentos[] (mesma filosofia de
    sales[]: não agregado, com a data REAL do agendamento; camp/adset/ad vêm
    do lead casado por telefone OU e-mail). "Status" contendo "realiz"
    (normalizado) marca Reunião Realizada — valores exatos da coluna não
    confirmados; ver decisão documentada no topo do arquivo."""
    header = agd_rows[0] if agd_rows else []
    idx = header_index(
        header,
        {"date": ["data"], "email": ["email"], "phone": ["telefone/whatsapp", "telefone"],
         "status": ["status"]},
        {"date": 1, "email": 8, "phone": 9, "status": 10},
    )
    NO_ATTRIB = {"src": "org", "camp": "(sem campanha)", "adset": "(sem conjunto)",
                 "ad": "(sem anúncio)", "d": None}
    out = []
    matched = 0
    total = 0
    for row in agd_rows[1:]:
        if not any((c or "").strip() for c in row):
            continue
        total += 1
        phone = canon_phone(cell(row, idx["phone"]))
        email = norm_email(cell(row, idx["email"]))
        attrib = attrib_for(phone_attrib, email_attrib, phone, email, NO_ATTRIB)
        if attrib is not NO_ATTRIB:
            matched += 1
        status = cell(row, idx["status"])
        out.append({
            "d": parse_date(cell(row, idx["date"])) or attrib["d"],
            "src": attrib["src"], "camp": attrib["camp"], "adset": attrib["adset"], "ad": attrib["ad"],
            "agendamentos": 1,
            "reunioes": 1 if is_reuniao_realizada(status) else 0,
        })
    print(f"  agendamentos atribuídos a anúncio: {matched}/{total} (cruzamento telefone OU e-mail)",
          file=sys.stderr)
    return out


# --------------------------------------------------------------------------- #
# Compradores -> registros por venda (não agregado)
# --------------------------------------------------------------------------- #
def read_sales(sales_rows, phone_attrib, email_attrib):
    """Lê a aba "Compradores". Colunas:
    Data, Hora, Status, Produto, Tipo, Comprador(a), E-mail, Telefone, País,
    Moeda compra, Valor compra (orig.), Valor bruto (BRL), Fat. líquido
    (USD), Fat. líquido (BRL), Método pagto, Parcelas, Origem, Origem UTM
    (bruto), Detalhe UTM.
    "fat" (faturamento líquido) <- "Fat. líquido (USD)" — NATIVO EM USD
    (decisão do cliente: usar o líquido em dólar em vez do bruto em BRL); a
    conversão pro toggle de moeda acontece no app.js (mesmo padrão do gasto
    do Meta Ads). Sem confirmação dos valores exatos de "Status" p/
    cancelamento/reembolso: conta TODA linha não vazia como venda
    (comportamento conservador do template original).
    Esta dash considera SÓ as vendas do MBA: linhas cuja coluna "Produto" não
    contém "mba" são ignoradas (decisão do cliente — ver is_mba_sale)."""
    header = sales_rows[0] if sales_rows else []
    idx = header_index(
        header,
        {"date": ["data"], "status": ["status"], "name": ["comprador"],
         "email": ["e-mail", "email"], "phone": ["telefone"], "produto": ["produto"],
         "faturamento": ["fat. liquido (usd)", "fat liquido (usd)"]},
        {"date": 0, "status": 2, "produto": 3, "name": 5, "email": 6, "phone": 7, "faturamento": 12},
    )
    NO_ATTRIB = {"src": "org", "camp": "(sem campanha)", "adset": "(sem conjunto)",
                 "ad": "(sem anúncio)", "d": None}
    out = []
    matched = 0
    total = 0
    skipped_produto = 0
    unmatched_log = []
    for row in sales_rows[1:]:
        if not any((c or "").strip() for c in row):
            continue
        if not is_mba_sale(cell(row, idx["produto"])):
            skipped_produto += 1
            continue
        total += 1
        phone = canon_phone(cell(row, idx["phone"]))
        email = norm_email(cell(row, idx["email"]))
        attrib = attrib_for(phone_attrib, email_attrib, phone, email, NO_ATTRIB)
        if attrib is not NO_ATTRIB:
            matched += 1
        else:
            unmatched_log.append((cell(row, idx["date"]), first_last_initial(cell(row, idx["name"])), phone))
        out.append({
            "d": parse_date(cell(row, idx["date"])) or attrib["d"],
            "src": attrib["src"], "camp": attrib["camp"], "adset": attrib["adset"], "ad": attrib["ad"],
            "vendas": 1,
            "fat": round(to_float(cell(row, idx["faturamento"])), 2),   # USD nativo
        })
    print(f"  vendas atribuídas a anúncio: {matched}/{total} (cruzamento telefone OU e-mail, Compradores × Central de Leads)",
          file=sys.stderr)
    print(f"  vendas ignoradas por Produto != MBA: {skipped_produto}", file=sys.stderr)
    if unmatched_log:
        print(f"  {len(unmatched_log)} compra(s) SEM anúncio de origem (entram nos totais como \"(sem campanha)\"):",
              file=sys.stderr)
        for d, nm, phone in unmatched_log:
            print(f"    - {d or '?'}  {nm}  tel …{phone[-4:] if len(phone) >= 4 else phone}", file=sys.stderr)
    return out


# --------------------------------------------------------------------------- #
# Meta Ads -> registros diários por anúncio
# --------------------------------------------------------------------------- #
def read_meta(meta_rows):
    """Lê a planilha "Meta Ads" (aba única). Colunas:
    Day, Campaign Name, Ad Set Name, Ad Name, Amount Spent, Impressions,
    Link Clicks, Landing Page Views, Leads, 3-Second Video Views, Creative
    Instagram Permalink.
    "Amount Spent" é NATIVO EM USD — gravado como está em meta[].sp; a
    conversão pro toggle de moeda acontece no app.js (client-side).
    Sem colunas de "Adds to Cart"/Checkout nesta conta — chk fica sempre 0
    ("-" no front, sem proxy de checkout disponível)."""
    header = meta_rows[0] if meta_rows else []
    idx = header_index(
        header,
        {"day": ["day"], "campaign": ["campaign name"], "adset": ["ad set name"],
         "ad": ["ad name"], "spent": ["amount spent"], "impr": ["impressions"],
         "clicks": ["link clicks"], "leads": ["leads"], "pv": ["landing page views"],
         "link": ["creative instagram permalink", "instagram permalink", "permalink"]},
        {"day": 0, "campaign": 1, "adset": 2, "ad": 3, "spent": 4, "impr": 5,
         "clicks": 6, "pv": 7, "leads": 8, "link": 10},
    )
    meta = []
    ad_links = {}
    for row in meta_rows[1:]:
        if not any((c or "").strip() for c in row):
            continue
        ad = cell(row, idx["ad"]) or "(sem anúncio)"
        link = cell(row, idx["link"])
        if link and ad not in ad_links:
            ad_links[ad] = link
        meta.append({
            "d": parse_date(cell(row, idx["day"])),
            "camp": cell(row, idx["campaign"]) or "(sem campanha)",
            "adset": cell(row, idx["adset"]) or "(sem conjunto)",
            "ad": ad,
            "sp": round(to_float(cell(row, idx["spent"])), 4),   # USD nativo
            "im": to_float(cell(row, idx["impr"])),
            "cl": to_float(cell(row, idx["clicks"])),
            "pv": to_float(cell(row, idx["pv"])),
            "ck": 0.0,   # sem proxy de checkout nesta conta
            "ml": to_float(cell(row, idx["leads"])),
        })
    return meta, ad_links


# --------------------------------------------------------------------------- #
# Processamento -> registros brutos
# --------------------------------------------------------------------------- #
def process(leads_rows, meta_rows, agendamentos_rows, sales_rows):
    leads, phone_attrib, email_attrib = read_leads(leads_rows)
    meta, ad_links = read_meta(meta_rows)
    agendamentos = read_agendamentos(agendamentos_rows, phone_attrib, email_attrib) if agendamentos_rows else []
    sales = read_sales(sales_rows, phone_attrib, email_attrib) if sales_rows else []

    usd_brl_rate = fetch_usd_brl_rate()

    dates = sorted({d for d in (
        [l["d"] for l in leads if l["d"]] + [m["d"] for m in meta if m["d"]] +
        [s["d"] for s in sales if s["d"]] + [a["d"] for a in agendamentos if a["d"]]
    )})
    now_brt = datetime.now(BRT)
    return {
        "build": {
            "generated_at_brt": now_brt.strftime("%d/%m/%Y %H:%M"),
            "build_id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            "today": now_brt.strftime("%Y-%m-%d"),
            "date_min": dates[0] if dates else None,
            "date_max": dates[-1] if dates else None,
            "tax_factor": TAX_FACTOR,
            "usd_brl_rate": usd_brl_rate,   # gasto (meta[].sp) é USD nativo; app.js converte ao vivo
            "sample_min_spend": SAMPLE_MIN_SPEND,
            "sample_min_mqls": SAMPLE_MIN_MQLS,
            "top_ads_n": TOP_ADS_N,
            "meta_cpmql": META_CPMQL,
            "meta_cac": META_CAC,
            "volume_min_amostral": VOLUME_MIN_AMOSTRAL,
            "n_dias_corte": N_DIAS_CORTE,
            "leads_lp_total": 0,   # sem fonte legada neste cliente
        },
        "leads": leads,
        "meta": meta,
        "sales": sales,
        "agendamentos": agendamentos,
        "ad_links": ad_links,
        "briefings": {},
    }


# --------------------------------------------------------------------------- #
# Insights de Tráfego (aba Relatório)
# --------------------------------------------------------------------------- #
def load_briefings(path: str) -> dict:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, OSError):
        return {}


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def render(data, template_path):
    base = os.path.dirname(os.path.abspath(template_path))

    def readf(name):
        with open(os.path.join(base, name), "r", encoding="utf-8") as f:
            return f.read()

    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    styles = readf("identidade-visual.css") + "\n" + readf("estilos.css")
    tpl = tpl.replace("__STYLES__", styles)
    tpl = tpl.replace("__APP_JS__", readf("app.js"))
    tpl = tpl.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    tpl = tpl.replace("__BUILD_ID__", data["build"]["build_id"])
    tpl = tpl.replace("__GENERATED_BRT__", data["build"]["generated_at_brt"])
    return tpl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leads-file", help="CSV local da aba \"Central de Leads\" (fonte principal)")
    ap.add_argument("--meta-file", help="CSV local da planilha Meta Ads")
    ap.add_argument("--agendamentos-file", help="CSV local da aba \"Agendamentos\" (Calendly)")
    ap.add_argument("--sales-file", help="CSV local da aba \"Compradores\"")
    ap.add_argument("--template", default="build/template.html")
    ap.add_argument("--out", default="dist/index.html")
    args = ap.parse_args()

    leads_rows = load_rows(EXPORT_URL.format(sid=SPREADSHEET_ID_LEADS, gid=GID_LEADS), args.leads_file)
    meta_rows = load_rows(EXPORT_URL.format(sid=SPREADSHEET_ID_META, gid=GID_META), args.meta_file)
    agendamentos_rows = load_rows(EXPORT_URL.format(sid=SPREADSHEET_ID_LEADS, gid=GID_AGENDAMENTOS), args.agendamentos_file)
    sales_rows = load_rows(EXPORT_URL.format(sid=SPREADSHEET_ID_LEADS, gid=GID_SALES), args.sales_file)

    data = process(leads_rows, meta_rows, agendamentos_rows, sales_rows)

    briefings_path = os.path.join(os.path.dirname(os.path.abspath(args.template)), "relatorios.json")
    data["briefings"] = load_briefings(briefings_path)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render(data, args.template))

    b = data["build"]
    q = sum(l["q"] for l in data["leads"])
    la = sum(l["a"] for l in data["leads"])
    vd = sum(s["vendas"] for s in data["sales"])
    fat = sum(s["fat"] for s in data["sales"])
    ag = sum(a["agendamentos"] for a in data["agendamentos"])
    re_ = sum(a["reunioes"] for a in data["agendamentos"])
    print("== build ok ==", file=sys.stderr)
    print(f"  cliente   : {CLIENT_NAME} · {MAIN_PRODUCT}", file=sys.stderr)
    print(f"  periodo   : {b['date_min']} -> {b['date_max']}", file=sys.stderr)
    print(f"  leads     : {len(data['leads'])}  MQLs (qualificados): {q}  Leads A: {la}", file=sys.stderr)
    print(f"  agend.    : {ag}  reuniões realizadas: {re_}", file=sys.stderr)
    print(f"  vendas    : {vd}  faturamento: US$ {fat:,.2f}", file=sys.stderr)
    print(f"  meta      : {len(data['meta'])} linhas  usd_brl_rate: {b['usd_brl_rate']}", file=sys.stderr)
    print(f"  out       : {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
