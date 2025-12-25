# NetCheck (Python)

NetCheck est un petit outil de diagnostic réseau que j'ai bricolé pour le support et les ops. 

L'idée est venue juste après avoir passé mon **CCNA 1** : je voulais un truc simple à lancer quand on me dit "ça ne marche pas", histoire de relier la théorie (modèle OSI, DNS, connectivité IP) à des tests concrets sans avoir à sortir l'artillerie lourde (Wireshark ou des scripts complexes).



L'objectif n'est pas de faire du scan agressif, mais d'avoir un état des lieux clair d'un service ou d'une destination en quelques secondes.

## Pourquoi utiliser NetCheck ?
- Pour valider rapidement une résolution **DNS**.
- Pour vérifier la connectivité **ICMP** (Ping) et **TCP** (ports ouverts).
- Pour tester le temps de réponse d'un service **HTTP/HTTPS**.
- Pour ne plus se faire surprendre par un certificat **TLS** expiré.

## Fonctions incluses
- `--dns` : Résolution de nom d'hôte.
- `--ping` : Test de connectivité classique.
- `--tcp host:port` : Test de connexion sur un port spécifique.
- `--http url` : Vérification du status code et du temps de réponse.
- `--tls host` : Check de la date d'expiration du certificat.
- `--json-out` : Export des résultats pour intégration dans d'autres outils.

## Installation

On passe par un environnement virtuel pour garder ça propre :

```bash
git clone https://github.com/atchekzaileo/NetCheck-outil-de-diagnostic-et-monitoring-l-ger-Python-.git

python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows

pip install -e .
```
## Exemples d’utilisation

### 1. Diagnostic complet (la totale)
C'est ce que je lance quand je veux checker un service de A à Z :
```bash
netcheck \
  --dns github.com \
  --ping 1.1.1.1 \
  --tcp github.com:443,1.1.1.1:53 \
  --http [https://github.com](https://github.com),[https://example.com](https://example.com) \
  --tls github.com \
  --json-out report.json
```
### 2. Test rapide DNS + HTTPS
Simple et efficace pour vérifier qu'un site est "up" :
```bash
netcheck --dns example.com --http [https://example.com](https://example.com)
```

### 3. Test d’échec (Firewall / Port fermé)
Pratique pour confirmer qu'un port est bien bloqué :
```bash
netcheck --tcp 127.0.0.1:9
```

À savoir
Ping : Sous Linux, l'envoi de paquets ICMP peut nécessiter des privilèges sudo selon votre configuration système.

Python : Développé et testé sous Python 3.10+.

### Tests unitaires
Pour vérifier que les modules fonctionnent correctement :
```bash
pip install pytest
pytest -v
```