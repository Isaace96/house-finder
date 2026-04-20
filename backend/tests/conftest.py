import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
