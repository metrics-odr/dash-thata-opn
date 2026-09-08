# CLAUDE.md — Contexto do projeto (TEMPLATE High Ticket)

> Este arquivo é lido automaticamente pelo Claude Code ao abrir o repositório.
> Ele carrega TODO o contexto necessário para continuar o trabalho sem depender
> de mensagens anteriores. Mantenha-o atualizado.
>
> **Este é um TEMPLATE limpo.** Todos os valores específicos do cliente estão
> marcados como `<<PREENCHER: descrição>>`. Siga o CHECKLIST abaixo para
> configurar um cliente novo.

---

## ✅ CHECKLIST DE NOVO CLIENTE (fazer em ordem)

Preencha cada `<<PREENCHER: …>>` do repositório. Ordem sugerida:

1. **`build/build.py` — constantes do topo:**
   - `SPREADSHEET_ID_META` / `SPREADSHEET_ID_LEADS` — IDs das (até 2) planilhas do cliente.
   - `GID_META`, `GID_LEADS`, `GID_AGENDAMENTOS`, `GID_SALES` — gids das abas usadas.
   - `CLIENT_NAME`, `MAIN_PRODUCT` — nome do cliente e da oferta principal.
   - `MAIN_PRODUCT_PREFIX` — prefixo comum às campanhas do cliente (documental — não filtra nada).
   - `TAX_FACTOR` — fator de imposto/taxa da mídia (1.0 = sem imposto).
2. **`build/build.py` — critério de MQL/Lead A:** ajuste `is_mql()`/`is_lead_a()` e os
   aliases das colunas de qualificação em `read_leads()` ao critério e ao cabeçalho
   real da aba de leads do cliente.
3. **`build/app.js`:** revisar os rótulos fixos de UI que citam o critério de MQL
   ("MQLs (...)") e o agrupamento de dimensão (bucket/prof) — o critério de
   `build.py` não propaga sozinho para esses textos.
4. **`build/template.html`:** preencher `<title>` e o logo (`logo-main`/`logo-sub`)
   com o nome/slogan do cliente. (Opcional: trocar o favicon base64.)
5. **`build/identidade-visual.css`:** ajustar cores se o cliente tiver identidade
   própria (opcional — o default funciona).
6. **`README.md` / `SETUP-CRON.md` / este `CLAUDE.md` / `AGENTS.md`:** owner/repo
   do GitHub, URL do GitHub Pages, nome do cliente, planilha/gids.
7. **`build/GUIA-RELATORIOS.md`:** preencher o "Contexto do funil" (cliente,
   oferta, critério de MQL).
8. **GitHub Pages + Actions:** confirmar que `build/` + `.github/workflows/deploy.yml`
   estão na `main` (ativa `workflow_dispatch`); rodar o workflow uma vez.
9. **cron-job.org:** seguir `SETUP-CRON.md` — token fine-grained novo (Actions:
   read/write, só neste repo), nunca reaproveitar um token exposto em chat.
10. **Insights de Tráfego (opcional):** `build/relatorios.json` e
    `build/relatorios_dados.json` começam vazios (`{}`). Para ativar os Insights:
    - deixar a Routine do Actions `briefing.yml` rodar (gera `relatorios_dados.json`
      com os números), e
    - criar a **Routine do Claude** (`create_trigger` apontando para este repo)
      que lê os números + os 2 guias e escreve `relatorios.json` na `main`
      (ver "Briefing automático" abaixo). **Não vem pronta** — precisa ser
      recriada por cliente.
11. **Testar local** com CSVs de amostra antes de publicar (3 páginas, tema
    claro/escuro, multi-seleção).

> **Fora do escopo deste template:** não há Cloudflare Worker nem chamada paga à
> API da Anthropic no pipeline. A automação de Insights é feita por Routine
> agendada do Claude Code (item 10). Se o cliente precisar de outra camada, é
> desenvolvimento novo.

---

## O que é

Dashboard de **Captura de Leads** — um app de BI estático (HTML/CSS/JS
puro + Chart.js via CDN) publicado no **GitHub Pages**, que cruza a lista de
**Leads** com o gerenciador de mídia paga e se atualiza sozinho a cada ~30 min
(build 100% na nuvem via GitHub Actions, disparado externamente pelo cron-job.org).

- **URL pública:** `https://metrics-odr.github.io/dash-thata-opn/`
- **Somente leitura** das planilhas. Nunca escrever de volta.

> **Cliente atual (Thata Junqueira) foge do template padrão de 1 planilha/4 abas:**
> são **DUAS** planilhas Google Sheets distintas (ver abaixo). Se você for
> replicar este repo para outro cliente que volte ao padrão de 1 planilha,
> reveja `build/build.py` (`SPREADSHEET_ID_META`/`SPREADSHEET_ID_LEADS` viram
> 1 só) e este documento.

## Fontes de dados (Google Sheets) — Thata Junqueira

**Planilha "Meta Ads"** — `SPREADSHEET_ID_META = "14yy7dhldcjPC2VzkXOfzGaS-kdqn5c3y3GWOm4vGj3c"`, aba única `gid=0`:
`Day` · `Campaign Name` · `Ad Set Name` · `Ad Name` · `Amount Spent` (**USD nativo**) · `Impressions` · `Link Clicks` · `Landing Page Views` · `Leads` · `3-Second Video Views` · `Video Views de 50%` · `Ad Status` · `Creative Instagram Permalink`.
`3-Second Video Views`/`Video Views de 50%` alimentam **HR** (Hook Rate) e **BR**
(Body Rate) na tabela Top Anúncios (calculados em `app.js::derive`, nunca no
Python). `Ad Status` (`ACTIVE`/`PAUSED`) vira o badge **Ativo/Pausado** na
tabela "Anúncios" (Captura Meta Ads) — mapa `ad_status` em `build.py::read_meta`,
igual ao `ad_links` do permalink (usado no ícone "Prévia" 👁 da mesma tabela).

**Planilha "Central de Eventos - 2026"** — `SPREADSHEET_ID_LEADS = "1v3mc-Z3lUYzGGkyIIYdK9PL3M-O6cgIBTlUWHQDboGU"`:

| Aba | gid | Colunas usadas |
|-----|-----|----------------|
| **Central de Leads** (fonte principal) | `0` | `Data` · `Nome` · `Email` · `Telefone` · `Funil` · `Página` · `Qualificação` · `Lead Scoring` · `UTM Source` · `UTM Medium` · `UTM Campaign` · `UTM Content` · `UTM Term` · `UTM id` · `Agendamento` |
| **Agendamentos** (Calendly) | `1722749521` | `ID Calendly` · `Data` · `Dia da Semana` · `Hora Início` · `Hora Fim` · `Consultora` · `Tipo de Evento` · `Convidado` · `Email` · `Telefone/WhatsApp` · `Status` · `Cancelado Por` · `Motivo do Cancelamento` · `Plataforma` · `Link da Reunião` · `Criado em` · `Funil Nota` |
| **Compradores** | `86137300` | `Data` · `Hora` · `Status` · `Produto` · `Tipo` · `Comprador(a)` · `E-mail` · `Telefone` · `País` · `Moeda compra` · `Valor compra (orig.)` · `Valor bruto (BRL)` · `Fat. líquido (USD)` · `Fat. líquido (BRL)` · `Método pagto` · `Parcelas` · `Origem` · `Origem UTM (bruto)` · `Detalhe UTM` |

URL de export CSV: `https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=<GID>`

### Regra de Lead Qualificado (MQL) e Lead A
- **MQL** = coluna `Qualificação` == `"qualificado"`. Lógica em `build.py` → `is_mql`.
- **Lead A** = coluna `Lead Scoring` == `"A"` — subconjunto MAIS qualificado que o
  MQL, métrica **paralela** (nunca substitui). Só preenchida a partir de
  03/08/2026. Lógica em `build.py` → `is_lead_a`. Aparece lado a lado do MQL em
  todo o front (funil, KPIs, tabela diária, hierarquia, Top Anúncios), com a
  proporção **A:MQL** (Lead A / MQL).

Sem coluna de especialidade/profissão nesta planilha: os gráficos "Leads por
Funil"/"Leads por Página" (`app.js`, `renderGeralCore`) usam as colunas `Funil`
e `Página` da Central de Leads como dimensão (coloridas verde/cinza pelo MQL).

`UTM Campaign` == `Campaign Name` do Meta Ads; `UTM Content` == `Ad Name`;
`UTM Medium` é usado como aproximação de "Conjunto" (decisão do cliente — não
existe Ad Set Name nesta planilha).

### Agendamentos & Vendas/Faturamento (cruzamento por telefone OU e-mail)
Diferente do template padrão (só telefone), este cliente cruza por **telefone
OU e-mail** — `build.py` → `read_leads()` monta `phone_attrib`/`email_attrib`
(1ª linha de cada contato define camp/adset/ad); `read_agendamentos()` e
`read_sales()` tentam telefone (`canon_phone`) primeiro e caem para e-mail
normalizado quando não bate. Cada agendamento/venda vira um registro próprio
(não agregado) em `DATA.agendamentos[]`/`DATA.sales[]`, com a **data real do
evento** (nunca a data do lead). No navegador, `agdActive()`/`salesActive()`
(`app.js`) filtram pela mesma data ativa que `leadsActive()`/`metaActive()`, e
os quatro arrays se propagam juntos em `buildAgg`/`daily`/`totals`.

**TODO agendamento/venda entra na dash**; quando não casa por telefone nem
e-mail, ainda conta nos totais/Visão Geral, porém como `(sem campanha)` /
`src="org"` — some apenas da quebra por campanha do Meta. `read_agendamentos`/
`read_sales` logam no build quantos ficaram sem anúncio de origem.

Faturamento (`fat`) vem de `Fat. líquido (USD)` — **nativo em USD** (decisão do
cliente: usar o líquido em dólar em vez do bruto em BRL; ver comentário em
`build.py::read_sales`), mesmo padrão do gasto do Meta Ads. Não há mais campo
`receita`/card "Receita" separado (removido — era redundante com Faturamento).

**Esta dash considera SÓ as vendas do MBA:** `read_sales()` filtra a aba
Compradores pela coluna `Produto` — linhas cujo `Produto` não contém "mba"
(case/acento-insensitive, `is_mba_sale()`) são descartadas antes de entrar em
`DATA.sales[]` (não contam em vendas, faturamento, CAC, ROAS nem nos
Top/Piores Anúncios). Outras ofertas da mesma planilha (ex.: Sessão
Estratégica, Sala Secreta) ficam de fora. O build loga quantas linhas foram
ignoradas por produto (`vendas ignoradas por Produto != MBA` em stderr).
"Status" de Agendamentos/Compradores não teve os valores exatos confirmados —
ver decisões documentadas no topo de `build.py`.

### Imposto da mídia paga
`TAX_FACTOR = 1.13806` em `build.py` — este cliente tem imposto de mídia de
13,806%. O toggle "Imposto Meta" (switch on/off, `#taxToggle`, `app.js`)
multiplica o gasto do Meta Ads (e tudo que deriva dele — CPL, CPMQL, CAC,
ROAS etc., via `taxf()`) por `TAX_FACTOR` quando ligado; desligado, usa o
gasto nativo sem imposto.

### Conversão de moeda (USD → BRL)
O gasto do Meta Ads e o Faturamento (`fat`, de `Fat. líquido (USD)`) são ambos
**nativos em USD**. `build.py` busca a cotação USD/BRL 1x por build
(`fetch_usd_brl_rate()`, APIs públicas sem chave, com fallback fixo 5.30 se
todas falharem — nunca quebra o build) e grava em `DATA.build.usd_brl_rate`. O
seletor de moeda na topbar (`#currencyToggle`, dois botões USD / BRL com
bandeira em SVG inline — não emoji, que não renderiza como bandeira no
Windows/Chrome — `.cur-flag` em `template.html`/`estilos.css`) —
`STATE.currency` em `app.js`) multiplica (`BRL`) ou mantém (`USD`) os valores
nativos ao vivo no navegador — nunca no Python — via `curF()` (mesma função
para gasto e fat, já que ambos partem de USD; CAC/ROAS/Ticket herdam a
conversão por dependerem de gasto/fat). A cotação vigente (dinâmica, vinda de
`DATA.build.usd_brl_rate`) aparece como texto abaixo do seletor (`#fxRate` em
`template.html`, preenchido em `app.js`).

### Convenções de campanha (do cliente)
Campanhas usam dois prefixos — `OPN` e `OPNF` (`MAIN_PRODUCT_PREFIX = "OPN"` é
só documental/label) — tratados como **1 cliente só**, sem filtrar por
prefixo em lugar nenhum do código (mesmo comportamento do template padrão,
que também não filtra por `MAIN_PRODUCT_PREFIX`).

## Arquitetura / arquivos

```
build/build.py            # lê os CSVs de 2 planilhas (read-only), emite REGISTROS BRUTOS (leads[]/meta[]/sales[]/agendamentos[]/ad_links) + usd_brl_rate; render() COSTURA os 4 arquivos abaixo
build/template.html       # esqueleto HTML. Placeholders __STYLES__, __APP_JS__, __DATA_JSON__, __BUILD_ID__, __GENERATED_BRT__
build/identidade-visual.css  # TODAS as cores (tema claro=padrão / escuro). Mexa AQUI p/ trocar só cor
build/estilos.css         # layout/componentes (sidebar, topbar, period-picker, funil, tabelas, gráficos, aba Relatório)
build/app.js              # lógica + renderização (KPIs, funil, tabelas, filtro cruzado, period-picker, heatmap, Relatório)
build/relatorios.json     # Insights de Tráfego por período (aba Relatório) — VERSIONADO; lido no build, sem API. Vazio no template ({}).
build/relatorios_dados.json      # números brutos por período (insumo p/ a Routine escrever relatorios.json) — não lido pelo site. Vazio no template ({}).
build/relatorio_lib.py           # datas/agregação compartilhadas (gerar_relatorios.py + coletar_dados_relatorio.py)
build/coletar_dados_relatorio.py # gera relatorios_dados.json (só números, sem texto) — roda no briefing.yml, 1x/dia
build/gerar_relatorios.py        # gera relatorios.json determinístico (sem IA) — fallback MANUAL, não roda mais sozinho
build/GUIA-RELATORIOS.md            # formato/estrutura dos Insights da aba Relatório (os 7 blocos) — preencher o contexto do funil
build/GUIA-INTERPRETACAO-METRICAS.md # regras de diagnóstico por métrica (High Ticket) — leitura obrigatória p/ redigir
.github/workflows/deploy.yml    # roda build.py e publica no Pages (workflow_dispatch + schedule + push)
.github/workflows/briefing.yml  # roda coletar_dados_relatorio.py e commita relatorios_dados.json na main (cron 1x/dia)
dist/index.html           # saída gerada (gitignored; o Actions reconstrói)
GUIA-REPLICACAO.md        # como replicar este modelo para outros relatórios/clientes
SETUP-CRON.md             # valores exatos do cron-job.org (com marcadores a preencher)
```

### Aba Relatório
Terceira página (sidebar, entre a de mídia paga e o rodapé). **Espelha a Visão
Geral** (mesmo funil/KPIs/gráficos/tabela diária, via `renderGeralCore(REL_IDS)`)
e, abaixo, acrescenta 3 blocos novos + um painel de metas editável:
- **Metas & parâmetros (painel editável)** — no topo da aba: Meta CPMQL, Meta CAC, Volume
  mínimo amostral (MQLs), N dias p/ corte. Persiste em `localStorage['dm_metas']`, default de
  `build.py` (`META_CPMQL`/`META_CAC`=None → "não definida"; `VOLUME_MIN_AMOSTRAL`/`N_DIAS_CORTE`).
  Editar recolore **CPMQL/CAC** nas tabelas de anúncio (verde ≤ meta · amarelo até +30% ·
  vermelho acima) e reavalia o **Status** do anúncio (ver abaixo), **tudo ao vivo**
  (`METAS` + `renderRelAds()` em `app.js`).
- **Top Anúncios** — 22 colunas (Anúncio · Status · Campanha · Conjunto · Gasto · HR · BR · CTR ·
  Leads · CPL · MQLs · Tx‑MQL · CPMQL · Leads A · Tx‑A · A:MQL · CPL‑A · ConvAGD ·
  Vendas · CAC · Faturamento · ROAS · **Link**). Anúncio e Link ficam **sticky**
  (colunas com `stk:'l'`/`stk:'r'` em `renderTable`/`app.js`: `position:sticky` numa
  única `<table>`, offset calculado em JS somando a largura das colunas sticky
  anteriores — mesmo mecanismo usado nas 3 tabelas hierárquicas de Campanha/Conjunto/
  Anúncio, ver abaixo). **HR** (Hook Rate = 3‑Second Video Views/Impressions) e
  **BR** (Body Rate = Video Views 50%/Impressions) substituíram CPM/Impressões.
  Ranking pelo **resultado mais profundo disponível** (Venda→MQL), amostra relevante primeiro.
  **Status** (`adStatusState()` em `app.js`, vs. metas de CPMQL/CAC do painel): **Escalar**
  (verde, dentro da meta) · **Manter** (azul, até +30% da meta) · **Cortar** (vermelho, acima
  do teto) · **Observar** (amarelo, sem amostra suficiente ainda). Limiares em `build.py`:
  `SAMPLE_MIN_SPEND`, `SAMPLE_MIN_MQLS`, `TOP_ADS_N`.
- **Insights de Tráfego** — texto por período redigido pelo **Claude** (linguagem de
  gestor de tráfego), lido de `build/relatorios.json` (sem API no build/navegador —
  o site só exibe o texto já pronto). Formato em **4 quadrantes** por período. Cada
  período compara com o período anterior **correto para aquela janela** (regra em
  `relatorio_lib.previous_period`). Chaves de período fixas
  (`hoje/ontem/3d/7d/14d/30d/mes/mespass/todo`), tags `Escalar/Otimizar/Cortar/Observar`.
  Toda a aritmética é pré-calculada em `build/relatorios_dados.json` — a Routine só
  interpreta, nunca recalcula. Regras completas em `build/GUIA-RELATORIOS.md` +
  `build/GUIA-INTERPRETACAO-METRICAS.md`. `app.js` ainda reconhece o formato antigo
  (`{"html": "…"}`) como fallback.

### Briefing automático do gestor (Routine do Claude, sem chamada à API Anthropic)
`build/relatorios.json` pode ser escrito 1×/dia por uma **Routine do Claude**
(Claude Code Remote — mesma infraestrutura de sessão/agente deste repo, agendada;
não é chamada paga à API). Fluxo em 2 etapas, porque o ambiente da Routine não
alcança `docs.google.com` (só o runner do GitHub Actions alcança):
1. `build/coletar_dados_relatorio.py` (GitHub Actions, `.github/workflows/briefing.yml`,
   1×/dia) agrega **só números** em `build/relatorios_dados.json` e commita na `main`.
2. A Routine do Claude lê esse JSON + `build/GUIA-RELATORIOS.md` +
   `build/GUIA-INTERPRETACAO-METRICAS.md`, redige `build/relatorios.json` e faz
   commit/push direto na `main`, disparando o `deploy.yml`. **Precisa ser criada
   por cliente** (`create_trigger` apontando para o repo novo) — não vem pronta.

`build/gerar_relatorios.py` (gerador determinístico, sem IA) continua no repo só
como **fallback manual**. Limitação conhecida: usa os defaults de `build.py`
(`META_CPMQL`/`META_CAC`/`VOLUME_MIN_AMOSTRAL`/`N_DIAS_CORTE`), não o que o gestor
editou no painel (fica em `localStorage`).

Funil completo: `Impressões → Cliques → Leads → MQLs → Agendamentos → Vendas →
Faturamento`. Enquanto só houver mídia paga × Leads, o funil vai até MQL;
Agendamentos/Vendas/Fat aparecem "-" até chegar a lista do comercial. Reuniões
Realizadas não tem card/coluna na UI (removido por não ter fonte de dados
neste cliente), mas a lógica de tier em `adQuality()` (`app.js`) continua
existindo internamente para o ranking de Top/Piores Anúncios, caso essa fonte
apareça no futuro.

### Link do criativo (aba de mídia paga)
`build.py` lê uma coluna opcional de permalink do criativo na aba de mídia →
mapa `ad_links` (anúncio → 1 permalink). Usado no "Link" das tabelas Top/Piores.
Sem a coluna, o link vira "—".

> **Layout modular:** o front-end é separado em `identidade-visual.css` + `estilos.css`
> + `app.js`, costurados por `render()` nos placeholders `__STYLES__`/`__APP_JS__`.
> Página 1 usa **funil vertical de leads** + KPIs secundários. Topbar tem
> **seletor de período em calendário** (default "Este mês"). **Heatmap** = cor FIXA
> por métrica (só opacidade varia): **Gasto=vermelho · Leads=azul · MQLs=ciano ·
> Vendas=verde · ROAS=amarelo · Leads A=laranja · CPL‑A=cinza claro**
> (`--heat-gasto/leads/mqls/vendas/roas/la/cpla`).

O `build.py` **não agrega**: exporta as linhas cruas e TODA a lógica (filtros de
data, filtro cruzado, KPIs, tabelas, gráficos, heatmap, imposto) roda no navegador.

## Rodar/testar local

```bash
python build/build.py --leads-file leads.csv --meta-file meta.csv \
  --agendamentos-file agendamentos.csv --sales-file compradores.csv --out dist/index.html
# (o sandbox do agente NÃO alcança docs.google.com; use CSVs locais para testar.
#  O runner do GitHub Actions tem internet e busca os CSVs das 2 planilhas ao vivo,
#  além da cotação USD/BRL.)
```

## Especificação funcional (resumo)

Três **páginas separadas** (sidebar; rótulos exibidos: **Visão Geral** ·
**Meta Ads** · **Insights de IA** — ids internos `geral`/`meta`/`rel` continuam
os mesmos em `app.js`/`template.html`):
1. **Visão Geral** (id `geral`) — funil vertical (Gasto → Impressões → Cliques → Leads →
   MQLs → Vendas/Faturamento) + KPIs secundários; gráfico combinado diário +
   tabela diária com heatmap (todos os leads; heatmap também em Leads A/CPL‑A/Vendas/ROAS,
   ver `HEAT_HUE` em `app.js`); barras por origem/faixa/plataforma/profissão.
2. **Meta Ads** (id `meta`) — funil em etapas; combinado diário; barras por utm_content;
   tabela diária com heatmap (só mídia paga); 3 tabelas hierárquicas Campanha →
   Conjunto → Anúncio, cada uma com gráfico de linha embaixo. A tabela "Anúncios"
   tem 2 colunas extras (`adExtraCols`): **Status** (badge Ativo/Pausado, coluna
   "Ad Status" do Meta Ads) e **Prévia** (ícone 👁, sticky à direita, linka `ad_links`).
3. **Insights de IA** (id `rel`) — espelha a Visão Geral + painel de Metas editável +
   Top Anúncios (22 colunas + Status) + Insights de Tráfego. Ver `build/GUIA-RELATORIOS.md`.

**Ordem das colunas nas tabelas:** `Data · Dia · Gasto · CPM · CTR · CR · ConvLP ·
Leads · CPL · Tx‑MQL · MQLs · CPMQL · Leads A · Tx‑A · A:MQL · CPL‑A · ConvAGD ·
Vendas · CAC · Fat. · ROAS` (ver `DAILY_COLS`/`hcols` em `app.js`). **ConvAGD**
(= Vendas / Agendamentos) substituiu o antigo "ConvMQL" — nome e fórmula estavam
incorretos (a coluna nunca dividiu por MQLs). Não há mais colunas de
Checkouts/VisCHK/Agend./Reun. Realiz./Receita — removidas por não terem fonte
de dados útil neste cliente (Meta Ads sem "Adds to Cart"; Receita era
redundante com Faturamento).

**Regras obrigatórias das tabelas** (ver `GUIA-REPLICACAO.md`): cabeçalho sticky;
ordenação tri‑state; colunas redimensionáveis (persist localStorage); linha
"Total Geral" fixa; dimensão nunca truncada; seleção com toggle + Ctrl multi;
filtro cruzado bidirecional; tabela diária com último dia no topo; heatmap de cor
fixa por métrica.

## Lacunas de dados (comuns até o cliente enviar mais fontes)
- **Agendamentos** → tem card na UI, mas Reuniões Realizadas (comparecimento) não
  tem fonte neste cliente e foi removida da UI (ver "Funil completo" acima).
- **Page Views, CR, CPV, ConvLP** → precisam de uma fonte de page views.
- Enquanto não vierem, essas métricas aparecem como "-".

## Publicação — problemas conhecidos
1. **Push:** se a integração GitHub da sessão for somente‑leitura (403), o caminho
   é `git push` direto para `github.com` com o **PAT do usuário**. Nunca gravar o
   token no `.git/config` (usar URL efêmera `https://x-access-token:<TOKEN>@github.com/...`).
2. **cron-job.org só funciona na `main`:** `workflow_dispatch` só existe na branch
   padrão. Levar `build/` + `.github/workflows/deploy.yml` para a `main`.
3. **Pages liga sozinho:** `actions/configure-pages@v5` com `enablement: true`
   (precisa `permissions: pages: write, id-token: write`).
4. **Proxy do sandbox:** o ambiente do agente costuma NÃO alcançar `docs.google.com`,
   `*.github.io` nem a API REST de Actions/Pages — mas o runner do Actions alcança tudo.
5. **Token exposto:** se um token foi colado no chat, **revogar e gerar um novo**.

## Branch / git
- Desenvolvimento na branch designada da sessão; manter sincronizada com `main`.
