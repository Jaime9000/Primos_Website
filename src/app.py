from flask import Flask, render_template, jsonify, request
import stripe
import logging
from datetime import datetime
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('payments.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('primos_payments')

app = Flask(__name__)

# Configure Stripe
stripe.api_key = STRIPE_SECRET_KEY

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/family')
def family():
    return render_template('family.html')

@app.route('/revolution')
def revolution():
    return render_template('revolution.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/payment')
def payment():
    return render_template('payment.html', stripe_public_key=STRIPE_PUBLIC_KEY)

@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
    try:
        data = request.json
        amount = data.get('amount', 1000)  # Amount in cents, default $10.00

        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'timestamp': datetime.now().isoformat(),
                'source': 'website'
            }
        )
        
        logger.info(f"Created payment intent for ${amount/100:.2f}")
        return jsonify({
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return jsonify(error=str(e)), 403

@app.route('/webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return jsonify({'error': str(e)}), 400

    # Handle the event
    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        amount = payment_intent.amount
        currency = payment_intent.currency
        payment_id = payment_intent.id
        
        logger.info(f"Payment succeeded: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        
        # Here you could:
        # 1. Send confirmation email
        # 2. Update database
        # 3. Trigger any follow-up processes
        
    elif event.type == 'payment_intent.payment_failed':
        payment_intent = event.data.object
        amount = payment_intent.amount
        currency = payment_intent.currency
        payment_id = payment_intent.id
        error = payment_intent.last_payment_error
        
        logger.error(f"Payment failed: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        logger.error(f"Error details: {error}")
        
    elif event.type == 'payment_intent.created':
        payment_intent = event.data.object
        amount = payment_intent.amount
        currency = payment_intent.currency
        payment_id = payment_intent.id
        
        logger.info(f"Payment intent created: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        
    elif event.type == 'charge.succeeded':
        charge = event.data.object
        amount = charge.amount
        currency = charge.currency
        charge_id = charge.id
        
        logger.info(f"Charge succeeded: {charge_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        
    elif event.type == 'charge.failed':
        charge = event.data.object
        amount = charge.amount
        currency = charge.currency
        charge_id = charge.id
        error = charge.failure_message
        
        logger.error(f"Charge failed: {charge_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        logger.error(f"Error details: {error}")
    
    else:
        logger.info(f"Unhandled event type: {event.type}")

    return jsonify({'status': 'success'})

@app.route('/payment-success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/payment-cancel')
def payment_cancel():
    return render_template('payment_cancel.html')

if __name__ == '__main__':
    app.run(debug=True)

