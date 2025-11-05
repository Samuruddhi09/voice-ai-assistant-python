from flask import Flask, request, jsonify, render_template
import os, subprocess, webbrowser
from urllib.parse import quote
import yt_dlp
import pytz
from datetime import datetime
import tzlocal
from stock_model import get_stock_recommendation
from flask import request, jsonify, render_template

# ✅ Import trading logic
from gold import get_gold_signal, get_gold_candles

app = Flask(__name__)

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# ================= FRONTEND ROUTES =================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/notes")
def notes():
    return render_template("notes.html")

@app.route("/todo")
def todo():
    return render_template("todo.html")

@app.route("/chat-history")
def chat_history():
    return render_template("chat-history.html")

@app.route("/schedule")
def schedule():
    return render_template("schedule.html")

@app.route("/reminders")
def reminders():
    return render_template("reminders.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/charts")
def charts():
    return render_template("charts.html")

# STOCK PAGE (UI + Predictions)
@app.route("/stock", methods=["GET", "POST"])
def stock_page():
    results = None
    
    if request.method == "POST":
        duration = request.form["duration"]
        capital = int(request.form["capital"])
        risk = request.form["risk"]
        top_n = int(request.form["top_n"])

        raw = get_stock_recommendation(duration, capital, risk, top_n)

        if hasattr(raw, "to_dict"):
            raw = raw.to_dict(orient="records")

        results = []
        for r in raw:
            results.append({
                "Stock": r.get("Stock", "N/A"),
                "Price": r.get("Price", 0),
                "Expected Return (%)": r.get("Expected Return (%)", 0),
                "Action": "BUY" if r.get("Expected Return (%)", 0) > 0 else "AVOID"
            })

    return render_template("stock.html", results=results)

#  JSON API for Bunny voice/Web requests
@app.route("/api/stock-advice")
def stock_advice_api():
    duration = request.args.get("duration", "1month")
    capital = int(request.args.get("capital", 20000))
    risk = request.args.get("risk", "low")
    top_n = int(request.args.get("top_n", 5))

    raw = get_stock_recommendation(duration, capital, risk, top_n)

    if hasattr(raw, "to_dict"):
        raw = raw.to_dict(orient="records")

    return jsonify(raw)

# ================= API ROUTES =================

@app.post("/launch-app")
def launch_app():
    data = request.get_json()
    app_name = data.get("app", "")

    known_apps = {
        "calculator": "calc.exe",
        "notepad": "notepad.exe",
        "chrome": chrome_path,
        "cmd": "cmd.exe",
        "paint": "mspaint.exe",
        "brave": "brave.exe",
    }

    app_to_run = known_apps.get(app_name.lower(), app_name)

    try:
        os.startfile(app_to_run)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.get("/youtube/search")
def search_youtube():
    query = request.args.get("q", "")
    try:
        url = f"https://www.youtube.com/results?search_query={quote(query)}"
        os.startfile(url)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.get("/youtube/play")
def play_youtube_video():
    query = request.args.get("q", "")
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'default_search': 'ytsearch1',
            'forceurl': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info and info['entries']:
                video_url = info['entries'][0]['webpage_url']
                os.startfile(video_url)
                return jsonify({"success": True, "url": video_url})
            else:
                return jsonify({"success": False, "error": "No video found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.get("/time")
def get_current_time():
    try:
        local_tz = tzlocal.get_localzone()
        now = datetime.now(local_tz)
        return jsonify({"time": now.strftime('%Y-%m-%d %H:%M:%S')})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.get("/time/<country>")
def get_time_by_country(country):
    zone_map = {
        "new york": "America/New_York",
        "london": "Europe/London",
        "tokyo": "Asia/Tokyo",
        "sydney": "Australia/Sydney",
        "mumbai": "Asia/Kolkata",
        "dubai": "Asia/Dubai"
    }
    try:
        tz = zone_map.get(country.lower(), "UTC")
        now = datetime.now(pytz.timezone(tz))
        return jsonify({"time": now.strftime('%Y-%m-%d %H:%M:%S')})
    except:
        return jsonify({"error": "invalid location"})

@app.get("/trading-session")
def get_trading_session():
    utc_now = datetime.utcnow().hour
    if 0 <= utc_now < 6:
        session = "Sydney Session"
    elif 6 <= utc_now < 9:
        session = "Tokyo Session"
    elif 9 <= utc_now < 17:
        session = "London Session"
    elif 17 <= utc_now < 22:
        session = "New York Session"
    else:
        session = "After-hours / Low liquidity"
    return jsonify({"session": session})

# GOLD SIGNAL API
@app.get("/gold-signal")
def gold_signal():
    result = get_gold_signal()
    return jsonify(result)

# GOLD CHART DATA (MT5)
@app.get("/gold-chart")
def gold_chart():
    df = get_gold_candles()
    if df is None:
        return jsonify({"success": False, "error": "MT5 not running"}), 500

    return jsonify({
        "success": True,
        "data": df.reset_index().to_dict(orient="records")
    })

# ================= RUN APP =================
if __name__ == "__main__":
    app.run(port=5000, debug=True)
