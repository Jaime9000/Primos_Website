from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import stripe
import logging
from datetime import datetime
import certifi
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
# Enable CORS for the Squarespace domain
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://primosdepelaez.com",  # Main domain
            "https://www.primosdepelaez.com",  # www subdomain
            "http://localhost:5001"  # Local development
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-Requested-With", "Authorization"]
    }
})

# Configure Stripe with SSL certificate
stripe.api_key = STRIPE_SECRET_KEY
stripe.verify_ssl_certs = True
stripe.ca_bundle_path = certifi.where()

@app.after_request
def add_security_headers(response):
    # Add security headers
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

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

        # Configure Stripe client for this request
        stripe.default_http_client = stripe.http_client.RequestsClient(verify=False)
        
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

    if not sig_header:
        logger.error("No Stripe signature header found")
        return jsonify({'error': 'No Stripe signature header'}), 400

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Received valid webhook event: {event.type}")
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}")
        return jsonify({'error': 'Unexpected error'}), 500

    try:
        # Handle the event
        if event.type.startswith('payment_intent.'):
            payment_intent = event.data.object
            handle_payment_intent_event(event.type, payment_intent)
        
        elif event.type.startswith('charge.'):
            charge = event.data.object
            handle_charge_event(event.type, charge)
            
        elif event.type.startswith('refund.'):
            refund = event.data.object
            handle_refund_event(event.type, refund)
            
        elif event.type.startswith('customer.'):
            customer = event.data.object
            handle_customer_event(event.type, customer)
            
        else:
            logger.info(f"Unhandled event type: {event.type}")
            
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error processing webhook event {event.type}: {str(e)}")
        return jsonify({'error': 'Error processing webhook'}), 500

def handle_payment_intent_event(event_type, payment_intent):
    """Handle all payment intent related events"""
    amount = payment_intent.amount
    currency = payment_intent.currency
    payment_id = payment_intent.id
    
    if event_type == 'payment_intent.succeeded':
        logger.info(f"Payment succeeded: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # TODO: Implement success actions (email, database update, etc.)
        
    elif event_type == 'payment_intent.payment_failed':
        error = payment_intent.last_payment_error
        logger.error(f"Payment failed: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        logger.error(f"Error details: {error}")
        # TODO: Implement failure handling (notification, retry logic, etc.)
        
    elif event_type == 'payment_intent.created':
        logger.info(f"Payment intent created: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        
    elif event_type == 'payment_intent.canceled':
        logger.info(f"Payment intent canceled: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # TODO: Implement cancellation handling

def handle_charge_event(event_type, charge):
    """Handle all charge related events"""
    amount = charge.amount
    currency = charge.currency
    charge_id = charge.id
    
    if event_type == 'charge.succeeded':
        logger.info(f"Charge succeeded: {charge_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # TODO: Implement success actions
        
    elif event_type == 'charge.failed':
        error = charge.failure_message
        logger.error(f"Charge failed: {charge_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        logger.error(f"Error details: {error}")
        # TODO: Implement failure handling
        
    elif event_type == 'charge.refunded':
        logger.info(f"Charge refunded: {charge_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # TODO: Implement refund handling
        
    elif event_type == 'charge.dispute.created':
        logger.warning(f"Dispute created for charge: {charge_id}")
        # TODO: Implement dispute handling

def handle_refund_event(event_type, refund):
    """Handle all refund related events"""
    amount = refund.amount
    currency = refund.currency
    refund_id = refund.id
    
    if event_type == 'refund.succeeded':
        logger.info(f"Refund succeeded: {refund_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # TODO: Implement refund success actions
        
    elif event_type == 'refund.failed':
        logger.error(f"Refund failed: {refund_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # TODO: Implement refund failure handling

def handle_customer_event(event_type, customer):
    """Handle all customer related events"""
    customer_id = customer.id
    
    if event_type == 'customer.created':
        logger.info(f"Customer created: {customer_id}")
        # TODO: Implement customer creation handling
        
    elif event_type == 'customer.updated':
        logger.info(f"Customer updated: {customer_id}")
        # TODO: Implement customer update handling
        
    elif event_type == 'customer.deleted':
        logger.info(f"Customer deleted: {customer_id}")
        # TODO: Implement customer deletion handling

@app.route('/payment-success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/payment-cancel')
def payment_cancel():
    return render_template('payment_cancel.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)

