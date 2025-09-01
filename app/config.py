import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-super-secreta")

    # Usa una de dos: DATABASE_URL o las partes
    DATABASE_URL = os.getenv("DATABASE_URL")  # ej: postgres://user:pwd@host:5432/dbname

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME","postgres")
    DB_USER = os.getenv("DB_USER","edgargarcia")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
