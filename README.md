# House Finder

Multi-user Rightmove search & review web app.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate         # Windows
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://postgres:<pw>@<host>:5432/postgres"
export SUPABASE_JWT_SECRET="..."
export FRONTEND_URL="http://localhost:5173"

uvicorn app.main:app --reload --port 8000
```

Tests (offline):

```bash
cd backend && pytest tests/test_scraper.py tests/test_image_extractor.py
```

### Frontend

```bash
cd frontend
npm install

# frontend/.env.local
# VITE_API_URL=http://localhost:8000
# VITE_SUPABASE_URL=https://<project>.supabase.co
# VITE_SUPABASE_ANON_KEY=<anon-key>

npm run dev
```

## Deployment

1. Create a Supabase project; run `supabase_migration.sql` in the SQL editor.
2. Deploy via `render.yaml` (blueprint). Fill env vars in the Render dashboard:
   - Backend: `DATABASE_URL` (Supabase connection string), `SUPABASE_JWT_SECRET`, `FRONTEND_URL`
   - Frontend: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

## Legacy CLI

The original `main.py` / `review.py` / `config.yaml` / TinyDB scripts remain for standalone/CLI use.
