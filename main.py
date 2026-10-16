if q.data == "add":
    context.user_data["step"] = "asset"
    await q.message.reply_text("Введи актив: GBP/USD, EUR/USD або JP225")

elif q.data == "stats":
    row = DB.execute(
        "SELECT COUNT(*), COALESCE(SUM(result),0), "
        "COALESCE(SUM(result>0)*100.0/NULLIF(COUNT(*),0),0) "
        "FROM trades WHERE user=?", (user,)
    ).fetchone()
    await q.message.reply_text(
        f"📊 Угод: {row[0]}\nРезультат: {row[1]:.2f}R\nWin rate: {row[2]:.1f}%",
        reply_markup=menu()
    )

elif q.data == "list":
    rows = DB.execute(
        "SELECT asset,result,note FROM trades WHERE user=? ORDER BY rowid DESC LIMIT 10",
        (user,)
    ).fetchall()
    msg = "\n".join(f"{a}: {r:+.2f}R — {n}" for a,r,n in rows) or "Угод ще немає."
    await q.message.reply_text(msg, reply_markup=menu())
if step == "asset":
    if value.upper() not in ["GBP/USD", "EUR/USD", "JP225"]:
        await update.message.reply_text("Введи GBP/USD, EUR/USD або JP225")
        return
    context.user_data["asset"] = value.upper()
    context.user_data["step"] = "result"
    await update.message.reply_text("Введи результат у R, наприклад 2 або -1")

elif step == "result":
    try:
        context.user_data["result"] = float(value.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Введи число, наприклад 2 або -1")
        return
    context.user_data["step"] = "note"
    await update.message.reply_text("Напиши нотатку або помилку. Якщо немає — постав -")

elif step == "note":
    DB.execute(
        "INSERT INTO trades VALUES (?,?,?,?)",
        (update.effective_user.id, context.user_data["asset"],
         context.user_data["result"], value)
    )
    DB.commit()
    context.user_data.clear()
    await update.message.reply_text("✅ Угоду збережено!", reply_markup=menu())
