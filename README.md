# Relationship Hypergraph System (RHPG)

Sistema de análise de performance de colaboradores usando teoria de grafos e hipergrafos. Classifica trabalhadores como **alta**, **neutra** ou **baixa** performance correlacionando métricas individuais com a qualidade do trabalho em grupo.

---

## Conceito

A ideia central é que a performance de uma pessoa não pode ser medida de forma isolada — ela precisa ser avaliada em relação ao impacto que essa pessoa causa nos grupos em que participa.

O sistema usa dois tipos de estrutura:

- **Vértices (Workers):** cada colaborador com suas métricas individuais (proficiência, KPIs)
- **Hipervértices (Groups):** cada grupo/projeto como uma hiperaresta que conecta múltiplos colaboradores

A classificação final combina 6 métricas:

| Métrica | Peso padrão | O que mede |
|---|---|---|
| Performance individual | 30% | KPIs / OKRs do colaborador |
| Proficiência | 15% | Nível de habilidade na área |
| PageRank | 20% | Influência na rede (quem colabora com quem é valorizado) |
| Betweenness | 10% | Quem faz ponte entre grupos (broker organizacional) |
| Afinidade média | 10% | Quão integrado o colaborador está em seus grupos |
| Delta score médio | 15% | Quanto o grupo melhora/piora com essa pessoa |

---

## Estrutura do Projeto

```
Relationship-RHPG/
├── rhpg/
│   ├── models/           # Modelos de dados (Worker, Group, Relationship)
│   ├── storage/          # SQLite + SQLAlchemy (CRUD, seed)
│   ├── graph/            # NetworkX DiGraph + HyperNetX hypergraph
│   ├── algorithms/       # Delta score, afinidade, centralidade, classificador
│   ├── api/              # FastAPI (routers, dependências)
│   └── visualization/    # Pyvis, Plotly, HyperNetX render
├── tests/                # Pytest (algoritmos + API)
├── data/                 # rhpg.db (SQLite, gerado automaticamente)
├── requirements.txt
└── pyproject.toml
```

---

## Instalação

**Pré-requisito:** Python 3.11+

```bash
# 1. Crie e ative um ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# 2. Instale as dependências
pip install -r requirements.txt
```

---

## Como Rodar

### 1. Popular o banco com dados de exemplo

Gera 25 colaboradores, 5 grupos e ~70 relações sintéticas:

```bash
python -m rhpg.storage.seed
```

### 2. Subir a API

```bash
uvicorn rhpg.api.main:app --reload
```

A API estará disponível em `http://localhost:8000`.
Documentação interativa (Swagger): `http://localhost:8000/docs`

### 3. Rodar os testes

```bash
python -m pytest tests/ -v
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `RHPG_DATABASE_URL` | `sqlite:///./data/rhpg.db` | URL do banco de dados |

---

## API — Endpoints

### Workers `/workers`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/workers/` | Cadastrar novo colaborador |
| `GET` | `/workers/` | Listar todos os colaboradores |
| `GET` | `/workers/{id}` | Buscar colaborador por ID |
| `PUT` | `/workers/{id}` | Atualizar dados do colaborador |
| `DELETE` | `/workers/{id}` | Remover colaborador |

**Exemplo de cadastro:**
```json
POST /workers/
{
  "name": "Ana Paula",
  "role": "Tech Lead",
  "department": "Engineering",
  "proficiency_score": 0.9,
  "individual_performance_score": 0.85,
  "tenure_years": 4.5
}
```

---

### Groups `/groups`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/groups/` | Criar grupo/projeto |
| `GET` | `/groups/` | Listar todos os grupos |
| `GET` | `/groups/{id}` | Buscar grupo por ID |
| `POST` | `/groups/{id}/members/{worker_id}` | Adicionar colaborador ao grupo |
| `DELETE` | `/groups/{id}/members/{worker_id}` | Remover colaborador do grupo |
| `GET` | `/groups/{id}/quality` | Score de qualidade atual do grupo |

**Exemplo de criação:**
```json
POST /groups/
{
  "name": "Alpha Squad",
  "project_name": "Project Alpha",
  "department": "Engineering",
  "baseline_work_quality": 0.65,
  "project_outcome_score": 0.75,
  "member_ids": ["uuid-worker-1", "uuid-worker-2"]
}
```

---

### Relationships `/relationships`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/relationships/` | Registrar relação entre dois colaboradores |
| `GET` | `/relationships/` | Listar todas as relações |
| `GET` | `/relationships/{id}` | Buscar relação por ID |
| `DELETE` | `/relationships/{id}` | Remover relação |

**Tipos de relação (`rel_type`):**
- `COLLABORATION` — Colaboração direta em tarefas/projetos
- `MEMBERSHIP` — Participação em grupo (criado automaticamente)
- `CROSS_GROUP` — Interação entre membros de grupos diferentes

**Exemplo:**
```json
POST /relationships/
{
  "source_id": "uuid-worker-1",
  "target_id": "uuid-worker-2",
  "rel_type": "COLLABORATION",
  "interaction_frequency": 0.8,
  "collaboration_quality": 0.9
}
```

> O campo `weight` é calculado automaticamente: `interaction_frequency × collaboration_quality`

---

### Analysis `/analysis`

Este é o coração do sistema.

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/analysis/run` | Executar pipeline completo e persistir resultados |
| `GET` | `/analysis/results` | Retornar resultados sem re-executar |
| `GET` | `/analysis/results/{worker_id}` | Resultado individual de um colaborador |
| `GET` | `/analysis/delta/{worker_id}/{group_id}` | Delta de um colaborador em um grupo específico |
| `GET` | `/analysis/leaderboard?top=10` | Ranking dos melhores colaboradores |
| `POST` | `/analysis/classify` | Re-classificar com pesos e método customizados |

**`POST /analysis/run`** — executa o pipeline completo:
1. Constrói o grafo NetworkX e o hipergrafo HyperNetX
2. Calcula delta score para cada colaborador em cada grupo
3. Calcula afinidade de cada colaborador com seus grupos
4. Calcula PageRank, betweenness e eigenvector centrality
5. Combina tudo num composite score
6. Classifica como HIGH / NEUTRAL / LOW
7. Persiste os resultados no banco

**`POST /analysis/classify`** — re-classifica com parâmetros customizados (sem persistir):
```json
{
  "weights": {
    "individual_performance": 0.40,
    "proficiency": 0.10,
    "pagerank": 0.25,
    "betweenness": 0.10,
    "mean_affinity": 0.05,
    "mean_delta": 0.10
  },
  "method": "percentile",
  "high_threshold": 0.65,
  "low_threshold": 0.40,
  "n_clusters": 3
}
```

**Métodos de classificação (`method`):**
- `percentile` *(padrão)* — acima do P70 → HIGH, abaixo do P30 → LOW
- `threshold` — baseado nos valores `high_threshold` e `low_threshold`
- `kmeans` — K-Means com `n_clusters` clusters, ranqueados por centroide

---

### Visualization `/viz`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/viz/network` | Grafo interativo (HTML Pyvis) |
| `GET` | `/viz/hypergraph` | Hipergrafo como imagem PNG (base64) |
| `GET` | `/viz/performance-bar` | Gráfico de barras — Plotly JSON |
| `GET` | `/viz/score-scatter` | Scatter PageRank vs Composite — Plotly JSON |

**`GET /viz/network`** — retorna um HTML completo com o grafo interativo:
- Nós verdes = HIGH performers
- Nós vermelhos = LOW performers
- Nós cinzas = NEUTRAL
- Losangos azuis = grupos
- Espessura das arestas proporcional ao peso da relação
- Tooltip com nome, cargo, score e classificação

---

## Algoritmos

### Delta Score

Mede quanto a qualidade do grupo muda com a presença do colaborador:

```
quality(G) = 0.35 × mean(performance_members)
           + 0.30 × mean(collaboration_quality_intra_edges)
           + 0.20 × project_outcome_score
           + 0.15 × baseline_work_quality

delta(w, G) = (quality_with_w − quality_without_w) / quality_without_w
```

Delta positivo → colaborador agrega valor ao grupo.
Delta negativo → colaborador reduz a qualidade do grupo.

### Afinidade

Mede o quanto o colaborador está integrado ao seu grupo:

```
affinity(w, G) = edge_density × mean_collab_quality × tenure_bonus

edge_density  = conexões de w com membros do G / (|G| − 1)
tenure_bonus  = min(1.0, tenure_years / 5.0)
```

### Composite Score

```
composite = Σ(weight_i × metric_i)
```

Onde cada métrica é normalizada para [0, 1] antes da combinação. O delta é normalizado via `(delta + 1) / 2` para deslocar de [-1, +inf] para [0, 1].

---

## Tecnologias

| Biblioteca | Uso |
|---|---|
| FastAPI | API REST |
| SQLAlchemy | ORM + SQLite |
| Pydantic v2 | Validação de dados |
| NetworkX | Grafo dirigido ponderado (PageRank, betweenness) |
| HyperNetX | Hipergrafo de grupos |
| pandas / numpy | Manipulação de matrizes de scores |
| scikit-learn | K-Means para classificação por clusters |
| Pyvis | Visualização interativa do grafo |
| Plotly | Gráficos de performance |
| matplotlib | Render do hipergrafo |
| pytest | Testes automatizados |
