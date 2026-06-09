"""
==============================================================================
 Optimisation de la Durée de Vie d'un Réseau de Capteurs (Coverage Problem)
==============================================================================

Contexte :
----------
On dispose de N capteurs, chacun doté d'une batterie limitée, et de M zones à
surveiller. Un capteur peut couvrir plusieurs zones. On veut activer les
capteurs par "configurations" (sous-ensembles couvrant toutes les zones) et
maximiser la durée de vie totale du réseau, c'est-à-dire le temps pendant
lequel au moins une configuration est active et couvre l'intégralité des zones.

Approche :
----------
1. Lecture du fichier d'instance (.txt).
2. Génération d'un ensemble de configurations valides via une heuristique
   aléatoire avec phase de nettoyage (suppression des capteurs redondants).
3. Génération d'un Programme Linéaire (LP) en format CPLEX LP.
4. Résolution via le solveur GLPK (glpsol) et affichage des résultats.

Usage :
-------
    python main.py <chemin_du_fichier_instance.txt>

Dépendances :
-------------
    - Python 3.x (bibliothèque standard uniquement)
    - GLPK (glpsol doit être installé et accessible dans le PATH)
==============================================================================
"""

import sys
import os
import random
import subprocess


# ==============================================================================
# MODULE 1 : PARSEUR DE FICHIER D'ENTRÉE
# ==============================================================================

def parse_instance(filepath: str) -> tuple[int, int, list[int], list[set[int]]]:
    """
    Lit et analyse le fichier d'instance au format texte strict.

    Format attendu du fichier :
        Ligne 1 : N (nombre de capteurs, entier)
        Ligne 2 : M (nombre de zones, entier)
        Ligne 3 : N entiers séparés par des espaces (batterie max de chaque capteur)
        Lignes 4 à 4+N-1 : indices des zones couvertes par le capteur i (espaces-séparés)

    Les lignes vides éventuelles sont ignorées. Les espaces superflus sont
    nettoyés via .strip().split().

    Paramètres :
        filepath (str) : Chemin vers le fichier d'instance.

    Retourne :
        tuple (N, M, batteries, couvertures) :
            N          (int)          : Nombre de capteurs.
            M          (int)          : Nombre de zones.
            batteries  (list[int])    : Batterie maximale de chaque capteur (1-indexé
                                        en interne, stocké à l'indice 0..N-1).
            couvertures(list[set])    : couvertures[i] = ensemble des zones couvertes
                                        par le capteur i (indices 0-basés).

    Lève :
        FileNotFoundError : Si le fichier n'existe pas.
        ValueError        : Si le format du fichier est incorrect.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Fichier introuvable : '{filepath}'")

    with open(filepath, 'r', encoding='utf-8') as f:
        toutes_lignes_brutes = f.readlines()

    # Lignes nettoyées (strip) mais SANS filtrer les vides — on en a besoin pour les couvertures
    toutes_lignes = [l.strip() for l in toutes_lignes_brutes]

    # Lignes non-vides pour N, M et batteries (les 3 premières infos)
    lignes_non_vides = [l for l in toutes_lignes if l]

    if len(lignes_non_vides) < 3:
        raise ValueError("Le fichier d'instance est trop court (moins de 3 lignes non-vides).")

    # -- Lecture de N et M --
    try:
        N = int(lignes_non_vides[0])
        M = int(lignes_non_vides[1])
    except ValueError as e:
        raise ValueError(f"Erreur de lecture de N ou M : {e}")

    if N <= 0 or M <= 0:
        raise ValueError(f"N et M doivent être des entiers positifs (N={N}, M={M}).")

    # -- Lecture des batteries --
    try:
        batteries = list(map(int, lignes_non_vides[2].split()))
    except ValueError as e:
        raise ValueError(f"Erreur de lecture des batteries (ligne 3) : {e}")

    if len(batteries) != N:
        raise ValueError(
            f"Le nombre de valeurs de batterie ({len(batteries)}) "
            f"ne correspond pas à N={N}."
        )

    # -- Lecture des zones couvertes par chaque capteur --
    # On repère la ligne des batteries dans le fichier brut pour lire exactement N lignes ensuite
    # (y compris les lignes vides = capteur sans zone)
    idx_batteries = -1
    batteries_str = lignes_non_vides[2]
    for idx, l in enumerate(toutes_lignes):
        if l == batteries_str:
            idx_batteries = idx
            break

    if idx_batteries == -1 or idx_batteries + N >= len(toutes_lignes) + 1:
        raise ValueError(
            f"Le fichier doit contenir {N} lignes de couverture après les batteries, "
            "mais le fichier est trop court."
        )

    couvertures: list[set[int]] = []
    for i in range(N):
        ligne_idx = idx_batteries + 1 + i
        if ligne_idx >= len(toutes_lignes):
            # Ligne absente = capteur sans zone
            couvertures.append(set())
            continue
        ligne_cov = toutes_lignes[ligne_idx]
        try:
            zones = set(map(int, ligne_cov.split())) if ligne_cov else set()
        except ValueError as e:
            raise ValueError(f"Erreur de lecture des zones du capteur {i+1} : {e}")
        couvertures.append(zones)

    # -- Validation : toutes les zones déclarées existent bien dans [0, M-1] ou [1, M] --
    # On détecte automatiquement si les indices sont 0-basés ou 1-basés
    toutes_zones = set().union(*couvertures) if couvertures else set()
    if toutes_zones and max(toutes_zones) > M:
        raise ValueError(
            f"Un indice de zone ({max(toutes_zones)}) est supérieur à M={M}."
        )

    print(f"[Parseur] Instance chargée : {N} capteurs, {M} zones.")
    print(f"[Parseur] Batteries : {batteries}")
    for i, cov in enumerate(couvertures):
        print(f"[Parseur] Capteur {i+1} couvre les zones : {sorted(cov)}")

    return N, M, batteries, couvertures


# ==============================================================================
# MODULE 2 : HEURISTIQUE DE GÉNÉRATION DE CONFIGURATIONS
# ==============================================================================

def generer_configurations(
    N: int,
    M: int,
    couvertures: list[set[int]],
    nb_iterations: int = 10_000,
    graine: int | None = None
) -> set[frozenset[int]]:
    """
    Génère un ensemble de configurations valides via une heuristique aléatoire.

    Une configuration est un frozenset d'indices de capteurs (0-basés) tel que
    l'union de leurs zones couvertes contient toutes les M zones.

    Algorithme (par itération) :
        1. Mélanger aléatoirement la liste des capteurs.
        2. Ajouter des capteurs un par un jusqu'à couvrir toutes les M zones
           (construction gloutonne aléatoire).
        3. Phase de nettoyage : pour chaque capteur de la configuration,
           vérifier s'il est redondant (i.e., sa suppression ne compromet pas
           la couverture totale). Si oui, le retirer définitivement.
        4. Ajouter la configuration nettoyée (minimale) à l'ensemble global.

    La phase de nettoyage garantit que les configurations générées sont
    minimales (non redondantes), ce qui améliore la qualité du modèle LP.

    Paramètres :
        N             (int)        : Nombre de capteurs.
        M             (int)        : Nombre de zones.
        couvertures   (list[set])  : couvertures[i] = zones couvertes par capteur i.
        nb_iterations (int)        : Nombre d'itérations de l'heuristique (défaut : 10 000).
        graine        (int|None)   : Graine pour la reproductibilité (None = aléatoire).

    Retourne :
        set[frozenset[int]] : Ensemble des configurations uniques (minimales) trouvées.

    Lève :
        ValueError : Si aucune configuration valide ne peut être construite
                     (cas où les capteurs ne couvrent pas toutes les M zones).
    """
    if graine is not None:
        random.seed(graine)

    # Déterminer l'ensemble cible de toutes les zones
    toutes_zones = set().union(*couvertures)
    if len(toutes_zones) < M:
        raise ValueError(
            f"Les capteurs ne couvrent que {len(toutes_zones)} zones sur {M} : "
            "aucune configuration valide ne peut couvrir toutes les zones."
        )

    # Adapter M à l'ensemble réel des zones (gérer les indices 0-basés ou 1-basés)
    ensemble_cible = toutes_zones  # Ensemble exact des zones à couvrir

    configurations: set[frozenset[int]] = set()
    indices_capteurs = list(range(N))

    for iteration in range(nb_iterations):
        # --- Étape 1 : Construction aléatoire ---
        ordre = indices_capteurs[:]
        random.shuffle(ordre)

        config_courante: list[int] = []
        zones_couvertes: set[int] = set()

        for capteur in ordre:
            config_courante.append(capteur)
            zones_couvertes |= couvertures[capteur]
            if zones_couvertes >= ensemble_cible:
                break  # Couverture totale atteinte

        # Vérification : la configuration couvre-t-elle toutes les zones ?
        if zones_couvertes < ensemble_cible:
            # Cas pathologique : ne devrait pas arriver si ensemble_cible est atteignable
            continue

        # --- Étape 2 : Phase de nettoyage (suppression des capteurs redondants) ---
        # On itère en ordre inverse pour minimiser les recalculs
        config_nettoyee = list(config_courante)
        i = 0
        while i < len(config_nettoyee):
            capteur_test = config_nettoyee[i]
            # Zones couvertes sans ce capteur
            zones_sans = set().union(
                *(couvertures[c] for c in config_nettoyee if c != capteur_test)
            ) if len(config_nettoyee) > 1 else set()

            if zones_sans >= ensemble_cible:
                # Ce capteur est redondant : on le retire définitivement
                config_nettoyee.pop(i)
                # Ne pas incrémenter i : on reteste la même position
            else:
                i += 1

        # --- Étape 3 : Stockage de la configuration minimale ---
        config_finale = frozenset(config_nettoyee)
        configurations.add(config_finale)

    print(f"\n[Heuristique] {nb_iterations} itérations effectuées.")
    print(f"[Heuristique] {len(configurations)} configuration(s) unique(s) trouvée(s).")

    if not configurations:
        raise ValueError("Aucune configuration valide trouvée. Vérifiez l'instance.")

    return configurations


# ==============================================================================
# MODULE 3 : GÉNÉRATION DU PROGRAMME LINÉAIRE (.lp)
# ==============================================================================

def generer_lp(
    N: int,
    batteries: list[int],
    configurations: set[frozenset[int]],
    fichier_lp: str = "modele.lp"
) -> list[frozenset[int]]:
    """
    Génère un fichier de Programme Linéaire au format CPLEX LP.

    Modèle mathématique :
    ---------------------
    Soit K le nombre de configurations uniques C_1, C_2, ..., C_K.
    Soit t_k le temps d'activation de la configuration C_k.

    Maximiser  : sum_{k=1}^{K} t_k          (durée de vie totale du réseau)

    Sous contraintes :
        Pour chaque capteur i (i = 1..N) :
            sum_{k : i ∈ C_k} t_k  <=  batterie_i
        (La somme des temps d'activation de toutes les configurations incluant
         le capteur i ne peut dépasser la batterie de ce capteur.)

    Bornes :
        t_k >= 0   pour tout k = 1..K

    Paramètres :
        N              (int)              : Nombre de capteurs.
        batteries      (list[int])        : Batteries des capteurs (0-indexés).
        configurations (set[frozenset])   : Ensemble des configurations valides.
        fichier_lp     (str)              : Nom/chemin du fichier LP à générer.

    Retourne :
        list[frozenset[int]] : La liste ordonnée des configurations (pour mapping
                               entre variable t_k et sa composition).
    """
    # Convertir en liste pour avoir un ordre stable et un index fixe
    configs_liste: list[frozenset[int]] = sorted(configurations, key=lambda c: sorted(c))
    K = len(configs_liste)

    with open(fichier_lp, 'w', encoding='utf-8') as f:
        # -- En-tête (commentaires au format CPLEX LP : antislash en début de ligne) --
        f.write(f"\\ Programme Lineaire : Maximisation de la duree de vie du reseau\n")
        f.write(f"\\ N={N} capteurs, K={K} configurations\n\n")

        # -- Fonction objectif --
        # GLPK a une limite de longueur de ligne (~32 KB). Pour les grandes instances,
        # on découpe l'objectif en lignes avec le + EN FIN de ligne (syntaxe valide CPLEX LP).
        f.write("Maximize\n")
        f.write("  obj:")
        TERMES_PAR_LIGNE = 50  # ~50 variables par ligne pour rester sous la limite
        for k in range(K):
            if k % TERMES_PAR_LIGNE == 0 and k > 0:
                f.write("\n       ")  # continuation en début de ligne suivante
            separateur = " +" if k > 0 else ""
            f.write(f"{separateur} t{k+1}")
        f.write("\n\n")

        # -- Contraintes --
        f.write("Subject To\n")
        for i in range(N):
            # Récupérer les configurations incluant le capteur i
            configs_avec_i = [k for k, config in enumerate(configs_liste) if i in config]

            if not configs_avec_i:
                # Ce capteur n'apparaît dans aucune configuration : contrainte triviale, on l'omet
                continue

            termes = [f"t{k+1}" for k in configs_avec_i]
            contrainte = " + ".join(termes)
            f.write(f"  c_capteur_{i+1}: {contrainte} <= {batteries[i]}\n")

        f.write("\n")

        # -- Bornes --
        f.write("Bounds\n")
        for k in range(K):
            f.write(f"  0 <= t{k+1}\n")

        f.write("\nEnd\n")

    print(f"\n[Générateur LP] Fichier '{fichier_lp}' généré avec succès.")
    print(f"[Générateur LP] {K} variable(s) de temps | {N} contrainte(s) de batterie.")

    return configs_liste


# ==============================================================================
# MODULE 4 : EXÉCUTION DU SOLVEUR ET PARSING DES RÉSULTATS
# ==============================================================================

def resoudre_et_afficher(
    configs_liste: list[frozenset[int]],
    fichier_lp: str = "modele.lp",
    fichier_sol: str = "solution.txt"
) -> None:
    """
    Exécute GLPK (glpsol) pour résoudre le LP, puis parse et affiche les résultats.

    Étapes :
        1. Lancer : glpsol --lp <fichier_lp> -o <fichier_sol>
        2. Lire <fichier_sol> généré par GLPK.
        3. Extraire la valeur de l'objectif (durée de vie maximale).
        4. Extraire les variables t_k > 0 et afficher leur composition.

    Format du fichier de sortie GLPK (solution.txt) :
        GLPK génère un fichier texte avec des sections. La valeur objective
        se trouve après "obj" dans la section des colonnes, et les variables
        sont listées avec leur valeur.

    Paramètres :
        configs_liste (list[frozenset]) : Liste ordonnée des configurations
                                          (même ordre que dans le fichier LP).
        fichier_lp    (str)             : Chemin du fichier LP à résoudre.
        fichier_sol   (str)             : Chemin du fichier solution GLPK.

    Lève :
        RuntimeError  : Si glpsol échoue ou si le parsing de la solution échoue.
        FileNotFoundError : Si glpsol n'est pas trouvé dans le PATH.
    """
    # --- Étape 1 : Exécution de GLPK ---
    commande = ["glpsol", "--lp", fichier_lp, "-o", fichier_sol]
    print(f"\n[Solveur] Lancement de la commande : {' '.join(commande)}")

    try:
        resultat = subprocess.run(
            commande,
            capture_output=True,
            text=True,
            timeout=120  # Timeout de 2 minutes
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            "La commande 'glpsol' est introuvable. "
            "Vérifiez que GLPK est installé et accessible dans le PATH système."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Le solveur GLPK a dépassé le délai d'attente (120s).")

    # Afficher la sortie de GLPK pour diagnostic
    if resultat.stdout:
        print("[GLPK stdout]")
        print(resultat.stdout)
    if resultat.stderr:
        print("[GLPK stderr]")
        print(resultat.stderr)

    if resultat.returncode != 0:
        raise RuntimeError(
            f"GLPK a retourné un code d'erreur : {resultat.returncode}. "
            "Consultez la sortie ci-dessus pour le diagnostic."
        )

    # --- Étape 2 : Lecture du fichier solution ---
    if not os.path.isfile(fichier_sol):
        raise FileNotFoundError(
            f"Le fichier solution '{fichier_sol}' n'a pas été créé par GLPK."
        )

    with open(fichier_sol, 'r', encoding='utf-8') as f:
        contenu_solution = f.read()

    # --- Étape 3 : Extraction de la valeur de l'objectif ---
    valeur_objectif = None
    statut_resolution = None

    for ligne in contenu_solution.splitlines():
        ligne_stripped = ligne.strip()

        # Chercher le statut de résolution
        if ligne_stripped.startswith("Status:"):
            statut_resolution = ligne_stripped.split(":", 1)[1].strip()

        # Chercher la valeur de l'objectif
        # Format GLPK : "Objective:  obj = <valeur> (MAXimum)"
        if "Objective:" in ligne_stripped and "obj" in ligne_stripped:
            try:
                # Extraire la valeur numérique après "="
                partie = ligne_stripped.split("=", 1)[1].strip()
                valeur_str = partie.split()[0]
                valeur_objectif = float(valeur_str)
            except (IndexError, ValueError):
                pass

    # --- Étape 4 : Extraction des variables actives (t_k > 0) ---
    variables_actives: dict[int, float] = {}

    # Parser la section des colonnes dans le fichier solution GLPK
    # Format typique :
    #   No. Column name  St   Activity     Lower bound   Upper bound    Marginal
    #   --- ------------ -- ------------- ------------- ------------- -------------
    #     1 t1           B    <valeur>         0                       
    in_colonnes = False
    for ligne in contenu_solution.splitlines():
        ligne_stripped = ligne.strip()

        # Détecter le début de la section des colonnes
        if "Column name" in ligne_stripped and "Activity" in ligne_stripped:
            in_colonnes = True
            continue

        # Fin de section (ligne vide ou nouvelle section)
        if in_colonnes:
            if not ligne_stripped or ligne_stripped.startswith("---"):
                if "---" in ligne_stripped:
                    continue  # Ligne de séparation, continuer
                else:
                    in_colonnes = False
                    continue

            # Parser une ligne de variable
            # Format : "   N  t<k>   <statut>   <valeur>   ..."
            parties = ligne_stripped.split()
            if len(parties) >= 4:
                try:
                    # parties[0] = numéro, parties[1] = nom variable,
                    # parties[2] = statut (B, L, U, F, NS...), parties[3] = activité
                    nom_var = parties[1]
                    activite_str = parties[3]
                    activite = float(activite_str)

                    # Vérifier que c'est bien une variable t<k>
                    if nom_var.startswith("t") and nom_var[1:].isdigit():
                        k = int(nom_var[1:]) - 1  # Convertir en index 0-basé
                        if activite > 1e-9:  # Strictement positif (tolérance numérique)
                            variables_actives[k] = activite
                except (ValueError, IndexError):
                    pass

    # --- Affichage des résultats ---
    print("\n" + "=" * 60)
    print("           RÉSULTATS DE L'OPTIMISATION")
    print("=" * 60)

    if statut_resolution:
        print(f"  Statut          : {statut_resolution}")

    if valeur_objectif is not None:
        print(f"  Durée de vie max: {valeur_objectif:.6f} unités de temps")
    else:
        print("  [AVERTISSEMENT] Valeur de l'objectif non trouvée dans la solution.")

    print(f"\n  Configurations actives ({len(variables_actives)} sur {len(configs_liste)}) :")
    print("-" * 60)

    if variables_actives:
        for k, duree in sorted(variables_actives.items(), key=lambda x: -x[1]):
            config = configs_liste[k]
            capteurs_str = ", ".join(str(c + 1) for c in sorted(config))
            print(f"  t{k+1:>4} = {duree:>10.6f}  |  Capteurs : {{{capteurs_str}}}")
    else:
        print("  Aucune variable active trouvée (solution triviale ou problème infaisable).")

    print("=" * 60)


# ==============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ==============================================================================

def main():
    """
    Point d'entrée du programme.

    Orchestre les 4 modules dans l'ordre :
        1. Parsing du fichier d'instance.
        2. Génération des configurations par heuristique.
        3. Génération du fichier LP.
        4. Résolution et affichage.
    """
    # -- Vérification des arguments de ligne de commande --
    if len(sys.argv) < 2:
        print("Usage : python main.py <fichier_instance.txt>")
        print("Exemple : python main.py instance1.txt")
        sys.exit(1)

    fichier_instance = sys.argv[1]

    print("=" * 60)
    print("  Optimisation de la Durée de Vie d'un Réseau de Capteurs")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # MODULE 1 : Parsing
    # -------------------------------------------------------------------------
    print("\n--- Module 1 : Lecture de l'instance ---")
    try:
        N, M, batteries, couvertures = parse_instance(fichier_instance)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERREUR] Impossible de lire l'instance : {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # MODULE 2 : Heuristique
    # -------------------------------------------------------------------------
    print("\n--- Module 2 : Génération des configurations ---")
    try:
        configurations = generer_configurations(
            N=N,
            M=M,
            couvertures=couvertures,
            nb_iterations=10_000  # Paramétrable ici
        )
    except ValueError as e:
        print(f"[ERREUR] Heuristique échouée : {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # MODULE 3 : Génération du LP
    # -------------------------------------------------------------------------
    print("\n--- Module 3 : Génération du fichier LP ---")
    fichier_lp = "modele.lp"
    fichier_sol = "solution.txt"

    configs_liste = generer_lp(
        N=N,
        batteries=batteries,
        configurations=configurations,
        fichier_lp=fichier_lp
    )

    # -------------------------------------------------------------------------
    # MODULE 4 : Résolution et affichage
    # -------------------------------------------------------------------------
    print("\n--- Module 4 : Résolution et affichage ---")
    try:
        resoudre_et_afficher(
            configs_liste=configs_liste,
            fichier_lp=fichier_lp,
            fichier_sol=fichier_sol
        )
    except (FileNotFoundError, RuntimeError) as e:
        print(f"[ERREUR] Résolution échouée : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
