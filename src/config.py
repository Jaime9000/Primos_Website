import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Stripe Configuration
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', 'pk_test_SM8IPFQBJgCFd0bnnwFuDfdU00AZqFLHPM')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_51FHHv5Hs5mN2cTmvFO2HxKPK75tHNJufHm9v2d4LmhLRL2pb2p1pJDObtF8x2BOXWK4jaTR0ZUUJoK6IUI23jpQD00RsPfAJd6')

# You'll get this after setting up webhooks
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '') 