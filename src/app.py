from flask import Flask, render_template, jsonify, request
import stripe
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY

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
        )
        return jsonify({
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/payment-success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/payment-cancel')
def payment_cancel():
    return render_template('payment_cancel.html')

if __name__ == '__main__':
    app.run(debug=True)

