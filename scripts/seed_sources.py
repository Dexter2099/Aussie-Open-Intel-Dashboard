#!/usr/bin/env python3
"""Seed initial source rows into the database."""
import os
import psycopg

SOURCES = [
    ("BOM Warnings", "https://www.bom.gov.au/", "Weather"),
    ("QFES Incidents", "https://www.qfes.qld.gov.au/", "Disaster"),
    ("Police Media", "https://mypolice.qld.gov.au/", "GovLE"),
    ("AIS Summary", "https://www.amsa.gov.au/", "Maritime"),
    ("CERT/ACSC Advisories", "https://www.cyber.gov.au/", "Cyber"),
]

def main() -> None:
    dsn = os.getenv("DATABASE_URL", "postgresql://aoidb:aoidb@localhost:5432/aoidb")
    inserted = 0
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for name, url, type_ in SOURCES:
                cur.execute("SELECT 1 FROM sources WHERE name=%s", (name,))
                if cur.fetchone():
                    continue
                cur.execute(
                    "INSERT INTO sources (name, url, type) VALUES (%s, %s, %s)",
                    (name, url, type_),
                )
                inserted += 1
        conn.commit()
    print(f"Inserted {inserted} sources.")

if __name__ == "__main__":
    main()
