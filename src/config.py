import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Stripe Configuration
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', 'pk_test_SM8IPFQBJgCFd0bnnwFuDfdU00AZqFLHPM')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_51FHHv5Hs5mN2cTmvFO2HxKPK75tHNJufHm9v2d4LmhLRL2pb2p1pJDObtF8x2BOXWK4jaTR0ZUUJoK6IUI23jpQD00RsPfAJd6')

# Webhook secret - required for production, optional for development
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
if not STRIPE_WEBHOOK_SECRET:
    logger.warning('STRIPE_WEBHOOK_SECRET not set. Webhook signature verification will be disabled.')

# Email Configuration - Using dummy password for development
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'dummy_password_for_development')