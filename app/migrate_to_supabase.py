"""
Script Migrasi Otomatis dari bank.db SQLite Lokal ke Supabase Cloud Database.
Mengunggah seluruh korpus lokal secara aman & efisien dalam batch 500 item.
"""
import os
import sys
import time
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from engine.supabase_client import save_to_corpus_bank_supabase, is_supabase_configured

BANK_DB_PATH = os.path.join(BASE_DIR, "corpus_bank", "bank.db")

def run_migration():
    print("="*70)
    print("MIGRASI KORPUS LOKAL (bank.db) -> SUPABASE CLOUD DATABASE")
    print("="*70)
    
    if not is_supabase_configured():
        print("[!] Supabase belum dikonfigurasi. Periksa app/.env")
        return
        
    if not os.path.exists(BANK_DB_PATH):
        print(f"[!] File {BANK_DB_PATH} tidak ditemukan.")
        return
        
    conn = sqlite3.connect(BANK_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM corpus")
    total_items = cur.fetchone()[0]
    print(f"[*] Total sumber di local bank.db: {total_items} item.")
    
    batch_size = 500
    migrated_count = 0
    start_time = time.time()
    
    cur.execute("SELECT url, text FROM corpus")
    
    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
            
        corpus_chunk = {u: t for u, t in rows if t and len(t) > 150}
        if corpus_chunk:
            success = save_to_corpus_bank_supabase(corpus_chunk)
            if success:
                migrated_count += len(corpus_chunk)
                pct = (migrated_count / total_items) * 100
                elapsed = time.time() - start_time
                print(f"[{pct:5.1f}%] Migrasi {migrated_count}/{total_items} sumber... ({elapsed:.1f}s)")
                
    conn.close()
    print("="*70)
    print(f"[SUCCESS] Migrasi selesai! Total {migrated_count} sumber berhasil diunggah ke Supabase.")
    print("="*70)

if __name__ == "__main__":
    run_migration()
