# Aubrey Qualities Photography Platform

A Flask-based web application built for photographer Aubrey Qualities. It handles the full workflow from showcasing a portfolio to collecting payments via Stripe and sending automated email notifications to clients. Built to be straightforward to manage, easy to deploy, and professional enough to put in front of paying clients.

## What is this?

This is a custom-built platform designed specifically for a working photographer. Rather than piecing together third-party tools, everything lives in one place: the portfolio, the checkout flow, the client communications, and the configuration. It's built with simplicity in mind so that maintaining it doesn't become a second job.

## Tech Stack

| Layer | Tool |
|---|---|
| Backend | Python / Flask |
| Payments | Stripe (test + live) |
| Email | Gmail SMTP |
| Deployment | Configurable (local or hosted) |

## Features

Photographer portfolio showcase with a clean, manageable structure. Stripe payment integration with webhook support so payments are confirmed server-side rather than just relying on a browser redirect. Automated client email notifications for things like booking confirmations and payment receipts. Environment-based configuration so no credentials are ever hardcoded into the codebase. A configurable base URL that makes switching between development and production painless.

## Getting Started

### Prerequisites

Before running this locally, you'll need the following:

Python 3.9 or higher, pip, and Git installed on your machine. A [Stripe](https://dashboard.stripe.com) account, which is free to create and comes with a test mode so you can work without touching real money. A Gmail account with [App Passwords](https://myaccount.google.com/apppasswords) enabled, which requires 2FA to be turned on. The [Stripe CLI](https://stripe.com/docs/stripe-cli) is optional but genuinely useful if you want to test webhooks locally.

### 1. Clone the repo

```bash
git clone https://github.com/your-username/aubrey-qualities.git
cd aubrey-qualities
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

On Windows use `venv\Scripts\activate` instead.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your environment variables

Copy the example env file:

```bash
cp .env.example .env
```

Then open `.env` and fill in your values:

```env
SECRET_KEY=your-secret-key-here

# Stripe — grab these from https://dashboard.stripe.com/apikeys
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (Gmail SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your@gmail.com

# Photographer details
PHOTOGRAPHER_NAME=Aubrey Qualities
PHOTOGRAPHER_EMAIL=your@gmail.com

# Base URL — use localhost for development, your live domain for production
BASE_URL=http://localhost:5000
```

Important: never commit your `.env` file to Git. It should already be listed in `.gitignore` and that is where it should stay.

### 5. Run the app

```bash
flask run
```

Visit http://localhost:5000 and you should be up and running.

## Stripe Setup

### Getting your keys

Log in to your [Stripe Dashboard](https://dashboard.stripe.com), go to Developers then API Keys, and copy your Publishable key and Secret key into your `.env` file. In test mode Stripe won't charge anyone real money. You can simulate a payment using the test card number `4242 4242 4242 4242` with any future expiry date and any CVC.

### Setting up webhooks

Webhooks are how the app gets reliably notified after a payment goes through. Relying only on a browser redirect after checkout is not reliable enough for a real payment flow, so this is worth setting up properly.

For local development, use the Stripe CLI to forward events to your local server:

```bash
stripe listen --forward-to localhost:5000/webhook
```

The CLI will output a webhook signing secret starting with `whsec_`. Paste that into `STRIPE_WEBHOOK_SECRET` in your `.env`.

For production, go to your Stripe Dashboard, open Developers then Webhooks, and add a new endpoint pointing to:

```
https://your-domain.com/webhook
```

Select the events you need (at minimum `payment_intent.succeeded` and `checkout.session.completed`), then copy the signing secret Stripe gives you into your production environment variables.

## Email Setup

The app sends emails to clients automatically, things like booking confirmations, payment receipts, and delivery notifications. To get this working with Gmail you need to set up an App Password rather than using your actual account password.

Enable 2-Factor Authentication on your Google account if you haven't already. Then go to myaccount.google.com/apppasswords and create a new App Password for Mail. Copy the 16-character password it generates into `MAIL_PASSWORD` in your `.env`. App Passwords are completely separate from your main account password and can be revoked at any time without locking you out of anything.

## Environment Variables Reference

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session secret. Make it long and random in production |
| `STRIPE_PUBLISHABLE_KEY` | Stripe public key. Safe to use in frontend JavaScript |
| `STRIPE_SECRET_KEY` | Stripe secret key. Never expose this publicly under any circumstances |
| `STRIPE_WEBHOOK_SECRET` | Used to verify that incoming webhook events actually came from Stripe |
| `MAIL_SERVER` | SMTP server, smtp.gmail.com for Gmail |
| `MAIL_PORT` | SMTP port, 587 for TLS |
| `MAIL_USERNAME` | Your Gmail address |
| `MAIL_PASSWORD` | Your Gmail App Password, not your real account password |
| `MAIL_DEFAULT_SENDER` | The From address shown on outgoing emails |
| `PHOTOGRAPHER_NAME` | The photographer's name as it appears throughout the app |
| `PHOTOGRAPHER_EMAIL` | Contact email used in the app and in outgoing emails |
| `BASE_URL` | The app's base URL, used for Stripe return URLs and links in emails |

## Going Live

Before deploying to a live environment, work through this checklist:

Replace `SECRET_KEY` with a long randomly generated string. Swap the Stripe test keys (`pk_test_`, `sk_test_`) for your live keys (`pk_live_`, `sk_live_`). Set up a live Stripe webhook endpoint and update `STRIPE_WEBHOOK_SECRET` with the new signing secret. Update `BASE_URL` to your actual production domain. Double-check that your `.env` file is not committed to Git. Set all environment variables directly in your hosting platform's dashboard rather than uploading a `.env` file.

## Project Structure

```
aubrey-qualities/
├── app/
│   ├── __init__.py
│   ├── routes/
│   ├── models.py
│   ├── templates/
│   └── static/
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md


## Security Notes

Never expose your `STRIPE_SECRET_KEY` anywhere public. It has full access to your Stripe account and if it ever leaks, roll it immediately from your dashboard. Always verify webhook signatures using `STRIPE_WEBHOOK_SECRET` so the app only processes events that actually came from Stripe. Use HTTPS in production. Stripe requires it, and it protects your clients' payment information.

## Contributing

This is a private project. If you are collaborating on it, please work on feature branches and open pull requests rather than pushing directly to main.

## Contact

Built for Aubrey Qualities Photography.
Email: your@gmail.com

## License

Private project. Not for redistribution or reuse without permission.
