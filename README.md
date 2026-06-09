<div align="center">

# 📡 GénérateurPL — Couverture de Zones

### Optimisation de la Durée de Vie d'un Réseau de Capteurs

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![GLPK](https://img.shields.io/badge/Solveur-GLPK-orange?style=for-the-badge)](https://www.gnu.org/software/glpk/)
[![Licence](https://img.shields.io/badge/Licence-Académique-blueviolet?style=for-the-badge)](#)
[![S6](https://img.shields.io/badge/Semestre-6-green?style=for-the-badge)](#)

> Projet d'optimisation linéaire en continu — Génération automatique de Programmes Linéaires (PL) pour maximiser la durée de vie d'un réseau de capteurs à couverture de zones.

</div>

---

## 📋 Table des matières

- [Contexte du problème](#-contexte-du-problème)
- [Architecture du projet](#-architecture-du-projet)
- [Format des instances](#-format-des-fichiers-dinstance)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Modèle mathématique](#-modèle-mathématique)
- [Heuristique de génération](#-heuristique-de-génération-de-configurations)
- [Instances de test](#-instances-de-test)
- [Analyse des résultats](#-analyse-des-résultats-partie-5)
- [Structure des fichiers](#-structure-des-fichiers)

---

## 🎯 Contexte du problème

On dispose de **N capteurs** répartis dans un espace, chacun possédant :
- une **batterie limitée** (durée de vie en unités de temps),
- une **zone de couverture** (ensemble de zones qu'il surveille).

L'objectif est de **maximiser la durée de vie totale du réseau**, définie comme la durée pendant laquelle l'intégralité des **M zones** est surveillée en continu.

Pour cela, on organise les capteurs en **configurations** : des sous-ensembles de capteurs qui, ensemble, couvrent toutes les zones. Chaque configuration peut être activée pendant une certaine durée, dans la limite de la batterie de chaque capteur.

Ce problème de **couverture de zones** est formulé comme un **Programme Linéaire (PL)** et résolu exactement par le solveur **GLPK**.

---

## 🏗️ Architecture du projet

Le projet suit un pipeline en 4 modules indépendants et chaînés :

```
Fichier d'instance (.txt)
         │
         ▼
┌─────────────────────┐
│   Module 1          │  parse_instance()
│   Parseur           │  → Lecture N, M, batteries, couvertures
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Module 2          │  generer_configurations()
│   Heuristique       │  → Construction aléatoire + nettoyage (redondances)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Module 3          │  generer_lp()
│   Générateur LP     │  → Écriture du fichier modele.lp (format CPLEX LP)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Module 4          │  resoudre_et_afficher()
│   Solveur GLPK      │  → glpsol → solution.txt → résultats affichés
└─────────────────────┘
```

---

## 📄 Format des fichiers d'instance

Les fichiers d'instance `.txt` suivent le format strict suivant :

```
N                          ← Nombre de capteurs (entier)
M                          ← Nombre de zones (entier)
b1 b2 ... bN               ← Batterie de chaque capteur (N entiers séparés par des espaces)
z1_1 z1_2 ...              ← Zones couvertes par le capteur 1
z2_1 z2_2 ...              ← Zones couvertes par le capteur 2
...                        ← (N lignes au total, une par capteur)
```

**Exemple (`fichier-exemple.txt`)** — 4 capteurs, 3 zones :

```
4
3
6 3 2 6
1 2
2 3
3
1 3
```

**Exemple (`instance_exemple.txt`)** — 5 capteurs, 4 zones :

```
5
4
10 8 6 12 9
1 2
2 3
3 4
1 4
2 3 4
```

> **Note :** Les indices de zones peuvent être 1-basés ou 0-basés, le parseur le détecte automatiquement.

---

## ⚙️ Installation

### Prérequis

- **Python 3.10+** (bibliothèque standard uniquement, aucune dépendance externe)
- **GLPK** (GNU Linear Programming Kit) — solveur LP

### 1. Cloner le dépôt

```bash
git clone https://github.com/TaskinSemih/G-n-rateurPL-Couverture_de_Zones.git
cd G-n-rateurPL-Couverture_de_Zones
```

### 2. Installer GLPK

#### Windows

Télécharger l'exécutable depuis [winglpk](https://sourceforge.net/projects/winglpk/) et ajouter `glpsol.exe` au `PATH`, **ou** le placer directement dans le répertoire du projet.

Le binaire `glpsol.exe` et `glpk_4_65.dll` peuvent également être utilisés directement depuis la racine du projet (non versionnés par Git).

#### Linux / macOS

```bash
# Ubuntu / Debian
sudo apt-get install glpk-utils

# macOS (Homebrew)
brew install glpk
```

#### Vérification

```bash
glpsol --version
```

---

## 🚀 Utilisation

### Résolution d'une instance

```bash
python main.py <fichier_instance.txt>
```

**Exemples :**

```bash
# Instance simple (4 capteurs, 3 zones)
python main.py fichier-exemple.txt

# Instance intermédiaire (5 capteurs, 4 zones)
python main.py instance_exemple.txt

# Instance moyenne (20 capteurs, 10 zones)
python main.py moyen_test_2.txt

# Grosse instance
python main.py gros_test_1.txt
```

**Sortie typique :**

```
============================================================
  Optimisation de la Durée de Vie d'un Réseau de Capteurs
============================================================

--- Module 1 : Lecture de l'instance ---
[Parseur] Instance chargée : 4 capteurs, 3 zones.
[Parseur] Batteries : [6, 3, 2, 6]
...

--- Module 2 : Génération des configurations ---
[Heuristique] 10000 itérations effectuées.
[Heuristique] 7 configuration(s) unique(s) trouvée(s).

--- Module 3 : Génération du fichier LP ---
[Générateur LP] Fichier 'modele.lp' généré avec succès.

--- Module 4 : Résolution et affichage ---

============================================================
           RÉSULTATS DE L'OPTIMISATION
============================================================
  Statut          : OPTIMAL
  Durée de vie max: 11.000000 unités de temps

  Configurations actives (3 sur 7) :
------------------------------------------------------------
     t2 =   6.000000  |  Capteurs : {1, 3}
     t5 =   3.000000  |  Capteurs : {2, 4}
     t7 =   2.000000  |  Capteurs : {1, 2}
============================================================
```

### Expérimentation automatique (toutes les instances)

```bash
python run_all.py
```

Lance `main.py` sur toutes les instances `.txt` du répertoire et affiche un **tableau récapitulatif** avec les durées de vie, statuts et temps d'exécution.

### Analyse de l'influence des itérations (Partie 5)

```bash
python analyse_partie5.py
```

Génère un **rapport HTML interactif** (`rapport_partie5.html`) avec des graphiques Chart.js illustrant l'impact du nombre d'itérations de l'heuristique sur la qualité de la solution.

---

## 📐 Modèle mathématique

Soit :
- $K$ : nombre de configurations valides générées $C_1, C_2, \ldots, C_K$
- $t_k$ : temps d'activation de la configuration $C_k$ (variable de décision)
- $b_i$ : batterie du capteur $i$

**Fonction objectif :**

$$\max \sum_{k=1}^{K} t_k$$

**Contraintes de batterie** (pour chaque capteur $i = 1, \ldots, N$) :

$$\sum_{\{k \mid i \in C_k\}} t_k \leq b_i$$

**Contraintes de non-négativité :**

$$t_k \geq 0 \quad \forall k = 1, \ldots, K$$

Le fichier LP généré (`modele.lp`) suit le **format CPLEX LP**, compatible avec GLPK.

---

## 🔧 Heuristique de génération de configurations

Le module 2 utilise une **heuristique aléatoire gloutonne** avec **phase de nettoyage** pour générer un ensemble diversifié de configurations valides :

### Algorithme (par itération)

1. **Construction aléatoire** : mélanger l'ordre des capteurs et les ajouter un par un jusqu'à couvrir toutes les zones.
2. **Phase de nettoyage** : tester chaque capteur de la configuration — s'il est redondant (sa suppression ne compromet pas la couverture totale), le retirer.
3. **Stockage** : ajouter la configuration minimale résultante à l'ensemble global (dédupliquée via `frozenset`).

### Paramètres clés

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `nb_iterations` | `10 000` | Nombre d'itérations de l'heuristique |
| `graine` | `None` | Graine aléatoire pour la reproductibilité |

> La phase de nettoyage garantit des **configurations minimales** (non redondantes), ce qui améliore la qualité du modèle LP et réduit le temps de résolution.

---

## 🗂️ Instances de test

| Fichier | Capteurs (N) | Zones (M) | Taille |
|---------|-------------|-----------|--------|
| `fichier-exemple.txt` | 4 | 3 | Petite |
| `instance_exemple.txt` | 5 | 4 | Petite |
| `moyen_test_2.txt` | 20 | 10 | Moyenne |
| `moyen_test_3.txt` | — | — | Moyenne |
| `gros_test_1.txt` | — | — | Grande |
| `maxi_test_1.txt` | — | — | Très grande |

---

## 📊 Analyse des résultats (Partie 5)

Le script `analyse_partie5.py` étudie l'**influence du nombre d'itérations** de l'heuristique sur la durée de vie optimale :

- **Paliers testés :** 10, 50, 100, 250, 500, 1 000, 2 000, 5 000, 10 000
- **Répétitions par palier :** 3 (avec graines différentes pour la stabilité statistique)
- **Instances analysées :** 4 instances de tailles variées

### Observations clés

- **Effet de saturation** : au-delà d'un certain seuil d'itérations, les nouvelles configurations sont déjà connues et n'apportent plus de gain sur la durée de vie.
- **Petites instances (N ≤ 10)** : la solution optimale est atteinte rapidement (dès ~100 itérations).
- **Grandes instances (N ≥ 100)** : davantage d'itérations permettent d'explorer un espace plus vaste et d'améliorer significativement la durée de vie.
- **Temps GLPK** : reste faible même avec ~10 000 configurations (méthode du simplexe efficace sur les LP continus).

Le rapport HTML généré (`rapport_partie5.html`) présente ces résultats sous forme de **graphiques interactifs** et d'un tableau détaillé.

---

## 📁 Structure des fichiers

```
GénérateurPL-Couverture_de_Zones/
│
├── main.py                  # Programme principal (pipeline complet)
├── run_all.py               # Script d'expérimentation automatique (Partie 4)
├── analyse_partie5.py       # Analyse de l'influence des itérations (Partie 5)
│
├── fichier-exemple.txt      # Instance petite (4 capteurs, 3 zones)
├── instance_exemple.txt     # Instance petite (5 capteurs, 4 zones)
├── moyen_test_2.txt         # Instance moyenne (20 capteurs, 10 zones)
├── moyen_test_3.txt         # Instance moyenne
├── gros_test_1.txt          # Grande instance
├── maxi_test_1.txt          # Très grande instance
│
├── rapport_final.html       # Rapport HTML final du projet
├── rapport_partie5.html     # Rapport HTML de l'analyse Partie 5
├── Rapport_Projet_Capteur.pdf  # Rapport PDF complet du projet
│
├── .gitignore               # Fichiers exclus du versionnement
└── README.md                # Ce fichier
```

> **Fichiers générés à l'exécution** (non versionnés) :
> - `modele.lp` — Programme Linéaire au format CPLEX LP
> - `solution.txt` — Solution brute retournée par GLPK

---

## 👥 Auteurs

Projet réalisé dans le cadre du **Semestre 6 — Cours d'Optimisation**.

---

<div align="center">

*Optimisation Linéaire — Couverture de Zones — S6*

</div>
