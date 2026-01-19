import os
import sqlite3
from datetime import datetime, timedelta, time as dtime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# AMAN: token diambil dari Environment Variable (jangan taruh token di file)
TOKEN = os.getenv("TOKEN")

DB_FILE = "duitcontrol.db"

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS tx(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER,
  ttype TEXT,
  amount INTEGER,
  note TEXT,
  tdate TEXT,
  ttime TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS setting(
  chat_id INTEGER PRIMARY KEY,
  limit_jajan INTEGER DEFAULT 0
)
""")
conn.commit()


def dnow(): return datetime.now().strftime("%Y-%m-%d")
def tnow(): return datetime.now().strftime("%H:%M")
def rp(n: int): return f"Rp {n}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Miftah’s DuitControl 💸\n"
        "Perintah:\n"
        "/limit 10000\n"
        "/masuk 50000 uang_saku\n"
        "/keluar 15000 kopi\n"
        "/hariini\n"
    )


async def limit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        limit = int(context.args[0])
        cur.execute("""
        INSERT INTO setting(chat_id, limit_jajan) VALUES(?,?)
        ON CONFLICT(chat_id) DO UPDATE SET limit_jajan=excluded.limit_jajan
        """, (chat_id, limit))
        conn.commit()
        await update.message.reply_text(f"✅ Limit jajan: {rp(limit)}")
    except:
        await update.message.reply_text("Format: /limit 10000")


async def masuk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        amt = int(context.args[0])
        note = " ".join(context.args[1:]) if len(context.args) > 1 else "-"
        cur.execute("INSERT INTO tx(chat_id,ttype,amount,note,tdate,ttime) VALUES(?,?,?,?,?,?)",
                    (chat_id, "IN", amt, note, dnow(), tnow()))
        conn.commit()
        await update.message.reply_text(f"➕ Masuk {rp(amt)} ({note})")
    except:
        await update.message.reply_text("Format: /masuk 50000 uang_saku")


async def keluar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        amt = int(context.args[0])
        note = " ".join(context.args[1:]) if len(context.args) > 1 else "-"
        cur.execute("INSERT INTO tx(chat_id,ttype,amount,note,tdate,ttime) VALUES(?,?,?,?,?,?)",
                    (chat_id, "OUT", amt, note, dnow(), tnow()))
        conn.commit()

        cur.execute("SELECT COALESCE(SUM(amount),0) FROM tx WHERE chat_id=? AND tdate=? AND ttype='OUT'",
                    (chat_id, dnow()))
        out_today = int(cur.fetchone()[0])

        cur.execute("SELECT limit_jajan FROM setting WHERE chat_id=?", (chat_id,))
        row = cur.fetchone()
        limit = int(row[0]) if row else 0

        msg = f"➖ Keluar {rp(amt)} ({note})\nTotal OUT hari ini: {rp(out_today)}"
        if limit > 0 and out_today > limit:
            msg += f"\n🔴 OVER {rp(out_today - limit)} (limit {rp(limit)})"
        else:
            msg += "\n🟢 Aman"
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("Format: /keluar 15000 kopi")


async def hariini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM tx WHERE chat_id=? AND tdate=? AND ttype='IN'",
                (chat_id, dnow()))
    tin = int(cur.fetchone()[0])
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM tx WHERE chat_id=? AND tdate=? AND ttype='OUT'",
                (chat_id, dnow()))
    tout = int(cur.fetchone()[0])
    await update.message.reply_text(
        f"📊 Hari ini ({dnow()})\n"
        f"➕ IN : {rp(tin)}\n"
        f"➖ OUT: {rp(tout)}\n"
        f"🏦 Sisa: {rp(tin - tout)}"
    )


def main():
    if not TOKEN:
        print("TOKEN belum diset. Set Environment Variable TOKEN dulu.")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("limit", limit_cmd))
    app.add_handler(CommandHandler("masuk", masuk_cmd))
    app.add_handler(CommandHandler("keluar", keluar_cmd))
    app.add_handler(CommandHandler("hariini", hariini_cmd))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
