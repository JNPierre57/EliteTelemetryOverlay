# Reinstalling from scratch

Cette procédure suppose Windows 11 sur Shadow et macOS Apple Silicon sur le Mac. Il n’est pas nécessaire de se souvenir de l’ancienne installation. **Le lecteur EDEB est disponible pour le schéma observé (version de base 279). Les sommes du rapport Shadow correspondent à EDEB ; vérifier maintenant le lecteur sur votre installation avant de streamer.**

Une réinstallation ne peut pas recréer une expédition disparue : conserver une sauvegarde EDEB et les Journals avant de remplacer le Shadow. Restaurer EDEB suivant ses procédures, puis vérifier le Current Exploration Trip dans EDEB lui-même. EliteTelemetryOverlay ne restaure ni ne modifie ces données.

## Shadow

1. Installer Elite Dangerous via votre plateforme habituelle, sélectionner Odyssey / Live et ouvrir le jeu avec le bon commandant.
2. Installer/ouvrir [EDEB depuis son site officiel](https://www.panostrede.de/EDEB/). Relever la version. Si l’expédition existait déjà, vérifier sa valeur avant toute autre opération. **Ne pas utiliser Reset Exploration Trip Data pendant l’installation.**
3. Vérifier qu’EDEB lit les Journals. Leur emplacement habituel est `%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous`. Dans les préférences EDEB, vérifier le chemin, puis observer un événement du jeu dans EDEB.
4. Installer Python 3.11 ou supérieur depuis [python.org](https://www.python.org/downloads/windows/), avec le lanceur `py`. Ouvrir un nouveau PowerShell et vérifier `py -3 --version`. Si plusieurs Python sont présents, le Python par défaut de `py -3` doit être au moins 3.11.
5. Installer [Tailscale pour Windows](https://tailscale.com/download/windows), ouvrir l’application, se connecter.
6. Utiliser le même compte/tailnet sur les deux machines. Vérifier que Shadow et le Mac figurent dans la page Machines de la console Tailscale. [Guide officiel](https://tailscale.com/kb/1017/install).
7. Ouvrir le dépôt EliteTelemetryOverlay sur votre compte GitHub, copier son URL HTTPS avec le bouton Code. Installer [Git for Windows](https://git-scm.com/downloads/win), puis :

```powershell
$RepoUrl = Read-Host 'Coller l URL HTTPS du depot EliteTelemetryOverlay'
git clone $RepoUrl
Set-Location EliteTelemetryOverlay
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-shadow.ps1
```

Alternative : télécharger ZIP depuis GitHub, décompresser, ouvrir PowerShell dans le dossier contenant README.md puis exécuter le script d’installation. Le dépôt est publié sur https://github.com/JNPierre57/EliteTelemetryOverlay.

8. Le script crée `.venv` et `config.local.json`, sans écraser une configuration existante. Ouvrir `notepad .\config.local.json`.
9. Dans `receiver_url`, mettre `http://<nom-MagicDNS-du-Mac>:8765` ou `http://<IP-Tailscale-du-Mac>:8765`. Remplacer les chevrons et leur contenu. Le champ `tailscale_ip` est utilisé seulement par le receiver sur Mac, pas par le sender.
10. Copier **la valeur du token du Mac** dans le champ `token` du Shadow via un moyen privé. Les deux installations génèrent initialement des secrets différents : il faut les aligner. Ne pas inclure le token dans une capture, un commit ou un message de diagnostic.
11. Vérifier la lecture réelle sans envoyer de données au Mac :

```powershell
py -3 -m telemetry.source
```

Le programme détecte automatiquement `%LOCALAPPDATA%\Elite Dangerous Exploration Buddy\db\EDEB.db` et affiche le total existant avec ses composantes. Comparer à Current Exploration Trip dans EDEB. Pour un emplacement personnalisé, ajouter `edeb_db_path` dans `config.local.json` (chemin absolu ; doubler les antislashs JSON ou utiliser `/`). La commande ponctuelle accepte également `--database 'D:\Custom EDEB\db\EDEB.db'`.

En cas de schéma incompatible, d’ambiguïté des filtres ou d’écart, suivre [EDEB-DATA-SOURCE.md](EDEB-DATA-SOURCE.md) et lancer le diagnostic. Ne pas masquer l’erreur avec un offset ou un reset.

12. Après démarrage du receiver Mac en démo, tester la chaîne depuis Shadow :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-shadow.ps1 -Demo
```

Le receiver Mac doit avoir été démarré avec `--demo`. Pour la lecture réelle, après comparaison réussie avec EDEB et configuration du Mac :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-shadow.ps1
```

Comparer le premier nombre du log à **Current Exploration Trip**, jamais Overall History. Vérifier une augmentation. Une lecture indisponible est retentée automatiquement sans envoyer zéro. Une incompatibilité persistante nécessite un nouveau diagnostic, pas une réinstallation de Python.

13. Démarrage automatique facultatif, uniquement après validation réelle : ouvrir le Planificateur de tâches → Créer une tâche de base → nom `EliteTelemetryOverlay Sender` → À l’ouverture de session → Démarrer un programme. Programme : chemin absolu vers `.venv\Scripts\python.exe` du dépôt. Arguments : `-m telemetry.sender --config config.local.json`. Champ **Démarrer dans** : chemin absolu du dépôt (sans guillemets). Dans les propriétés, choisir votre compte et « Exécuter uniquement si l’utilisateur est connecté », puis activer le redémarrage en cas d’échec toutes les minutes. Ne pas utiliser un compte SYSTEM : les données EDEB sont propres à votre utilisateur. Les logs sont visibles en lancement manuel ; ne pas activer l’automatisation tant que ce lancement n’est pas fiable. Pour désactiver, désactiver/supprimer cette tâche.

## Mac

1. Installer [OBS Studio pour macOS](https://obsproject.com/download). Utiliser la version Apple Silicon.
2. Installer Python 3.11+ via [python.org pour macOS](https://www.python.org/downloads/macos/). Vérifier dans Terminal : `python3 --version`.
3. Installer [Tailscale pour macOS](https://tailscale.com/docs/install/mac), ouvrir l’application et autoriser la configuration VPN demandée.
4. Rejoindre le même tailnet que Shadow. Dans le menu Tailscale ou la console Machines, copier l’IPv4 Tailscale du Mac et son nom MagicDNS. Le receiver utilise l’IP numérique ; le sender peut utiliser le nom. Si la CLI n’est pas dans PATH, utiliser la commande du bundle ci-dessous :

```sh
/Applications/Tailscale.app/Contents/MacOS/Tailscale status
/Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4
```

5. Cloner l’URL copiée sur GitHub. Si Git manque, accepter l’installation des outils de ligne de commande macOS proposée par `git --version`, ou télécharger le ZIP du dépôt.

```sh
printf 'URL HTTPS du depot : '
read -r REPO_URL
git clone "$REPO_URL"
cd EliteTelemetryOverlay
sh scripts/install-mac.sh
```

6. Ouvrir `config.local.json` avec un éditeur de texte brut. Renseigner `tailscale_ip` avec l’IPv4 Tailscale réelle du Mac, par exemple une adresse commençant par `100.`. Ne pas écrire `0.0.0.0`, l’IP Wi-Fi ou un hostname dans ce champ. Le port par défaut est 8765.
7. Conserver le secret généré et copier sa valeur dans le fichier local Shadow. Les installateurs ne l’affichent pas dans les logs. Pour remplacer un secret perdu, modifier les deux configurations puis redémarrer les deux services.
8. Démarrer en démo pour le premier essai :

```sh
sh scripts/start-mac.sh --demo
```

Pour le stream réel après vérification du lecteur sur Shadow, arrêter avec Ctrl+C puis lancer `sh scripts/start-mac.sh` sans `--demo`. Autoriser Python dans le pare-feu macOS si celui-ci bloque les connexions entrantes ; aucune redirection de port sur votre routeur. Ne pas activer Tailscale Funnel.

9. Dans un autre Terminal :

```sh
curl --fail http://127.0.0.1:8765/health
curl --fail http://127.0.0.1:8765/api/value
```

Avant le premier envoi : `value: null`. Après la démo Shadow : un nombre avec `source: demo`. La démo finit volontairement à zéro après avoir testé les augmentations et le reset. Un zéro n’est pas une erreur s’il a été reçu.

10. OBS → Sources → + → **Navigateur / Browser**. Si cette source n’existe pas, vérifier l’installation officielle d’OBS.
11. Décocher « Fichier local ». URL exacte avec le port par défaut : `http://127.0.0.1:8765/overlay/`.
12. Largeur **1200**, hauteur **180**, 30 FPS suffisent. Pour une police plus grande, augmenter aussi la hauteur. Le texte se réduit automatiquement à la largeur disponible.
13. Placer la source au-dessus de la capture du jeu, vérifier le fond transparent et les rouleaux en relançant la démo. Pour tester l’animation, OBS doit être déjà ouvert quand les valeurs augmentent. À l’ouverture initiale le chiffre se place directement, volontairement. Si le Mac demande de réduire les animations, utiliser explicitement `http://127.0.0.1:8765/overlay/?motion=always` dans OBS pour autoriser les rouleaux dans cette source.
14. Démarrage automatique facultatif après validation : exécuter `python3 tools/make_launch_agent.py` depuis le dépôt. Cette commande écrit un LaunchAgent avec les chemins absolus du dépôt courant ; puis exécuter les commandes indiquées par le script. Il démarre à la connexion de l’utilisateur, relance en cas d’échec et attend donc indirectement Tailscale via ses tentatives de redémarrage. Il ne démarre pas avant la connexion. Ne pas conserver un receiver manuel en parallèle. Les logs sont dans `data/receiver.log`. Après déplacement du dépôt, désactiver l’ancien agent et régénérer son fichier.

## Network check from Shadow

Avec le receiver Mac actif, depuis PowerShell dans le dépôt :

```powershell
$c = Get-Content .\config.local.json -Raw | ConvertFrom-Json
$uri = [Uri]$c.receiver_url
& "$env:ProgramFiles\Tailscale\tailscale.exe" status
& "$env:ProgramFiles\Tailscale\tailscale.exe" ping $uri.Host
Test-NetConnection -ComputerName $uri.Host -Port $uri.Port
Invoke-RestMethod ($c.receiver_url.TrimEnd('/') + '/health')
```

Un ping Tailscale réussi ne suffit pas à prouver que le port HTTP est autorisé. Si nécessaire, autoriser uniquement Shadow vers Mac sur TCP 8765 dans les règles du tailnet. [Pare-feu et Tailscale](https://tailscale.com/kb/1181/firewalls).

## Starting a normal streaming session

Après comparaison du lecteur avec le total EDEB :

1. Lancer Tailscale sur les deux machines.
2. Lancer Elite puis EDEB sur Shadow et vérifier le bon commandant/current trip.
3. Lancer le sender Shadow. Il retente si le Mac n’est pas encore disponible.
4. Lancer le receiver Mac sans `--demo`.
5. Lancer OBS avec la Browser Source.
6. Comparer le total OBS au Current Exploration Trip et vérifier les logs du sender.

Pas besoin de réinstaller ni de régénérer le token à chaque session. Ne pas exécuter le sender manuel si la tâche planifiée fonctionne déjà.

## Starting a new Elite exploration trip

Lorsque vous souhaitez **réellement** commencer une nouvelle expédition, utiliser le menu EDEB **Reset Exploration Trip Data**, qui concerne le trip et non l’historique global. Ne pas supprimer la base ni réinstaller EDEB. Le lecteur suit les systèmes marqués `IsTripHistory = 1` ; le transport accepte toute diminution, y compris zéro, la persiste et l’affiche immédiatement sans animation inverse. Comparer après reset avec EDEB avant de lancer le stream. Le changement de marqueurs est testé sur fixtures ; le comportement du reset natif EDEB doit encore être vérifié lors d’un vrai nouveau départ, pas en sacrifiant l’expédition actuelle.

## Updates, backup, removal

Avant mise à jour, arrêter les services. Sauvegarder séparément `config.local.json` (secret) et `data/last-value.json` (cache), puis mettre à jour le dépôt avec `git pull` si cloné. Exécuter les tests, relancer les scripts d’installation si Python a changé, puis redémarrer. Ne pas commiter ces sauvegardes. La sauvegarde EDEB est indépendante et bien plus importante pour l’expédition.

Pour désinstaller : arrêter les processus, supprimer la tâche Windows ou décharger le LaunchAgent, puis supprimer le dossier du projet. Aucune donnée EDEB ne doit être supprimée.
