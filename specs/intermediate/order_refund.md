Process: Order Refund (Digital Goods)

Goal
- Refund a customer for a digital purchase when they meet policy criteria.

Triggers
- Customer email with subject containing "refund" OR support ticket tagged "refund".

Inputs
- order_id (string), customer_id (string), reason (free text), purchase_date (date), payment_method (enum: card, paypal), price (number).

Policy
- Only within 30 days of purchase.
- If download_count > 0 and reason == "accidental purchase", require manager sign-off.
- If fraud_flag == true -> escalate and STOP (no refund).

Steps (high-level)
1) Retrieve order + account.
2) Policy check (30-day window, fraud).
3) If needs approval -> request + wait (max 24h).
4) Issue refund via payment provider.
5) Notify customer with templated email.
6) Log outcome to audit store.

Success
- Payment provider confirms refund; audit record exists; customer email sent.

Failure
- Any step produces error -> log with reason; do not issue refund.

Clarifications
- Approval required but approver role not specified.
- Customer notification template/content not specified.