import sqlite3
import json
import os
from pathlib import Path

DB_PATH = Path("usr/workdir/avender.db")

def seed_database():
    print("🌱 Seeding Avender Database...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenant_config (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalog_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, price REAL NOT NULL,
            description TEXT, metadata TEXT DEFAULT '{}' 
        )
    """)

    # Seed Tenant Config
    configs = {
        "admin_pin": "0000",
        "tradeName": "Burger House",
        "archetype": "retail",
        "agentName": "Sofía",
        "tone": "friendly"
    }
    for k, v in configs.items():
        cursor.execute("INSERT OR REPLACE INTO tenant_config (key, value) VALUES (?, ?)", (k, v))

    # Clear old catalog
    cursor.execute("DELETE FROM catalog_item")

    # Seed Catalog
    items = [
        ("Hamburguesa Clásica", 5.50, "Carne de res, queso, lechuga y tomate.", '{"calories": 800, "category": "food"}'),
        ("Hamburguesa Doble", 7.50, "Doble carne, doble queso, tocino.", '{"calories": 1200, "category": "food"}'),
        ("Papas Fritas", 2.50, "Porción grande de papas crujientes.", '{"calories": 400, "category": "sides"}'),
        ("Gaseosa Cola", 1.50, "Bebida azucarada 500ml.", '{"calories": 200, "category": "drinks"}')
    ]
    
    for item in items:
        cursor.execute("INSERT INTO catalog_item (name, price, description, metadata) VALUES (?, ?, ?, ?)", item)

    conn.commit()
    conn.close()
    print("✅ Database seeded successfully with 4 products and config!")

if __name__ == "__main__":
    seed_database()
