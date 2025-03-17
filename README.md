# Application de Gestion de Clinique Médicale

Une application web Flask pour la gestion d'une clinique médicale, conçue spécifiquement pour les médecins pneumologues.

## Fonctionnalités

- 👨‍⚕️ Gestion des patients et des rendez-vous
- 📝 Suivi des consultations médicales
- 💊 Gestion des symptômes et diagnostics
- 💰 Facturation et suivi des paiements
- 📄 Génération de documents (arrêts de travail, ordonnances)
- 📊 Statistiques et rapports

## Installation

1. Cloner le repository
```bash
git clone https://github.com/votre-username/med-clinic.git
cd med-clinic
```

2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. Installer les dépendances
```bash
pip install -r requirements.txt
```

4. Configurer la base de données
```bash
flask db upgrade
```

5. Lancer l'application
```bash
flask run
```

## Configuration requise

- Python 3.8+
- SQLite ou PostgreSQL
- Navigateur web moderne

## Structure du Projet

## Tests

Pour lancer les tests:
```bash
pytest
```

## Licence

MIT License
