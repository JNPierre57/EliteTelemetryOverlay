# What is EliteTelemetryOverlay?

EliteTelemetryOverlay affiche dans OBS sur un Mac la valeur estimée de l’expédition d’exploration **en cours** d’EDEB, exécuté sur un Shadow Windows.

```text
EDEB on Shadow → Tailscale → receiver on Mac → OBS Browser Source
```

**État actuel : transport, persistance, overlay animé et diagnostic disponibles ; lecture réelle EDEB en attente du rapport Shadow.** Le rapport Shadow a confirmé SQLite et les colonnes de valeur ; leurs sommes doivent encore être comparées au total affiché par EDEB. Le sender normal refuse donc de démarrer, au lieu de publier un chiffre supposé. Il faut terminer et valider l’adaptateur à partir du diagnostic avant un stream réel. Voir [la découverte EDEB](docs/EDEB-DATA-SOURCE.md).

## Quick Start

Prérequis : Python 3.11+ ; aucune dépendance Python tierce. Depuis le dossier du dépôt sur Mac :

```sh
sh scripts/install-mac.sh
sh scripts/start-mac.sh --demo
```

Dans un second terminal, depuis le même dossier :

```sh
.venv/bin/python -m telemetry.sender --demo
```

Dans OBS, ajouter une **Source navigateur** de **1200 × 180** avec cette URL (fichier local décoché) :

```text
http://127.0.0.1:8765/overlay/
```

La démo démarre à un milliard, augmente, passe à plusieurs milliards, puis teste une diminution et zéro. Elle porte le libellé DEMO et utilise une persistance distincte. À la première ouverture, la valeur est affichée directement. Les augmentations suivantes animent les rouleaux ; les diminutions sont immédiates. Ctrl+C arrête un service. Ne pas lancer deux receivers sur le même port.

Sur Shadow, première action pour débloquer EDEB :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\inspect-edeb.ps1
```

Examiner `reports/edeb-inspection.json` et fournir les éléments décrits dans la documentation source. Après le premier rapport, suivre la comparaison ciblée avec `-TripValue` et `-HistoryValue` décrite dans cette documentation. Ne jamais réinitialiser l’expédition pour installer cet outil.

## Installation et maintenance

- [Réinstallation complète Windows + Mac, OBS, Tailscale et démarrage automatique](docs/INSTALL.md)
- [Source EDEB : faits vérifiés, inconnues et diagnostic](docs/EDEB-DATA-SOURCE.md)
- [Architecture, configuration et protocole](docs/ARCHITECTURE.md)
- [Dépannage avec commandes](docs/TROUBLESHOOTING.md)
- [Validation et limites des tests](docs/TESTING.md)

## Développement

```sh
python3 -m unittest discover -s tests -v
node tests/format.test.cjs
```

Node est uniquement nécessaire au test de formatage, jamais à l’exécution. Les fixtures SQLite sont synthétiques et ne prétendent pas reproduire EDEB. GitHub Actions définit une matrice Windows/macOS/Linux ; les résultats de CI doivent être consultés après publication.

Le code Python commun est dans `telemetry/` (`sender.py`, `receiver.py`, `source.py`) pour éviter de dupliquer configuration et validation. `overlay/` contient les trois technologies web natives ; `tools/` le diagnostic ; `scripts/` les lanceurs. Aucun CDN, Docker, framework ou cloud n’est nécessaire.

Les secrets, rapports et valeurs persistées sont exclus de Git. Le receiver écoute uniquement sur localhost et, si configurée, une adresse IPv4 Tailscale explicite. Aucun port de routeur ni Tailscale Funnel n’est nécessaire. Licence MIT. Projet indépendant de Frontier Developments et d’EDEB.
