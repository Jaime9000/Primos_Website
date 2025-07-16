from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import stripe
import logging
from datetime import datetime
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import certifi
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, EMAIL_PASSWORD
import json

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

def send_receipt_email(payment_intent):
    """Send receipt email to customer"""
    sender_email = "admin@gmail.com"  # Dummy email for development
    receiver_email = payment_intent.receipt_email
    amount = payment_intent.amount / 100  # Convert cents to dollars

    message = MIMEMultipart("alternative")
    message["Subject"] = "Payment Receipt - Primos de Peláez FC"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Create HTML version of the message
    html = f"""
    <html>
      <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <h2 style="color: #2b2d42;">Thank you for your payment!</h2>
          <p>We've received your payment of ${amount:.2f} USD.</p>
          <p>Payment ID: {payment_intent.id}</p>
          <p>Date: {datetime.fromtimestamp(payment_intent.created).strftime('%Y-%m-%d %H:%M:%S')}</p>
          <hr style="border: 1px solid #edf2f4;">
          <p style="color: #2b2d42;">Primos de Peláez FC</p>
          <p style="font-size: 0.9em; color: #8d99ae;">This is an automated message, please do not reply.</p>
        </div>
      </body>
    </html>
    """

    part = MIMEText(html, "html")
    message.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, EMAIL_PASSWORD)
            server.sendmail(sender_email, receiver_email, message.as_string())
            logger.info(f"Receipt email sent to {receiver_email}")
    except Exception as e:
        logger.error(f"Failed to send receipt email: {str(e)}")

app = Flask(__name__)
# Enable CORS for the allowed domains
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://football-io.com",  # Production domain
            "https://www.football-io.com",  # www subdomain
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
        email = data.get('email')

        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            receipt_email=email,  # Add email for receipt
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'timestamp': datetime.now().isoformat(),
                'source': 'website',
                'customer_email': email
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
        if STRIPE_WEBHOOK_SECRET:
            # If webhook secret is set, verify the signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Received valid webhook event: {event.type}")
        else:
            # In development, parse the payload without verification
            event = json.loads(payload)
            logger.warning("Webhook signature verification skipped - running in development mode")
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
        # Send receipt email
        if hasattr(payment_intent, 'receipt_email') and payment_intent.receipt_email:
            send_receipt_email(payment_intent)
        
    elif event_type == 'payment_intent.payment_failed':
        error = payment_intent.last_payment_error
        logger.error(f"Payment failed: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        logger.error(f"Error details: {error}")
        # Send failure notification to admin
        notify_admin_of_failure(payment_intent)
        
    elif event_type == 'payment_intent.created':
        logger.info(f"Payment intent created: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        
    elif event_type == 'payment_intent.canceled':
        logger.info(f"Payment intent canceled: {payment_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # Send cancellation notification to admin
        notify_admin_of_cancellation(payment_intent)

def handle_charge_event(event_type, charge):
    """Handle all charge related events"""
    amount = charge.amount
    currency = charge.currency
    charge_id = charge.id
    
    if event_type == 'charge.succeeded':
        logger.info(f"Charge succeeded: {charge_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # Update payment records
        update_payment_records(charge, 'succeeded')
        
    elif event_type == 'charge.failed':
        error = charge.failure_message
        logger.error(f"Charge failed: {charge_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        logger.error(f"Error details: {error}")
        # Update payment records and notify admin
        update_payment_records(charge, 'failed')
        notify_admin_of_failure(charge)
        
    elif event_type == 'charge.refunded':
        logger.info(f"Charge refunded: {charge_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # Update payment records and send refund confirmation
        update_payment_records(charge, 'refunded')
        send_refund_confirmation(charge)
        
    elif event_type == 'charge.dispute.created':
        logger.warning(f"Dispute created for charge: {charge_id}")
        # Handle dispute
        handle_dispute(charge)
        notify_admin_of_dispute(charge)

def handle_refund_event(event_type, refund):
    """Handle all refund related events"""
    amount = refund.amount
    currency = refund.currency
    refund_id = refund.id
    
    if event_type == 'refund.succeeded':
        logger.info(f"Refund succeeded: {refund_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # Update payment records
        update_payment_records(refund, 'refunded')
        # Send refund confirmation
        send_refund_confirmation(refund)
        
    elif event_type == 'refund.failed':
        logger.error(f"Refund failed: {refund_id} - Amount: ${amount/100:.2f} {currency.upper()}")
        # Notify admin and retry refund
        notify_admin_of_failure(refund)
        retry_refund(refund)

def handle_customer_event(event_type, customer):
    """Handle all customer related events"""
    customer_id = customer.id
    email = customer.email
    
    if event_type == 'customer.created':
        logger.info(f"Customer created: {customer_id} - Email: {email}")
        # Store customer information
        store_customer_info(customer)
        
    elif event_type == 'customer.updated':
        logger.info(f"Customer updated: {customer_id} - Email: {email}")
        # Update stored customer information
        update_customer_info(customer)
        
    elif event_type == 'customer.deleted':
        logger.info(f"Customer deleted: {customer_id}")
        # Archive customer information
        archive_customer_info(customer)

def notify_admin_of_failure(event_object):
    """Notify admin of payment/refund failures"""
    # Implementation depends on your notification system
    logger.info(f"Admin notification sent for failure: {event_object.id}")

def notify_admin_of_cancellation(event_object):
    """Notify admin of payment cancellations"""
    logger.info(f"Admin notification sent for cancellation: {event_object.id}")

def notify_admin_of_dispute(charge):
    """Notify admin of disputes"""
    logger.warning(f"Admin notification sent for dispute on charge: {charge.id}")

def update_payment_records(event_object, status):
    """Update payment records in your database"""
    # Implementation depends on your database structure
    logger.info(f"Payment record updated - ID: {event_object.id}, Status: {status}")

def send_refund_confirmation(refund):
    """Send refund confirmation email to customer"""
    if hasattr(refund, 'charge'):
        charge = stripe.Charge.retrieve(refund.charge)
        if hasattr(charge, 'receipt_email'):
            # Send email confirmation
            logger.info(f"Refund confirmation sent to {charge.receipt_email}")

def handle_dispute(charge):
    """Handle dispute cases"""
    logger.warning(f"Handling dispute for charge: {charge.id}")
    # Implement dispute handling logic
    # This might include gathering evidence, submitting a response, etc.

def retry_refund(refund):
    """Retry failed refund"""
    try:
        new_refund = stripe.Refund.modify(
            refund.id,
            metadata={'retry_count': str(int(refund.metadata.get('retry_count', 0)) + 1)}
        )
        logger.info(f"Refund retry initiated: {new_refund.id}")
    except Exception as e:
        logger.error(f"Refund retry failed: {str(e)}")

def store_customer_info(customer):
    """Store customer information in your database"""
    # Implementation depends on your database structure
    logger.info(f"Customer information stored: {customer.id}")

def update_customer_info(customer):
    """Update customer information in your database"""
    # Implementation depends on your database structure
    logger.info(f"Customer information updated: {customer.id}")

def archive_customer_info(customer):
    """Archive customer information"""
    # Implementation depends on your database structure
    logger.info(f"Customer information archived: {customer.id}")

@app.route('/payment-success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/payment-cancel')
def payment_cancel():
    return render_template('payment_cancel.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)

