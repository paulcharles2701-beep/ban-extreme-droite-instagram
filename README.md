## Road to Ban toute l'extrême droite sur Instagram

Pas mal de posts Instagram ont commencé à partager des listes de comptes d'extrême droite à bloquer.

https://www.instagram.com/p/DfCaZQxCIPr/

L'idée de ce projet est de faciliter le blocage de ces comptes en automatisant le processus sur Instagram. Je trouvais assez fastidieux de le faire manuellement pour chaque compte. Ce script permet de gagner du temps et de s'assurer que les comptes restent bien bloqués, d'autant qu'Instagram débloque parfois périodiquement des comptes que vous aviez bloqués.

Le script est écrit en Python et utilise [Playwright](https://playwright.dev/) pour automatiser les interactions avec Instagram. Le fichier `comptes.txt` contient la liste des comptes à bloquer, un par ligne. Pour l'instant, la liste provient de listes partagées sur Instagram et du site [onbloquelextremedroite.fr](https://www.onbloquelextremedroite.fr/liste), mais vous pouvez y ajouter vos propres comptes. N'hésitez pas à proposer des modifications ou des ajouts au projet.

### Installation

1. Assurez-vous d'avoir Python installé sur votre machine.
2. Installez les dépendances :
   ```bash
   pip install playwright
   python -m playwright install chromium
   ```

### Utilisation

1. *(Optionnel)* Mettez à jour la liste depuis le site :
   ```bash
   python extraire_liste.py
   ```
   Le fichier `comptes.txt` est régénéré, avec les comptes regroupés par catégorie.

2. Lancez le blocage :
   ```bash
   python block-accounts.py
   ```

Une fenêtre de navigateur s'ouvre. Connectez-vous à votre compte Instagram, puis le script bloque automatiquement les comptes de `comptes.txt`.

### Un blocage réparti sur plusieurs jours

Bloquer beaucoup de comptes d'un coup peut amener Instagram à considérer votre activité comme suspecte, et à restreindre temporairement votre compte. Le script limite donc le nombre de blocages à **30 par jour** (paramètre `MAX_PAR_JOUR`). La liste actuelle d'environ 110 comptes est ainsi traitée en **4 jours**.

Il suffit de **relancer le script une fois par jour** :

- l'avancement est enregistré dans `resultats.csv` ;
- les comptes déjà bloqués sont ignorés et le script reprend là où il s'est arrêté ;
- si le quota du jour est atteint, le script s'arrête et vous invite à revenir le lendemain ;
- à la fin de chaque exécution, il affiche le nombre de comptes restants et une estimation du nombre de jours nécessaires.

Exemple de sortie :

```
📊 Avancement : 30/109 comptes traités
   Aujourd'hui : 0/30 blocages
   À traiter : 79 compte(s), quota restant : 30
...
📅 Encore 49 compte(s), environ 2 jour(s). Relancez demain.
```

### Revérification automatique

Comme Instagram débloque parfois des comptes, chaque compte est **revérifié 30 jours** après son dernier contrôle (paramètre `REVERIF_JOURS`). S'il est toujours bloqué, rien ne se passe. Sinon, il est bloqué à nouveau. Une fois la liste entièrement traitée, lancer le script de temps en temps suffit pour garder vos blocages à jour.

### Paramètres

Les paramètres se trouvent en haut de `block-accounts.py` :

| Paramètre | Défaut | Description |
|---|---|---|
| `MAX_PAR_JOUR` | `30` | Nombre maximum de blocages par jour |
| `REVERIF_JOURS` | `30` | Délai avant de revérifier un compte déjà bloqué |
| `DELAI_MIN` / `DELAI_MAX` | `8` / `20` | Pause aléatoire entre deux comptes, en secondes |

Il est déconseillé d'augmenter fortement `MAX_PAR_JOUR` ou de réduire les délais.

### En cas de problème

- **« Réessayez plus tard »** : Instagram limite temporairement vos actions. Le script s'arrête de lui-même. Attendez au moins 24 h avant de relancer.
- **Un compte en erreur** : une capture d'écran `erreur_<compte>.png` est créée. Le compte sera retenté au prochain lancement.
- **Recommencer de zéro** : supprimez `resultats.csv`