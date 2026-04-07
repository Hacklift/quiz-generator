# quiz-generator

Generate quizzes in a particular field.

## Local setup

Install dependencies for the client and server, then provide the required environment variables for both apps.

## Stripe test mode setup

The paid plan flow now uses Stripe Checkout in test mode.

Server env:

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_MONTHLY=price_...
STRIPE_PRICE_ID_YEARLY=price_...
FRONTEND_BASE_URL=http://localhost:3000
```

Install the server dependency update, start the API, and forward Stripe webhooks locally:

```bash
cd server
pip install -r requirements.txt
stripe listen --forward-to localhost:8000/api/billing/webhook
```

Use Stripe sandbox price IDs for the monthly and yearly plans, then test Checkout with card `4242 4242 4242 4242`.

To let customers update payment methods, cancel, or switch plans, configure the Stripe Billing Portal in your Stripe sandbox and use the in-app "Manage Subscription" action after a customer has completed Checkout.

## Run

Legacy Streamlit entrypoint:

```bash
streamlit run quiz.py
```
