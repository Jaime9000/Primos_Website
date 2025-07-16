import os

# Stripe Configuration
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', 'your_stripe_public_key')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'your_stripe_secret_key') 