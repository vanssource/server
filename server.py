from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from threading import Thread
from datetime import datetime, time
import yfinance as yf
from time import sleep
import os

app = FastAPI()

# Agar React bisa akses API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_FILE = "harga_saham_live.csv"
EXCEL_FILE = "daftar_saham.xlsx"

# === Cek jam kerja ===
def is_within_office_hours(start_time, end_time):
    now = datetime.now().time()
    return start_time <= now <= end_time

# Tentukan jam kerja
START_WORK = time(8, 58)
END_WORK   = time(17, 5)

# === Background scraper ===
def scrape_stocks():
    df_saham = pd.read_excel(EXCEL_FILE)
    symbols = df_saham["Code"].dropna().unique().tolist()
    df_result = pd.DataFrame(columns=["Code", "Last Price", "Updated At"])

    while True:
        if is_within_office_hours(START_WORK, END_WORK):
            print(f"=== Mulai scraping batch baru: {datetime.now()} ===")
            for sym in symbols:
                while True:  # retry sampai harga valid
                    try:
                        ticker = yf.Ticker(sym + ".JK")
                        price = ticker.fast_info.last_price
                        if price is not None:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df_result.loc[len(df_result)] = [sym, price, timestamp]
                            df_result.to_csv(CSV_FILE, index=False)
                            print(f"{sym}: {price} ({timestamp})")
                            break
                    except Exception as e:
                        print(f"{sym}: Error {e}, retry...")
                    sleep(2)
            print("Batch selesai, tunggu 30 detik...")
            sleep(30)  # delay antar batch
        else:
            print(f"Di luar jam kerja: {datetime.now().strftime('%H:%M:%S')}, stop loop")
            break  # langsung berhenti biar ga lanjut scraping

# === Jalankan scraper hanya kalau dalam jam kerja ===
if is_within_office_hours(START_WORK, END_WORK):
    Thread(target=scrape_stocks, daemon=True).start()
else:
    print("Deploy di luar jam kerja → scraper tidak dijalankan, pakai data lama CSV")

# === API endpoint ===
@app.get("/api/stocks")
def get_stocks():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        return df.to_dict(orient="records")
    return []
