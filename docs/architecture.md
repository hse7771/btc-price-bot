# Architecture

This document details the architecture and core design decisions behind **BTC Price Bot**.

---

## Table of Contents

- [Key Components](#key-components)
- [Data Flow](#data-flow)
- [Design Decisions](#design-decisions)
- [Security Measures](#security-measures)
- [Rate Limits & Scalability](#rate-limits--scalability)
- [Future Improvements](#future-improvements)

---

## Key Components

- **Async Telegram Bot**  
  Built with `python-telegram-bot` (async version). Handles all user messages, commands, inline buttons, and 
  payments in an event-driven, non-blocking fashion.


- **Price Fetcher**  
  Retrieves Bitcoin prices from multiple APIs (CoinGecko and Blockchain.info) in parallel, using fallback logic and 
  a memory cache to minimize external calls and improve responsiveness.


- **Subscription Scheduler**  
  A custom async scheduler (using the bot’s job queue) manages both fixed UTC-interval (Base Plan) and 
  custom local-time (Personal Plan) subscriptions for price alerts.


- **Timezone Management**  
  Users can set their timezone via GPS location (`timezonefinder`) or manual input (`pytz`). Timezone data is stored 
  per-user and respected for all alerts.


- **Persistent Storage**  
  User settings, subscriptions, payments, and timezones are stored in SQLite, accessed asynchronously 
  with `aiosqlite`. The DB uses WAL mode for concurrency and retry logic to handle write locks safely.


- **Monetization Module**  
  Integrates YooMoney and Unlimit payment providers for upgrades and donations. Handles invoice generation, 
  expiry, payment confirmation, and subscription management.


---

## Data Flow

1. **User triggers action** via Telegram (message or button)
2. **Bot receives event** asynchronously; handler runs with proper context
3. **Price fetch**: If needed, triggers the fetcher, otherwise uses cached data
4. **Subscription check**: Scheduler fires on intervals, loads subscriptions from DB, sends price updates as needed
5. **Timezone resolution**: Each notification is sent in user’s local time, using stored settings
6. **Payments**: Upgrade and donation flows handled via provider APIs, updates tier/subscription status in DB

---

## Design Decisions

- **Asynchronous architecture:**  
  Enables fast, scalable response to user commands and background scheduling.


- **Multi-API fallback for BTC price fetching:**  
  Increases reliability and uptime by switching sources automatically if one fails.


- **SQLite with WAL and write-retry:**  
  Chosen for portability and concurrency. WAL mode allows simultaneous reads/writes, while retry logic prevents failed 
  writes due to locks.


- **In-memory price caching:**  
  Reduces API calls, improves responsiveness, and helps avoid third-party rate limiting.


- **Minimal dependencies for easy deployment:**  
  No extra services needed for most setups; everything can be run with Python and pulled repo, or just Docker.

---

## Security Measures

- **Token & API Key Management:**  
  All sensitive credentials (Telegram bot token, payment provider keys) are stored securely in environment variables 
  and loaded via `.env` files — never hardcoded in source or committed to version control.


- **SQL Injection Protection:**  
  All database queries use parameterized statements, eliminating the risk of SQL injection.


- **Payment Integrity:**  
  All incoming payment notifications are validated for correct amounts and currencies before user privileges are updated.


- **Rate Limiting:**  
  Caching and scheduled notification management prevent API abuse and denial-of-service conditions.


- **Error Handling:**  
  The bot handles external API failures gracefully, never exposing sensitive information to users.

---

## Rate Limits & Scalability

### Telegram Limits

- **Per-bot sending:** Telegram bots are allowed to send up to 30 messages per second.  
- **How we handle:** Our scheduler batches and spaces out notifications so the bot never exceeds this threshold, 
    ensuring reliability for up to 100–1000 users in production.
- **Beyond this scale:** For larger user bases, Telegram’s limit can be managed by buying telegram paid broadcasts, or 
    hosting own instance of Telegram Bot API server (all out of scope for this version but feasible as next steps).

### Hosting Free Tier limitations  
  
- **AWS Free Tier:** provides 750 instance hours/month—enough for one always-on micro instance.

### Price Data API Limits

- **Current setup:** We use a public API (blockchain.info or CoinGecko’s free endpoint), which does not enforce a 
    strict monthly cap.  
  - **1-minute polling:** Safe and efficient, since public APIs update prices once per minute anyway.
- **Fallback plan:** If forced to migrate to CoinGecko’s free API key (10,000 calls/month), the code is designed to 
    fall back to a minimum 5-minute interval for all users, with clear documentation and update for all subscribers.
- **Why not poll more often?**: With basic free API plans, it doesn’t make much sense, as updates typically arrive 
    only once per minute. As user base grows, migrating to paid API plans may be considered. 

### Caching & Robustness

- **Smart caching:** All price data is cached in-memory for 60 seconds, so user requests or notifications within this 
    window never trigger duplicate API calls, protecting us from API overuse and maintaining fresh data.
- **If cache is lost:** On restart, the bot simply fetches a new price on the next user or timer event.

---

_If you have a suggestion for improving limits or a use case requiring higher throughput, please open an issue or reach out!_


## Future Improvements

- **Paid API integration:** Use paid plans for more frequent updates or a larger user base.
- **Additional cryptocurrencies/currencies:** Allow tracking other coins or more fiat options.
- **More payment providers:** Integrate additional gateways for global coverage.
- **Self-hosted server (Telegram API) or sharded architecture:** For massive scale (10,000+ users).
- **Database upgrades:** If needed, swap SQLite for Postgres/MySQL to support more concurrent writes/reads.
