# Dashboard de Captura de Leads · Thata Junqueira

Dashboard **100% na nuvem** do funil **Sessão Estratégica** ("Sala Secreta") de
**Thata Junqueira** que cruza a aba **Central de Leads** (leads do funil) com o
investimento de mídia paga (**Meta Ads**, planilha própria em USD), com a aba
**Agendamentos** (Calendly) e com a aba **Compradores**, calcula os **Leads
Qualificados (MQLs)**, os **Leads A** (subconjunto mais qualificado, métrica
paralela), **Agendamentos/Reuniões Realizadas** e as **Vendas/Faturamento**
atribuídos por anúncio, e é publicada no **GitHub Pages**. Reconstrói sozinha a
cada ~30 min, disparada pelo **cron-job.org** — sem depender de nenhum PC ligado.

**URL pública:** `https://metrics-odr.github.io/dash-thata-opn/`

---

## O que ela mostra

- **KPIs**: Gasto Total, Leads Totais, CPL, **MQLs** (Qualificação = "qualificado"), CPMQL, Tx-MQL, **Leads A** (Lead Scoring = "A"), CPL-A, Tx-A, A:MQL, Impressões, Cliques, CTR, CPC, CPM.
- **Evolução diária**: gasto/dia, leads × MQLs × Leads A/dia, CPL × CPMQL × CPL-A/dia.
- **Funil completo**: Impressões → Cliques → Leads → MQLs/Leads A → Agendamentos → Reuniões Realizadas → Vendas → Faturamento.
- **Qualificação & origem**: leads por Funil/Página, por origem (mídia paga vs. orgânico) e por plataforma.
- **Cruzamento por campanha**: gasto (mídia paga) × leads/MQLs/Leads A (Central de Leads) → CPL, CPMQL, CPL-A e taxas calculadas.
- **Tabela de leads qualificados** (e-mail e telefone **mascarados**, pois a página é pública).
- **Toggle de imposto da mídia paga** (não usado para este cliente — `TAX_FACTOR = 1.0`), **toggle de moeda BRL/USD** (o gasto do Meta Ads é nativo em dólar; a conversão usa uma cotação buscada no build, com fallback fixo) e **modo claro/escuro**.
- **Aba Relatório**: painel de metas editável + Top/Piores Anúncios + Insights de Tráfego (texto, preenchido manualmente ou por automação própria — ver `build/GUIA-RELATORIOS.md`).

## Critério de Lead Qualificado (MQL) e Lead A

- **MQL** = coluna **Qualificação** (aba "Central de Leads") == `"qualificado"`. Lógica em `build.py` → `is_mql`.
- **Lead A** = coluna **Lead Scoring** (mesma aba) == `"A"` — subconjunto MAIS qualificado que o MQL, métrica **paralela** (nunca substitui o MQL). Só começou a ser preenchida em 03/08/2026 em diante. Lógica em `build.py` → `is_lead_a`.

## Fontes de dados (somente leitura, 2 planilhas)

**Planilha "Meta Ads"** (`14yy7dhldcjPC2VzkXOfzGaS-kdqn5c3y3GWOm4vGj3c`), aba única (`gid=0`):
investimento/impressões/cliques/leads do gerenciador — `Amount Spent` é **nativo em USD**.

**Planilha "Central de Eventos - 2026"** (`1v3mc-Z3lUYzGGkyIIYdK9PL3M-O6cgIBTlUWHQDboGU`):

| Aba | gid | Uso |
|-----|-----|-----|
| Central de Leads (fonte principal) | `0` | fonte **principal** de leads — usada em todos os gráficos/cards/tabelas |
| Agendamentos (Calendly) | `1722749521` | cruzada por telefone OU e-mail com a Central de Leads → Agendamentos/Reuniões Realizadas por anúncio |
| Compradores | `86137300` | cruzada por telefone OU e-mail com a Central de Leads → Vendas/Faturamento por anúncio |

O build lê essas abas via **export CSV público** (`.../export?format=csv&gid=...`).
**Nada é escrito de volta** nas planilhas.

---

## Arquitetura

```
cron-job.org  ──(POST workflow_dispatch a cada 30 min)──▶  GitHub Actions
                                                              │
                          build/build.py  lê os CSVs ◀────────┘
                                 │  cruza dados + calcula MQLs/Leads A + câmbio USD→BRL
                                 ▼
                          dist/index.html  ──▶  deploy  ──▶  GitHub Pages (URL pública)
```

- `build/build.py` — baixa os CSVs das 2 planilhas, cruza os dados, busca a cotação USD/BRL, gera `dist/index.html`.
- `build/template.html` — layout/gráficos/tema (Chart.js via CDN).
- `.github/workflows/deploy.yml` — roda o build e publica no Pages.

**Cache-bust:** a página usa `Cache-Control: no-cache`, mostra o horário do último
build, tem botão **Atualizar** e se recarrega sozinha (`?t=timestamp`) ~30 min após
aberta — sempre pegando a versão mais nova.

## Rodar localmente (opcional)

```bash
python build/build.py --out dist/index.html            # busca os CSVs ao vivo (2 planilhas)
# ou, com arquivos locais para teste:
python build/build.py --leads-file leads.csv --meta-file meta.csv \
  --agendamentos-file agendamentos.csv --sales-file compradores.csv --out dist/index.html
```

---

## Ativação (uma vez) e cron-job.org

O disparo por `workflow_dispatch` só funciona quando o workflow está na branch
**`main`**. Veja **`SETUP-CRON.md`** para o passo a passo e os valores exatos
(URL, headers e body, com o token a preencher) a colar no cron-job.org.

> ⚠️ **Segurança:** nunca comite tokens no repositório. Gere um token
> *fine-grained*, só com **Actions: read/write** neste repositório, e use-o
> apenas no cron-job.org (ou em GitHub Secrets, se aplicável).

## Como usar este template para um novo cliente

Veja o **CHECKLIST DE NOVO CLIENTE** no topo de `CLAUDE.md` (ou `AGENTS.md`) e
o passo a passo completo em `GUIA-REPLICACAO.md`.
