# REMS - RAG Evaluation & Monitoring System

Système d'évaluation et de monitoring pour chatbots RAG réglementaires.

## Fonctionnalités

- **Évaluation RAGAS** : Faithfulness, Context Precision/Relevancy, Answer Relevancy
- **Détection d'hallucinations** : Identification automatique des réponses non fidèles aux sources
- **Diagnostic automatique** : Analyse des causes racines et recommandations
- **Interface web** : Dashboard Streamlit avec visualisation des métriques
- **Rapports** : Export PDF, HTML et YAML des recommandations
- **Scheduling** : Évaluations hebdomadaires automatisées via cron

## Installation

```bash
# Cloner le repository
git clone https://github.com/arielibaba/rag-evaluation-monitoring-system-for-regulatory.git
cd rag-evaluation-monitoring-system-for-regulatory

# Installer les dépendances
uv sync

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API et URL de base de données

# Initialiser la base de données
uv run rems init-db
```

## Configuration

Créez un fichier `.env` à partir de `.env.example` :

```env
REMS_DATABASE_URL=postgresql://user:password@localhost:5432/rems
REMS_CHATBOT_API_URL=http://localhost:8000
REMS_GOOGLE_API_KEY=your-google-api-key
REMS_EVALUATION_MODEL=gemini-2.0-flash
```

## Utilisation

### Interface Web

```bash
uv run rems web
```

Accédez à http://localhost:8501 pour :
- Voir le dashboard avec les scores actuels
- Consulter l'historique des évaluations
- Lancer une nouvelle évaluation

### CLI

```bash
# Évaluation depuis un fichier JSON
uv run rems evaluate --file interactions.json

# Évaluation depuis l'API du chatbot
uv run rems evaluate --start 2026-01-01 --end 2026-01-07 --name "Eval Semaine 1"

# Collecte des interactions sans évaluation
uv run rems collect --start 2026-01-01 --limit 100 --store
```

### Évaluation Hebdomadaire Automatique

```bash
# Ajouter au crontab (chaque lundi à 8h)
crontab -e
0 8 * * 1 /chemin/vers/scripts/weekly_evaluation.sh
```

## Format des Données

Le fichier JSON d'interactions doit respecter ce format :

```json
{
  "interactions": [
    {
      "query": "Quelle est la procédure de déclaration ?",
      "response": "Selon l'article 12, la procédure...",
      "retrieved_documents": [
        {
          "content": "Article 12 - Procédure de déclaration...",
          "source": "reglement_2024.pdf"
        }
      ]
    }
  ]
}
```

## Outputs

### Fichier YAML de recommandations

```yaml
evaluation_id: "abc123"
evaluation_date: "2026-01-10T08:00:00"
overall_score: 0.72
quality_level: acceptable

recommendations:
  - component: generator
    priority: high
    issue: "faithfulness trop faible: 65.0% (seuil: 75.0%)"
    suggestion: "Ajouter des instructions explicites dans le prompt..."
    parameter_adjustments:
      generator.temperature:
        action: decrease
        suggested_value: 0.3
```

### Rapports PDF/HTML

Générés dans le dossier `reports/` avec :
- Score global et tendance
- Métriques détaillées par composant
- Distribution des scores
- Recommandations prioritaires

## Architecture

```
src/rems/
├── cli.py                 # Interface ligne de commande
├── config.py              # Configuration (variables d'env)
├── models/                # Modèles SQLAlchemy (PostgreSQL)
├── collector/             # Collecte des interactions (API/fichier)
├── evaluators/            # Évaluateurs RAGAS
├── diagnostic/            # Analyse des causes racines
├── recommendations/       # Génération des recommandations
├── reports/               # Génération PDF/HTML
└── web/                   # Interface Streamlit
```

## Technologies

- **RAGAS** - Métriques d'évaluation RAG
- **LangChain + Gemini** - LLM-as-judge
- **PostgreSQL + SQLAlchemy** - Stockage des évaluations
- **Streamlit + Plotly** - Interface web
- **WeasyPrint** - Génération PDF

## Licence

MIT
