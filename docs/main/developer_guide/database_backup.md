# Database Backup and Restore

This guide explains how to create on-demand snapshots of the Postgres database and how to restore them to a local isolated database (a "branch") for inspection.

Prerequisites (macOS)
- Install Postgres client tools (pg_dump, pg_restore, psql):
  - brew install libpq
  - Add to PATH (zsh): echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc && exec zsh

Environment
- Never paste secrets into code or chat. Set the DB URL only in your shell session.
- Securely set SUPABASE_DB_URL:
  read -s "PGPASS?DB password: "; export SUPABASE_DB_URL="postgres://postgres:${PGPASS}@db.<your-project>.supabase.co:5432/postgres?sslmode=require"; unset PGPASS; echo

Create a snapshot
- From repo root:
  python3 scripts/backup_db.py
- Output files:
  - backups/YYYY-MM-DD_HHMMSS.dump (custom format, compressed)
  - backups/latest.dump (symlink to the latest snapshot if supported by FS)

Restore a snapshot (create a local "branch")
- Ensure a local Postgres is installed (Postgres.app or Homebrew postgresql@16).
- Create a local DB and restore:
  createdb my_branch_db
  python3 scripts/restore_db.py backups/latest.dump my_branch_db
- Inspect the data:
  psql postgres:///my_branch_db

Troubleshooting
- pg_dump not found: brew install libpq and ensure PATH is updated as above.
- Authentication failed: verify SUPABASE_DB_URL, remove any braces, URL-encode special characters in passwords if needed.
- Module import error: run CLI scripts from the repository root as shown above.

Implementation details
- Reusable logic: utils/db_backup.py
- CLI:
  - scripts/backup_db.py
  - scripts/restore_db.py

---

## Rychlý návod: bezpečná obnova PostgreSQL .dump do nového Supabase projektu

Cíl: rychle ověřit a obnovit zálohu bez rizika pro interní schémata Supabase (auth, realtime, storage, …). Obnovujeme jen vaše aplikační schéma (typicky `public`).

0) Předpoklady
- Supabase: založený nový projekt (vezmi Postgres connection URL z Project Settings → Database).
- macOS + Homebrew (doporučené): nainstalované klientské nástroje PostgreSQL.
- Soubor zálohy ve formátu custom/tar (přípona `.dump`).
- Bezpečnost: Po testu vždy rotuj DB heslo v Supabase (Project Settings → Database → Reset password).

1) Instalace klientských nástrojů (macOS)
```bash
brew install libpq
# přidat do PATH (zsh):
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```
Pokud používáš Linux/WSL, nainstaluj balíček s `pg_restore`/`psql` dle distribuce (např. `postgresql-client`).
Alternativa bez instalace: Docker varianta níže.

2) Připrav soubor a proměnné
- Neukládej dump na Desktop/Documents (macOS chrání přístup). Umísti ho například do `/tmp`:
```bash
cp /cesta/k/tvemu/<FILENAME>.dump /tmp/
```
- Nastav si connection URL (doplnit vlastní údaje):
```bash
export PGURL='postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require'
# vypneme timeouty během obnovy
export PGOPTIONS='-c statement_timeout=0'
```
- Pokud by síť řešila jen IPv6 a byl problém s připojením, přidej `hostaddr=<IPv4>`:
```bash
export PGURL='postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require&hostaddr=<DB_IPV4>'
```

3) Obnova jen aplikačních schémat (typicky `public`)
NEOBNOVUJ interní supabasí schémata (`auth`, `realtime`, `storage`, `vault`, `graphql*`, `pgbouncer`, `extensions`, `supabase_migrations`, `pg_*`, `information_schema`).
- Základní příkaz (jen `public`):
```bash
pg_restore --no-owner --no-acl --exit-on-error --verbose -j 4 \
  --schema=public \
  -d "$PGURL" /tmp/<FILENAME>.dump
```
- Máte-li i další vlastní schémata, přidejte vícekrát `--schema=...`, např.:
```bash
pg_restore --no-owner --no-acl --exit-on-error --verbose -j 4 \
  --schema=public --schema=app_private \
  -d "$PGURL" /tmp/<FILENAME>.dump
```
- Opakovaná obnova do stejné DB: přidejte jen pro svoje schéma `--clean --if-exists`.
- Nikdy nepouštějte `--clean` bez filtru `--schema=...`, ať nesmažete interní Supabase objekty.

4) Rychlá verifikace po obnově
```bash
# identita a spojení
psql "$PGURL" -c "select current_database(), inet_server_addr(), now();"

# seznam tabulek v public
psql "$PGURL" -c "
select table_name
from information_schema.tables
where table_schema='public' and table_type='BASE TABLE'
order by 1;"

# hrubý odhad počtu řádků (ze statistik)
psql "$PGURL" -c "
select relname as table, n_live_tup as approx_rows
from pg_stat_user_tables
order by approx_rows desc;"
```
Pár přesných kontrol (nahraď svými tabulkami):
```bash
psql "$PGURL" -c "select count(*) from public.nav_history;"
psql "$PGURL" -c "select count(*) from public.price_history;"
psql "$PGURL" -c "select count(*) from public.processed_transactions;"
psql "$PGURL" -c "select count(*) from public.binance_accounts;"
```
Rozšíření (pokud je schéma používá):
```bash
psql "$PGURL" -c 'create extension if not exists "uuid-ossp";'
psql "$PGURL" -c 'create extension if not exists "pgcrypto";'
```

5) Docker varianta (pokud nechceš instalovat klienta)
Pozn.: kontejnery často nemají IPv6 – v případě potíží použij `hostaddr=<IPv4>` v connection URL.
```bash
# jen public schéma
docker run --rm -e PGOPTIONS='-c statement_timeout=0' -v "$PWD:/backup" postgres:17 \
  pg_restore --no-owner --no-acl --exit-on-error --verbose -j 4 \
  --schema=public \
  -d "postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require" \
  /backup/<FILENAME>.dump
```
Pokud by `pg_restore` hlásil „unsupported version (1.16) in file header“, použij `postgres:17` (nebo novější) – dump je z PG17.

6) Nejčastější problémy a rychlé fixy
- Operation not permitted při čtení souboru (macOS Desktop/Documents): Přesuň dump do `/tmp` nebo dej Terminalu Full Disk Access.
- Chybí rozšíření (uuid-ossp, pgcrypto, …): vytvoř přes `CREATE EXTENSION` (viz výše) nebo v Supabase Database → Extensions.
- Kolize objektů při opakované obnově: přidej `--clean --if-exists`, ale jen s `--schema=` na tvá schémata.
- Síť/IPv6 (Network is unreachable): použij Homebrew klienta místo Dockeru, nebo přidej `hostaddr=<IPv4>`.
- Velké dumpy časují: máme `PGOPTIONS='-c statement_timeout=0'`; případně sniž `-j` nebo importuj po částech.

7) Bezpečnost po testu
- V Supabase resetuj DB password (Project Settings → Database → Reset password).
- Zvaž omezení přístupu (IP allowlist) a rotaci service role klíčů, pokud byly někde sdílené.

