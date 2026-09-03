"""Create Better Auth tables in PostgreSQL for the Next.js frontend."""
import os
import sys


SQL = """
-- Better Auth tables for Next.js frontend
CREATE TABLE IF NOT EXISTS "user" (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL UNIQUE,
    "emailVerified" BOOLEAN NOT NULL DEFAULT false,
    image TEXT,
    "createdAt" TIMESTAMP NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "expiresAt" TIMESTAMP NOT NULL,
    token TEXT NOT NULL UNIQUE,
    "ipAddress" TEXT,
    "userAgent" TEXT,
    "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "accountId" TEXT NOT NULL,
    "providerId" TEXT NOT NULL,
    "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    "accessToken" TEXT,
    "refreshToken" TEXT,
    "idToken" TEXT,
    "accessTokenExpiresAt" TIMESTAMP,
    "refreshTokenExpiresAt" TIMESTAMP,
    scope TEXT,
    password TEXT
);

CREATE TABLE IF NOT EXISTS verification (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    "expiresAt" TIMESTAMP NOT NULL,
    "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_token ON session(token);
CREATE INDEX IF NOT EXISTS idx_session_userId ON session("userId");
CREATE INDEX IF NOT EXISTS idx_account_userId ON account("userId");
CREATE INDEX IF NOT EXISTS idx_verification_identifier ON verification(identifier);
"""


def main():
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("[better-auth] DATABASE_URL not set, skipping")
        return

    try:
        import psycopg2
    except ImportError:
        print("[better-auth] psycopg2 not available, trying subprocess...")
        # Fallback: use psql if psycopg2 isn't available
        os.system(f'echo "{SQL}" | psql "{database_url}"')
        return

    try:
        conn = psycopg2.connect(database_url, sslmode="require")
        cur = conn.cursor()
        cur.execute(SQL)
        conn.commit()
        print("[better-auth] Tables created/verified: user, session, account, verification")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[better-auth] Warning: {e}")


if __name__ == "__main__":
    main()
