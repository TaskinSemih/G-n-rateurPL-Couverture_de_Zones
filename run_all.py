"""
Script d'experimentation automatique - Partie 4 du projet
Lance main.py sur toutes les instances et produit un tableau de resultats.
"""
import subprocess
import sys
import glob
import time
import os

INSTANCES = sorted([
    f for f in glob.glob("*.txt")
    if f not in ("solution.txt",)
])

print("=" * 70)
print("  EXPERIMENTATION - TOUTES LES INSTANCES")
print("=" * 70)
print(f"  Instances : {INSTANCES}\n")

resultats = []

for instance in INSTANCES:
    print(f"\n  [TEST] {instance} ...")

    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "main.py", instance],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )
        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")
        output = stdout + stderr
        duree_exec = time.time() - t0
    except subprocess.TimeoutExpired:
        resultats.append({
            "instance": instance, "N": "?", "M": "?",
            "configs": "?", "duree_vie": "TIMEOUT",
            "statut": "TIMEOUT", "temps": ">300s"
        })
        print("    TIMEOUT")
        continue
    except Exception as e:
        resultats.append({
            "instance": instance, "N": "?", "M": "?",
            "configs": "?", "duree_vie": "ERREUR",
            "statut": "ERREUR", "temps": "-"
        })
        print(f"    ERREUR : {e}")
        continue

    # Parser la sortie
    N, M = "?", "?"
    nb_configs = "?"
    duree_vie = "ECHEC"
    statut = "ECHEC"

    for ligne in output.splitlines():
        # N et M
        if "Instance" in ligne and "capteurs" in ligne:
            parts = ligne.split()
            for i, p in enumerate(parts):
                if p.isdigit():
                    if i + 1 < len(parts) and "capteur" in parts[i+1]:
                        N = p
                    elif i + 1 < len(parts) and "zone" in parts[i+1]:
                        M = p

        # Nb configurations
        if "configuration(s) unique(s)" in ligne:
            parts = ligne.strip().split()
            if parts:
                nb_configs = parts[1]

        # Duree de vie
        if "vie max" in ligne and ":" in ligne:
            try:
                val = ligne.split(":")[1].strip().split()[0]
                duree_vie = float(val)
            except Exception:
                pass

        # Statut
        if "Statut" in ligne and ":" in ligne:
            statut = ligne.split(":", 1)[1].strip()

    resultats.append({
        "instance": instance,
        "N": N, "M": M,
        "configs": nb_configs,
        "duree_vie": duree_vie,
        "statut": statut,
        "temps": f"{duree_exec:.1f}s"
    })

    print(f"    N={N}, M={M}, Configs={nb_configs}, Duree={duree_vie}, Statut={statut}, Temps={duree_exec:.1f}s")

# Tableau final
print("\n" + "=" * 80)
print("  TABLEAU RECAPITULATIF")
print("=" * 80)
print(f"  {'Instance':<25} {'N':>5} {'M':>5} {'Configs':>8} {'Duree de vie':>14} {'Statut':>10} {'Temps':>7}")
print("  " + "-" * 76)
for r in resultats:
    dv = f"{r['duree_vie']:.4f}" if isinstance(r['duree_vie'], float) else str(r['duree_vie'])
    print(f"  {r['instance']:<25} {str(r['N']):>5} {str(r['M']):>5} {str(r['configs']):>8} {dv:>14} {str(r['statut']):>10} {str(r['temps']):>7}")
print("=" * 80)
