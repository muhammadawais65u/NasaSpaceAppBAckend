# Junior Astronaut Mission Trainer - Backend (FastAPI + Supabase + NASA DONKI)

NASA Space Apps Challenge 2026.

## Setup
```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Mac/Linux: cp .env.example .env  -> then fill in the keys
```

## Supabase
1. Create a project at supabase.com. Put URL, anon key and service-role key in `.env`.
2. In the SQL Editor run, in order: `migrations/001_schema.sql`, `002_rls.sql`, `003_functions.sql`.
3. Authentication -> enable email sign-in, create 2 test users.

## Run
```bash
python scripts/check_nasa.py                 # verify NASA key + real field names
pytest                                       # game-rule unit tests (no keys needed)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open http://localhost:8000/docs

## Security
- Never commit `.env`. The service-role key and NASA key stay server-side only.
- Game numbers are GAME DESIGN values, not NASA measurements.
- NASA DONKI data is labelled live / cached / archived / unavailable.
