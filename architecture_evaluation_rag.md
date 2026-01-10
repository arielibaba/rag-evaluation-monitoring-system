# Module d'Évaluation et d'Amélioration de Performance RAG

## Projet : RAG Evaluation & Monitoring System (REMS)

**Version :** 0.0.1  
**Date :** Janvier 2026  

---

## Table des Matières

1. [Contexte](#1-contexte)
2. [Problématique](#2-problématique)
3. [Objectifs](#3-objectifs)
4. [Périmètre](#4-périmètre)
5. [Architecture Générale](#5-architecture-générale)
6. [Modules du Système](#6-modules-du-système)
7. [Intégration Giskard & RAGAS](#7-intégration-giskard--ragas)
8. [Livrables](#8-livrables)

---

## 1. Contexte

### 1.1 Situation Actuelle

L'organisation dispose d'un **chatbot réglementaire opérationnel** basé sur une architecture RAG (Retrieval-Augmented Generation). Ce chatbot est en production et répond quotidiennement aux questions des utilisateurs sur des sujets réglementaires complexes.

La chaîne RAG du chatbot existant comprend les composants suivants :

| Composant | Rôle |
|-----------|------|
| **Indexing** | Découpage des documents réglementaires en chunks et vectorisation |
| **Retriever** | Recherche des documents pertinents dans la base vectorielle |
| **Query Reformulator** | Reformulation/expansion de la requête utilisateur |
| **LLM Generator** | Génération de la réponse à partir des documents retrouvés |
| **Memory/History** | Gestion du contexte conversationnel |

### 1.2 Enjeux du Domaine Réglementaire

Le domaine réglementaire impose des exigences particulièrement strictes :

- **Exactitude absolue** : Une erreur sur un texte de loi peut avoir des conséquences juridiques
- **Traçabilité** : Chaque réponse doit pouvoir être rattachée à ses sources
- **Actualité** : Les informations obsolètes doivent être détectées et exclues
- **Conformité** : Les réponses doivent respecter le cadre réglementaire applicable

---

## 2. Problématique

### 2.1 Problèmes Identifiés

#### Opacité des Performances
Actuellement, il n'existe aucune visibilité objective sur la qualité des réponses produites par le chatbot. Les problèmes ne sont découverts que par les retours utilisateurs, souvent tardivement.

#### Diagnostic Difficile
Lorsqu'une réponse est incorrecte ou de mauvaise qualité, il est impossible de déterminer rapidement quel composant de la chaîne RAG est responsable :
- Est-ce que les mauvais documents ont été retrouvés ? (problème de retrieval)
- Est-ce que le LLM a inventé des informations ? (hallucination)
- Est-ce que la requête a été mal reformulée ? (problème de reformulation)
- Est-ce que le contexte historique a créé de la confusion ? (problème de mémoire)

#### Absence de Métriques Standardisées
Sans métriques objectives et continues, il est impossible de :
- Suivre l'évolution de la qualité dans le temps
- Comparer différentes configurations
- Prendre des décisions d'amélioration basées sur des données

#### Risques Non Maîtrisés
Les hallucinations du LLM (génération d'informations fausses) peuvent passer inaperçues, créant un risque juridique et réputationnel significatif.

### 2.2 Matrice des Risques

| Risque | Probabilité | Impact | Criticité |
|--------|-------------|--------|-----------|
| Hallucination sur un texte de loi | Moyenne | Critique | **Critique** |
| Citation d'une information obsolète | Haute | Haute | **Haute** |
| Mauvaise attribution des sources | Moyenne | Haute | **Haute** |
| Réponse incomplète | Haute | Moyenne | Moyenne |
| Confusion due au contexte historique | Moyenne | Moyenne | Moyenne |

---

## 3. Objectifs

### 3.1 Objectifs Principaux

| # | Objectif | Description |
|---|----------|-------------|
| O1 | **Observabilité Complète** | Mesurer la performance de chaque composant de la chaîne RAG avec des métriques précises et actionnables |
| O2 | **Détection Proactive** | Identifier les dégradations de qualité et les anomalies avant qu'elles n'impactent les utilisateurs |
| O3 | **Diagnostic Automatisé** | Localiser automatiquement les composants défaillants et leurs causes racines |
| O4 | **Reporting Actionnable** | Générer des rapports exploitables (PDF, HTML, dashboards) pour différentes audiences |
| O5 | **Amélioration Continue** | Proposer des recommandations de correctifs et permettre des actions automatisées |
| O6 | **Intégration Pipeline** | S'intégrer dans le pipeline CI/CD pour un monitoring continu en production |

### 3.2 Objectifs Quantitatifs

| Indicateur | Situation Actuelle | Cible |
|------------|-------------------|-------|
| Temps de détection d'une dégradation | Plusieurs jours | < 1 heure |
| Couverture d'évaluation automatique | 0% | 100% |
| Temps de diagnostic d'un incident | 4-8 heures | < 15 minutes |
| Fréquence des rapports | Ad-hoc manuel | Quotidien automatique |
| Taux de détection des hallucinations | Inconnu (~40%) | > 95% |

---

## 4. Périmètre

### 4.1 Dans le Périmètre

✅ Évaluation des performances du chatbot existant  
✅ Collecte et analyse des interactions (query → response)  
✅ Évaluation des documents retrouvés par le retriever (si accessible)  
✅ Détection des hallucinations et problèmes de qualité  
✅ Génération de rapports PDF, HTML et dashboards  
✅ Diagnostic automatique des causes d'erreur  
✅ Recommandations d'amélioration (et actions automatisables)  
✅ Monitoring continu et système d'alerting  
✅ Intégration au pipeline CI/CD existant  

### 4.2 Hors Périmètre

❌ Modification du code source du chatbot existant  
❌ Implémentation d'un nouveau système RAG  
❌ Gestion de l'infrastructure du chatbot  
❌ Ré-entraînement des modèles du chatbot  

### 4.3 Prérequis d'Intégration

Le module d'évaluation nécessite l'accès aux données suivantes depuis le chatbot :

| Donnée | Nécessité | Description |
|--------|-----------|-------------|
| Query utilisateur | **Obligatoire** | La question posée par l'utilisateur |
| Réponse générée | **Obligatoire** | La réponse produite par le chatbot |
| Documents retrouvés | **Recommandé** | Les chunks/documents utilisés pour la génération |
| Scores de similarité | Optionnel | Les scores de retrieval pour chaque document |
| Query reformulée | Optionnel | La requête après reformulation/expansion |
| Historique conversation | Optionnel | Le contexte conversationnel injecté |
| Ground truth | Optionnel | Réponses de référence pour évaluation supervisée |

---

## 5. Architecture Générale

### 5.1 Vue d'Ensemble

Le système REMS est un **module externe** qui se connecte au chatbot existant pour collecter, évaluer et analyser les interactions, sans modifier le fonctionnement du chatbot.

```
┌─────────────────────────────────────────────────────────────┐
│                  CHATBOT RAG EXISTANT                        │
│              (Ne subit aucune modification)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ Interactions (logs / API / webhook)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│          RAG EVALUATION & MONITORING SYSTEM (REMS)          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Couche d'Intégration                       │ │
│  │   Collecte des interactions depuis le chatbot          │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Couche d'Évaluation                        │ │
│  │   Évaluateurs par composant + End-to-End               │ │
│  │   (Giskard + RAGAS)                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Couche Diagnostic & Recommandations             │ │
│  │   Analyse des causes + Propositions de correctifs      │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Couche Reporting & Monitoring                 │ │
│  │   Rapports PDF/HTML + Dashboard + Alertes              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  PIPELINE CI/CD EXISTANT                     │
│          (GitLab CI, Airflow, Prometheus, Slack...)         │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Principes Architecturaux

| Principe | Description |
|----------|-------------|
| **Non-intrusif** | Le module n'impacte pas les performances du chatbot |
| **Découplé** | Architecture asynchrone avec message queue |
| **Adaptatif** | S'adapte aux données disponibles (évaluation partielle si données incomplètes) |
| **Extensible** | Ajout facile de nouveaux évaluateurs ou métriques |
| **Observable** | Le module lui-même expose des métriques de fonctionnement |

---

## 6. Modules du Système

### 6.1 Module d'Intégration (Data Collector)

#### Description
Ce module est responsable de la collecte des interactions depuis le chatbot existant. Il s'adapte à différents modes de connexion selon l'architecture du chatbot.

#### Modes de Collecte Supportés

| Mode | Description | Cas d'usage |
|------|-------------|-------------|
| **Webhook Receiver** | Endpoint HTTP recevant les interactions en temps réel | Le chatbot pousse chaque interaction |
| **API Poller** | Interrogation périodique d'une API du chatbot | Le chatbot expose une API de consultation |
| **Log Collector** | Lecture des fichiers de logs structurés | Logs JSON/structured logging |
| **Database Connector** | Connexion directe à la base de données (lecture seule) | Accès à la DB des conversations |
| **File Watcher** | Surveillance d'un répertoire pour imports batch | Évaluation offline ou rétroactive |

#### Responsabilités
- Connexion aux sources de données du chatbot
- Normalisation des données vers un format unifié
- Gestion des erreurs et retry
- Buffering en cas d'indisponibilité temporaire
- Validation de l'intégrité des données

#### Données Collectées
Pour chaque interaction, le module collecte (selon disponibilité) :
- Identifiant unique de l'interaction
- Timestamp
- Query utilisateur
- Réponse générée
- Documents/chunks retrouvés
- Scores de retrieval
- Query reformulée
- Historique de conversation
- Métadonnées (latence, version du modèle, user ID...)

---

### 6.2 Module Retrieval Evaluator

#### Description
Ce module évalue la qualité du processus de retrieval, c'est-à-dire la capacité du chatbot à retrouver les documents pertinents pour répondre à une question.

#### Prérequis
- Query utilisateur ✓
- Documents/chunks retrouvés ✓ (obligatoire pour ce module)
- Ground truth des sources (optionnel, améliore la précision)

#### Métriques Évaluées

| Métrique | Description | Source |
|----------|-------------|--------|
| **Context Relevancy** | Pertinence des documents retrouvés par rapport à la question | RAGAS |
| **Context Precision** | Proportion de documents pertinents parmi ceux retrouvés | RAGAS |
| **Context Recall** | Proportion de documents pertinents effectivement retrouvés (nécessite ground truth) | RAGAS |
| **Redundancy Score** | Taux de redondance/duplication entre les documents retrouvés | Custom |
| **Coverage Score** | Mesure dans laquelle les documents couvrent tous les aspects de la question | Custom |

#### Analyses Produites
- Score de pertinence pour chaque document retrouvé
- Identification des documents non pertinents (bruit)
- Détection de lacunes (aspects de la question non couverts)
- Comparaison avec les sources attendues (si ground truth disponible)

---

### 6.3 Module Query Reformulator Evaluator

#### Description
Ce module évalue la qualité des reformulations de requêtes effectuées par le chatbot (si applicable). Il vérifie que la reformulation préserve l'intention originale tout en améliorant le retrieval.

#### Prérequis
- Query originale ✓
- Query reformulée ✓ (obligatoire pour ce module)

#### Métriques Évaluées

| Métrique | Description |
|----------|-------------|
| **Intent Preservation** | Mesure de la conservation de l'intention utilisateur après reformulation |
| **Semantic Similarity** | Similarité sémantique entre query originale et reformulée |
| **Query Expansion Quality** | Qualité des termes ajoutés lors de l'expansion |
| **Retrieval Impact** | Amélioration effective du retrieval grâce à la reformulation |

#### Analyses Produites
- Détection des reformulations qui dénaturent la question
- Identification des pertes d'information
- Évaluation de l'enrichissement sémantique
- Impact mesuré sur la qualité du retrieval

---

### 6.4 Module Generator Evaluator (LLM)

#### Description
Ce module évalue la qualité des réponses générées par le LLM. C'est le module le plus critique car il détecte les hallucinations et vérifie la fidélité aux sources.

#### Prérequis
- Query utilisateur ✓
- Réponse générée ✓
- Documents retrouvés (fortement recommandé)
- Ground truth de la réponse (optionnel)

#### Métriques Évaluées

| Métrique | Description | Source |
|----------|-------------|--------|
| **Faithfulness** | Fidélité de la réponse aux documents sources (pas d'invention) | RAGAS |
| **Answer Relevancy** | Pertinence de la réponse par rapport à la question | RAGAS |
| **Hallucination Score** | Détection et quantification des hallucinations | Giskard |
| **Answer Correctness** | Exactitude de la réponse (nécessite ground truth) | RAGAS |
| **Completeness** | Complétude de la réponse (tous les aspects traités) | Custom |
| **Regulatory Compliance** | Conformité au cadre réglementaire | Custom |

#### Détection des Hallucinations
Le module utilise une approche en plusieurs étapes :
1. **Extraction des claims** : Identification des affirmations factuelles dans la réponse
2. **Vérification** : Chaque claim est vérifié contre les documents sources
3. **Classification** : Les claims non supportés sont classifiés comme hallucinations
4. **Scoring** : Calcul d'un score global d'hallucination

#### Analyses Produites
- Liste des affirmations non supportées par les sources
- Score de fidélité global
- Détection des contradictions avec les sources
- Alertes pour les hallucinations critiques (textes de loi, chiffres...)

---

### 6.5 Module Memory/History Evaluator

#### Description
Ce module évalue la qualité de la gestion du contexte conversationnel. Il vérifie que l'historique de conversation est utilisé de manière pertinente et ne crée pas de confusion.

#### Prérequis
- Query utilisateur ✓
- Réponse générée ✓
- Historique de conversation ✓ (obligatoire pour ce module)

#### Métriques Évaluées

| Métrique | Description |
|----------|-------------|
| **Context Relevance** | Pertinence du contexte historique injecté par rapport à la question actuelle |
| **History Utilization** | Taux d'utilisation effective de l'historique dans la réponse |
| **Coherence with History** | Cohérence de la réponse avec les échanges précédents |
| **Contradiction Detection** | Détection de contradictions avec des réponses précédentes |

#### Analyses Produites
- Identification du contexte historique pertinent vs non pertinent
- Détection des cas où l'historique crée de la confusion
- Mesure de l'impact du contexte sur la qualité de la réponse
- Recommandations sur la taille de fenêtre optimale

---

### 6.6 Module End-to-End Evaluator

#### Description
Ce module orchestre tous les évaluateurs et produit une évaluation globale de la chaîne RAG. Il agrège les scores, identifie les bottlenecks et attribue les erreurs aux composants responsables.

#### Responsabilités

| Fonction | Description |
|----------|-------------|
| **Orchestration** | Coordonne l'exécution de tous les évaluateurs |
| **Agrégation** | Calcule un score de qualité global pondéré |
| **Bottleneck Detection** | Identifie le composant le plus faible de la chaîne |
| **Error Attribution** | Attribue les erreurs détectées aux composants responsables |
| **Trend Analysis** | Analyse les tendances de qualité dans le temps |

#### Score Global
Le score global est calculé comme une moyenne pondérée des scores de chaque composant :

| Composant | Poids par défaut |
|-----------|-----------------|
| Retrieval | 30% |
| Generation | 40% |
| Reformulation | 10% |
| Memory | 20% |

Les poids sont configurables selon l'importance relative de chaque composant pour l'organisation.

#### Niveaux de Qualité

| Niveau | Score | Description |
|--------|-------|-------------|
| Excellent | ≥ 0.90 | Qualité optimale, aucune action requise |
| Bon | 0.75 - 0.89 | Qualité satisfaisante, améliorations mineures possibles |
| Acceptable | 0.60 - 0.74 | Qualité suffisante mais améliorations recommandées |
| Faible | 0.40 - 0.59 | Qualité insuffisante, actions correctives nécessaires |
| Critique | < 0.40 | Qualité inacceptable, intervention urgente requise |

---

### 6.7 Module de Diagnostic (Root Cause Analyzer)

#### Description
Ce module analyse les résultats d'évaluation pour identifier les causes racines des problèmes détectés. Il établit des corrélations entre les symptômes observés et les causes probables.

#### Fonctionnement

1. **Détection des Symptômes**
   - Scores faibles sur certaines métriques
   - Patterns d'erreurs récurrents
   - Anomalies par rapport aux baselines

2. **Analyse Causale**
   - Corrélation entre métriques (ex: faible context precision → faible faithfulness)
   - Analyse temporelle (dégradation progressive vs soudaine)
   - Clustering des erreurs par type

3. **Attribution**
   - Mapping symptômes → causes probables
   - Score de confiance pour chaque hypothèse
   - Priorisation par impact

#### Catalogue des Causes Racines

| Symptôme | Causes Probables | Composant |
|----------|------------------|-----------|
| Faible context relevancy | Mauvaise qualité des embeddings, seuil de similarité inadapté | Retriever |
| Faible faithfulness | Prompt insuffisamment contraignant, température LLM trop haute | Generator |
| Hallucinations fréquentes | Contexte insuffisant, guardrails absents | Generator |
| Faible context recall | Top-K trop faible, chunks trop petits | Retriever/Indexing |
| Incohérence avec historique | Fenêtre de contexte trop courte, mauvaise sélection | Memory |
| Perte d'intention | Reformulation trop agressive | Reformulator |

---

### 6.8 Module de Recommandations (Remediation Engine)

#### Description
Ce module génère des recommandations d'amélioration basées sur le diagnostic. Il peut également déclencher des actions automatiques pour les correctifs à faible risque.

#### Types de Recommandations

| Type | Description | Exemple |
|------|-------------|---------|
| **Paramétrage** | Ajustement de paramètres existants | "Augmenter le top-K de 3 à 5" |
| **Configuration** | Modification de la configuration | "Activer le reranker" |
| **Prompt** | Amélioration des prompts | "Ajouter une instruction de citation des sources" |
| **Architecture** | Changement structurel | "Implémenter un hybrid search BM25 + dense" |
| **Data** | Action sur les données | "Réindexer les documents avec chunks plus petits" |

#### Niveaux d'Automatisation

| Niveau | Description | Approbation |
|--------|-------------|-------------|
| **Manuel** | Recommandation uniquement, action humaine requise | N/A |
| **Semi-automatique** | Action préparée, déclenchement sur approbation | Requise |
| **Automatique** | Action déclenchée automatiquement (faible risque) | Non requise |

#### Exemples de Correctifs Automatisables
- Ajustement des seuils de similarité
- Modification de la température du LLM
- Ajout de guardrails dans le prompt système
- Modification de la taille de la fenêtre de contexte

---

### 6.9 Module de Reporting

#### Description
Ce module génère des rapports d'évaluation dans différents formats et pour différentes audiences.

#### Types de Rapports

| Rapport | Audience | Contenu | Format |
|---------|----------|---------|--------|
| **Rapport Exécutif** | Direction, Management | KPIs principaux, tendances, risques | PDF |
| **Rapport Technique** | Équipe technique | Métriques détaillées, analyses, échantillons | HTML, PDF |
| **Rapport de Conformité** | Compliance, Juridique | Incidents, violations, attestations | PDF |
| **Dashboard Temps Réel** | Opérations, Support | Métriques live, alertes | Grafana |

#### Contenu du Rapport Exécutif
- Score de qualité global et tendance
- Comparaison avec la période précédente
- Top 3 des problèmes identifiés
- Risques et recommandations prioritaires
- Statut des actions en cours

#### Contenu du Rapport Technique
- Métriques détaillées par composant
- Distribution des scores
- Analyse des échecs (exemples anonymisés)
- Corrélations entre métriques
- Diagnostic des causes racines
- Recommandations techniques détaillées

#### Fréquence
| Type | Fréquence |
|------|-----------|
| Dashboard | Temps réel |
| Rapport quotidien | Tous les jours à 7h |
| Rapport hebdomadaire | Chaque lundi |
| Rapport mensuel | Premier jour du mois |

---

### 6.10 Module d'Alerting

#### Description
Ce module gère les alertes en temps réel basées sur des seuils configurables et des détections d'anomalies.

#### Types d'Alertes

| Sévérité | Critères | Action | Canal |
|----------|----------|--------|-------|
| **Critique** | Hallucination détectée, score < 0.4 | Notification immédiate + possible blocage | PagerDuty, SMS |
| **Haute** | Score < 0.6, dégradation > 20% | Notification équipe | Slack, Email |
| **Moyenne** | Score < 0.75, anomalie détectée | Log + notification journalière | Email digest |
| **Basse** | Recommandation d'amélioration | Inclusion dans rapport | Rapport hebdo |

#### Seuils Configurables

| Métrique | Seuil Warning | Seuil Critique |
|----------|---------------|----------------|
| Overall Score | < 0.70 | < 0.50 |
| Faithfulness | < 0.75 | < 0.60 |
| Hallucination Rate | > 5% | > 15% |
| Context Relevancy | < 0.65 | < 0.50 |

---

### 6.11 Module de Monitoring Continu

#### Description
Ce module assure l'évaluation continue en production avec différentes stratégies selon le volume et la criticité.

#### Stratégies d'Évaluation

| Stratégie | Description | Utilisation |
|-----------|-------------|-------------|
| **Temps Réel** | Évaluation de chaque interaction | Métriques critiques (hallucination, compliance) |
| **Sampling** | Évaluation d'un échantillon aléatoire | Métriques coûteuses (LLM-as-judge) |
| **Batch** | Évaluation périodique en lot | Analyses approfondies, tendances |

#### Taux de Sampling Recommandés

| Volume quotidien | Sampling Rate | Interactions évaluées |
|------------------|---------------|----------------------|
| < 1 000 | 100% | Toutes |
| 1 000 - 10 000 | 20% | 200 - 2 000 |
| 10 000 - 100 000 | 5% | 500 - 5 000 |
| > 100 000 | 1% | > 1 000 |

#### Intégration CI/CD
Le module s'intègre au pipeline CI/CD pour :
- **Quality Gates** : Blocage du déploiement si les scores sont insuffisants
- **Regression Testing** : Comparaison avant/après chaque mise à jour
- **Canary Analysis** : Évaluation comparative lors de déploiements progressifs

---

## 7. Intégration Giskard & RAGAS

### 7.1 Rôle de RAGAS

RAGAS (Retrieval-Augmented Generation Assessment) fournit les métriques standardisées pour l'évaluation RAG :

| Métrique RAGAS | Utilisation dans REMS |
|----------------|----------------------|
| **Faithfulness** | Évaluation de la fidélité aux sources (Generator Evaluator) |
| **Answer Relevancy** | Pertinence de la réponse (Generator Evaluator) |
| **Context Precision** | Précision du retrieval (Retrieval Evaluator) |
| **Context Recall** | Rappel du retrieval (Retrieval Evaluator) |
| **Context Relevancy** | Pertinence des contextes (Retrieval Evaluator) |
| **Answer Correctness** | Exactitude vs ground truth (Generator Evaluator) |

### 7.2 Rôle de Giskard

Giskard fournit des capacités complémentaires :

| Fonctionnalité Giskard | Utilisation dans REMS |
|------------------------|----------------------|
| **Hallucination Detection** | Scan automatique des hallucinations |
| **LLM-as-Judge** | Évaluation qualitative par LLM |
| **Vulnerability Scan** | Détection de failles (prompt injection, toxicité...) |
| **Test Generation** | Génération automatique de cas de test |
| **CI/CD Integration** | Intégration native aux pipelines |

### 7.3 Complémentarité

| Aspect | RAGAS | Giskard | Utilisation Combinée |
|--------|-------|---------|---------------------|
| Métriques retrieval | ✅ Fort | ⚪ Limité | RAGAS principalement |
| Métriques génération | ✅ Fort | ✅ Fort | Les deux, moyenne pondérée |
| Détection hallucinations | ⚪ Indirect | ✅ Fort | Giskard principalement |
| Génération de tests | ✅ Oui | ✅ Oui | Les deux |
| Scan de vulnérabilités | ❌ Non | ✅ Fort | Giskard uniquement |

---

## 8. Livrables

### 8.1 Livrables Logiciels

| Livrable | Description |
|----------|-------------|
| **REMS Core** | Module principal d'évaluation avec tous les évaluateurs |
| **REMS Connectors** | Connecteurs pour intégration au chatbot (webhook, API, logs...) |
| **REMS Dashboard** | Dashboard Grafana préconfigurée |
| **REMS Reports** | Générateur de rapports PDF/HTML |
| **REMS CLI** | Interface ligne de commande pour évaluations manuelles |
| **REMS API** | API REST pour intégration avec d'autres systèmes |

### 8.2 Livrables Documentation

| Document | Contenu |
|----------|---------|
| **Guide d'Installation** | Procédure de déploiement et configuration |
| **Guide d'Intégration** | Configuration des connecteurs selon l'architecture du chatbot |
| **Guide Utilisateur** | Utilisation des dashboards et rapports |
| **Guide des Métriques** | Description détaillée de chaque métrique |
| **Runbook** | Procédures de résolution des alertes |

### 8.3 Livrables Opérationnels

| Livrable | Description |
|----------|-------------|
| **Dashboards Grafana** | Tableaux de bord préconfigurés |
| **Templates de Rapports** | Templates pour les rapports PDF/HTML |
| **Règles d'Alerting** | Configuration des alertes Prometheus/AlertManager |
| **Pipelines CI/CD** | Jobs GitLab CI / GitHub Actions prêts à l'emploi |

---

## Annexe : Glossaire

| Terme | Définition |
|-------|------------|
| **RAG** | Retrieval-Augmented Generation - Architecture combinant recherche documentaire et génération par LLM |
| **Chunk** | Fragment de document indexé dans la base vectorielle |
| **Retrieval** | Processus de recherche des documents pertinents |
| **Faithfulness** | Mesure de la fidélité d'une réponse aux documents sources |
| **Hallucination** | Génération d'informations non présentes dans les sources |
| **Ground Truth** | Données de référence pour évaluation supervisée |
| **LLM-as-Judge** | Utilisation d'un LLM pour évaluer les réponses d'un autre LLM |
| **Context Precision** | Proportion de documents pertinents parmi les documents retrouvés |
| **Context Recall** | Proportion de documents pertinents effectivement retrouvés |

---

**Document d'Architecture - RAG Evaluation & Monitoring System (REMS)**  
**Version 2.0 - Décembre 2024**
