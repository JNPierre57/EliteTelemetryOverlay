# What is EliteTelemetryOverlay?

EliteTelemetryOverlay affiche dans OBS sur un Mac la valeur estimée de l’expédition d’exploration **en cours** d’EDEB, exécuté sur un Shadow Windows.

```text
EDEB on Shadow → Tailscale → receiver on Mac → OBS Browser Source
```

**État actuel : lecteur EDEB, transport, persistance et overlay disponibles.** Les sommes extraites du rapport Shadow correspondent exactement aux deux totaux affichés par EDEB. Le lecteur utilise ce schéma vérifié et refuse les données incompatibles ou ambiguës. Il reste à tester son exécution sur Shadow et le flux réel dans OBS ; voir [la source EDEB et ses limites](docs/EDEB-DATA-SOURCE.md).

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

Sur Shadow, pour vérifier la lecture réelle sans config ni réseau :

```powershell
git pull --ff-only
py -3 -m telemetry.source
```

Comparer le chiffre à **Current Exploration Trip** dans EDEB. Ne jamais réinitialiser l’expédition pour installer cet outil. Pour la connexion continue vers le Mac, suivre le guide d’installation. Le diagnostic `tools/inspect-edeb.ps1` reste disponible en cas d’écart ou de mise à jour EDEB.

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
