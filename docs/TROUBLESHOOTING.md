# Troubleshooting

Exécuter les commandes depuis la racine du dépôt. Pour un port personnalisé, adapter les URLs. Ctrl+C arrête un processus manuel. Ne jamais joindre `config.local.json` à un rapport de problème.

## OBS affiche 0 ou un tiret

Un tiret signifie qu’aucune donnée n’a été reçue. Un zéro signifie un véritable update zéro, notamment la fin de la démo. Vérifier :

```sh
curl --fail http://127.0.0.1:8765/api/value
```

`source: demo` indique la démo. Ne pas confondre ses données et la production. Vérifier la lecture réelle sur Shadow avec `py -3 -m telemetry.source` : une erreur conserve la dernière valeur, sans publier zéro. Consulter [la source](EDEB-DATA-SOURCE.md).

## OBS affiche une ancienne valeur

Vérifier le même endpoint, puis les logs sender et EDEB. Sans changement de valeur, aucun POST n’est envoyé : un timestamp ancien est normal quand on n’explore pas. Il n’existe pas de heartbeat qui prouve qu’EDEB tourne. Vérifier le trip directement. Après perte/suppression manuelle du cache receiver, redémarrer le sender pour republier la valeur inchangée. Une coupure réseau provoque un rattrapage du dernier total, pas de chaque étape intermédiaire.

## Shadow ne contacte pas le Mac / MagicDNS ne résout pas

```powershell
$c = Get-Content .\config.local.json -Raw | ConvertFrom-Json
$uri = [Uri]$c.receiver_url
& "$env:ProgramFiles\Tailscale\tailscale.exe" status
& "$env:ProgramFiles\Tailscale\tailscale.exe" ping $uri.Host
Resolve-DnsName $uri.Host
Test-NetConnection -ComputerName $uri.Host -Port $uri.Port
Invoke-RestMethod ($c.receiver_url.TrimEnd('/') + '/health')
```

Vérifier le même tailnet, les machines connectées et MagicDNS activé dans la console Tailscale. Si la résolution échoue, remplacer le hostname dans `receiver_url` par l’IPv4 Tailscale du Mac. Vérifier le port, le pare-feu Mac et les règles du tailnet. Ne pas remplacer par une IP publique ou LAN : le sender les refuse. Aucun proxy HTTP n’est utilisé.

## HTTP 401 / mauvais token

Copier la même valeur de `token` dans les deux fichiers locaux, sans espace supplémentaire. Redémarrer les deux processus. Ne pas réexécuter l’installateur pour espérer changer le secret : il préserve le fichier existant. Un test POST réservé à un receiver en **démo** :

```powershell
$c = Get-Content .\config.local.json -Raw | ConvertFrom-Json
$body = @{value=1000000000; timestamp=[DateTime]::UtcNow.ToString('o'); source='demo'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri ($c.receiver_url.TrimEnd('/') + '/api/value') -ContentType 'application/json' -Headers @{Authorization=('Bearer ' + $c.token)} -Body $body
```

Ne pas activer la transcription PowerShell pendant la manipulation d’un secret. HTTP 400 : vérifier entier JSON (pas une chaîne), source, timestamp avec fuseau et mode démo du receiver. HTTP 503 : vérifier les droits et l’espace disque du dossier `data`.

## Receiver inaccessible / erreur au démarrage

```sh
curl --fail http://127.0.0.1:8765/health
lsof -nP -iTCP:8765 -sTCP:LISTEN
/Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4
sh scripts/start-mac.sh
```

`Address already in use` : un receiver existe déjà, éventuellement LaunchAgent. `Can't assign requested address` : Tailscale n’est pas connecté ou `tailscale_ip` n’est pas l’IP de ce Mac. Ne pas contourner en écoutant sur `0.0.0.0`. Échec de lecture du cache : conserver une copie du fichier corrompu, vérifier sa provenance et restaurer une sauvegarde valide ; l’application refuse de le remplacer silencieusement par zéro.

## EDEB mis à jour / schéma incompatible

Le lecteur accepte le schéma et la version de base 279 observés sur Shadow. Toute incompatibilité bloque les envois et préserve la dernière valeur, avec reprise automatique si la source redevient lisible. Après mise à jour EDEB, relancer :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\inspect-edeb.ps1 -OutputPath .\reports\edeb-after-update.json
```

Comparer le rapport à la version validée et vérifier le total dans EDEB. Ne jamais migrer la base avec cet outil ni ajouter un nom de table au hasard.

## EDEB n’est pas lancé / DB verrouillée

Ouvrir EDEB dans la session Windows du bon utilisateur. Une base sur disque n’est pas une preuve que les dernières activités ont été traitées. Si l’inspection signale un fichier verrouillé ou modifié pendant la copie, retenter lorsqu’EDEB est moins actif. Si nécessaire, fermer EDEB normalement, inspecter puis le relancer. Ne pas forcer l’arrêt, modifier les permissions ni supprimer un WAL/SHM/journal. Le diagnostic laisse les originaux intacts.

## Valeur différente d’EDEB

Comparer Current Exploration Trip, pas Overall History ou la valeur du système courant. Vérifier commandant, version, fin de scan et mode DEMO. Relever l’heure, la valeur affichée et les composantes cartographie/biologie ; fournir un rapport redigé selon [EDEB-DATA-SOURCE.md](EDEB-DATA-SOURCE.md). Ne pas appliquer un offset, ajouter une prime système ou recréer le trip pour masquer l’écart.

## Fond blanc/noir au lieu de transparent

Utiliser **Source navigateur** avec l’URL `/overlay/`, pas Capture de fenêtre ou Capture d’écran. Le CSS fourni force un fond transparent ; une fenêtre de navigateur externe peut néanmoins paraître noire. Dans OBS placer la source au-dessus d’une image colorée pour vérifier l’alpha. Retirer un CSS personnalisé OBS qui imposerait un fond. Vérifier les dimensions 1200 × 180.

## Browser Source ne se rafraîchit plus

Vérifier `/health`, puis les propriétés OBS → Actualiser le cache de la page. Le polling ne dépend d’aucun CDN. Vérifier que l’URL correspond au port courant. Lors d’une coupure, la dernière valeur est conservée avec un message. Après modification de configuration, redémarrer le receiver et actualiser la source. L’absence d’animation à l’ouverture ou lors d’une baisse est normale ; les préférences système de mouvement réduit désactivent aussi les rouleaux.

## Mac ou Shadow redémarré

Relancer Tailscale, EDEB et les services dans l’ordre du [guide](INSTALL.md). Le cache Mac conserve la valeur, le sender renvoie son premier relevé. Pour LaunchAgent :

```sh
launchctl print gui/$(id -u)/local.EliteTelemetryOverlay.receiver
tail -n 50 data/receiver.log
```

Les logs LaunchAgent ne sont pas automatiquement tournants : les archiver/supprimer lorsque le receiver est arrêté s’ils grossissent. Sous Windows, consulter l’historique du Planificateur et relancer manuellement le sender pour voir l’erreur. Ne pas lancer deux instances.

## Nouvelle expédition après Reset Exploration Trip Data

Le receiver accepte zéro et toutes les baisses, sans défilement inverse. Si l’ancien chiffre reste présent, vérifier d’abord la valeur native EDEB, puis la source et la connectivité. Ne pas effacer le cache comme solution à un lecteur incorrect. Le lecteur suit les marqueurs de trip à chaque lecture ; le reset natif EDEB reste à vérifier lors de votre prochain vrai départ.

## EDEB « filters no longer agree »

Les rapports initiaux ne distinguaient pas certains filtres parce que les valeurs non complétées/non issues des Journals étaient nulles au sens numérique (zéro). Si ces lignes portent désormais une valeur non nulle, le lecteur refuse de choisir une formule sans preuve. Il conserve le dernier total et retente. Après stabilisation d’EDEB, relancer le diagnostic avec `-TripValue` et `-HistoryValue` comme indiqué dans [EDEB-DATA-SOURCE.md](EDEB-DATA-SOURCE.md), puis comparer les filtres.

## EDEB « snapshot changed », « rollback journal » ou « read unavailable »

Une activité d’écriture peut empêcher une copie stable ; le sender retente automatiquement après deux secondes, sans écriture dans EDEB. Si l’erreur dure, vérifier `py -3 -m telemetry.source`, le chemin et les droits en lecture. Pour une base très volumineuse, augmenter `read_interval`. Ne supprimer aucun WAL/SHM/journal pour forcer la lecture. En cas de doute, fermer EDEB normalement, vérifier la lecture puis relancer EDEB.
