# Monetization & Payment System

This document describes the subscription plans, payment providers, upgrade/donation flows, and logic behind **BTC Price Bot’s** monetization features.

---

## Subscription Tiers

| Tier  | Personal Plans | Min Interval | Priority Support |
|-------|:--------------:|:------------:|:----------------:|
| Free  |       1        |    5 min     |        –         |
| Pro   |       3        |    1 min     |        ✅         |
| Ultra |       5        |    1 min     |        ✅         |

---

## Payment Providers

BTC Price Bot integrates two payment gateways for global reach and demonstration purposes:

- **YooMoney**  
  - Supports Russian Ruble (RUB) payments  
  - Used for both upgrades and donations  
  - Demo/test and production flows supported

- **Ammer Pay**  
  - Supports international (USD/EUR/etc.) payments  
  - Used for upgrades and donations  
  - Currently operates in test/demo mode

> **Sandbox mode:** All payment flows can be tested without real transactions in demo mode for portfolio/demonstration purposes.

---

## Payment Handling

- **Payment logic** is modular—easily extensible for more providers in the future.
- **Downgrade/expiry:** When a paid plan expires, user is downgraded to Free tier with a notification and adjusted limits.
- **Multiple successful payments:** All payments (even for the same tier) are recorded with a timestamp for audit and support.
