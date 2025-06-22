<a name="readme-top"></a>

<!-- SHIELDS -->
<!-- Add badges here later -->

<!-- PROJECT LOGO -->
<p align="center" style="margin:0; padding:0; line-height: 1;">
    <a href="https://t.me/BTCPricePriceBot">
        <img src="images/logo.png" alt="Logo" width="120" height="120" />
    </a>
  <br><br>
  <strong style="font-size: 2.2em;">₿ BTC Price Bot</strong>
</p>

  <p align="center">
    A professional, production-ready <strong>Telegram bot</strong> that delivers real-time Bitcoin price tracking, <br />
    personalized alerts, smart caching, and seamless upgrade options.
    <br /><br />
    <a href="#-demo"><strong>🎥 View Demo</strong></a>
    &nbsp;&nbsp;•&nbsp;&nbsp;
    <a href="https://github.com/hse7771/btc-price-bot/issues/new?labels=bug&template=bug-report---.md"><strong>🐞 Report Bug</strong></a>
    &nbsp;&nbsp;•&nbsp;&nbsp;
    <a href="https://github.com/hse7771/btc-price-bot/issues/new?labels=enhancement&template=feature-request---.md"><strong>💡 Request Feature</strong></a>
  </p>


---

## 📋 Table of Contents

- [📌 Overview](#-overview)
  - [🔑 Core Functionality](#-core-functionality)
  - [💡 Why This Project?](#-why-this-project)
  - [🎥 Demo](#-demo)
- [🛠️ Built With](#-built-with)
- [🚀 Getting Started](#-getting-started)
  - [🔗 Live Demo](#-live-demo)
  - [⚙️ Local Setup](#-local-setup)
    - [🐳 Docker](#-docker)
    - [🐍 Plain Python](#-plain-python)
- [📘 Documentation](#-documentation)
  - [🧠 Architecture](#-documentation)
  - [⌨️ Commands](#-documentation)
  - [🚢 Deployment](#-documentation)
  - [💸 Monetization](#-documentation)
  - [🌳 Git Workflow](#-documentation)
- [🤝 Contributing](#-contributing)
  - [🔁 Contribution Workflow](#-contribution-workflow)
  - [✅ Guidelines](#-guidelines)
  - [🛠️ Developer Standards](#-developer-standards)
- [📄 License](#-license)
- [📬 Contact](#-contact)

---

## 📌 Overview

**BTC Price Bot** is a robust, production-ready Telegram bot that provides users with live Bitcoin (BTC) price 
information, customizable currency preferences, and subscription-based price alerts. It combines asynchronous 
programming techniques with a user-friendly, interactive chat interface and a scalable backend architecture.

### 🔑 Core Functionality

- 📈 Fetches BTC prices from multiple APIs with fallback logic (CoinGecko and Blockchain.info) ensuring reliability
    and freshness  
- 💱 Supports user-selected currency filtering with inline multi-select toggle buttons  
- 🔔 Implements two subscription models for automated price updates:  
  - **Base Plan**: Standard UTC-based intervals (15, 30, 60, 240, 1440 minutes)  
  - **Personal Plan**: Fully customizable local-time based alerts respecting user timezone
- 🌍 Timezone management using both GPS-based detection and manual offset entry for accurate local notifications  
- 💳 Monetization via tiered subscription plans (Pro, Ultra) integrated with YooMoney and Ammer Pay payment providers  
- ☕ Donation support with flexible tipping options to help sustain the bot’s infrastructure  

### 💡 Why This Project?

BTC Price Bot is more than just a price tracker — it is a showcase of:

- Modern asynchronous Python application design  
- Real-world integration of payment processing and subscription management  
- Complex timezone-aware scheduling in a global user environment  
- Clean, maintainable, and well-documented codebase suitable for production deployment  
- Strong developer discipline in version control and code quality practices  
- Managing a full production deployment pipeline, including Docker containerization and environment configuration 

### 🎥 Demo

[![Demo Video](./images/preview.png)](https://youtu.be/zHaG3XCzhN4)

> Click the image to watch the demo on YouTube.

**Demo Notes:**
- The demo uses the **Smart Glocal** payment provider (since Ammer Pay does not provide test card numbers)\
  _Note: Smart Glocal will not be used in production, as it does not support self-employed status._
- **Timecodes** are included in the video description for quick navigation to main features.

Together, these facets reflect a professional approach to software development — from initial design and 
coding standards to scalable deployment and maintenance. This project demonstrates comprehensive skills 
in backend development, API integration, and system design.

---

## 🛠️ Built With

* [![Python][Python-badge]][Python-url]
* [![Telegram][Telegram-badge]][Telegram-url]
* [![PTB][PTB-badge]][PTB-url]
* [![aiohttp][Aiohttp-badge]][Aiohttp-url]
* [![SQLite][SQLite-badge]][SQLite-url]
* [![aiosqlite][Aiosqlite-badge]][Aiosqlite-url]
* [![timezonefinder][Timezonefinder-badge]][Timezonefinder-url]
* [![pytz][Pytz-badge]][Pytz-url]
* [![Docker][Docker-badge]][Docker-url]
* [![pre-commit][Precommit-badge]][Precommit-url]
* [![flake8][Flake8-badge]][Flake8-url]
* [![isort][Isort-badge]][Isort-url][![BlackStyle][BlackStyle-badge]][Black-url]
* [![autopep8][Autopep8-badge]][Autopep8-url]

---

## 🚀 Getting Started

### 🔗 Live Demo

👉 [Launch the Bot on Telegram](https://t.me/BTCPricePriceBot)

> You can check BTC prices, choose your currencies, and test both subscription types (base + personal plans).  
> Upgrade and donation features are enabled in sandbox/test mode.

### ⚙️ Local Setup

> Make sure you have **Python 3.10+** and `pip` installed.

  **Clone the repo**
  ```bash
  git clone https://github.com/hse7771/btc-price-bot.git
  cd btc-price-bot
  ```

#### 🐳 Docker

> This method isolates dependencies and is ideal for deployment or testing.

1. **Create and fill in your `.env` file**
    ```bash
    cp .env.example .env  # You can use this template
    ```

    Then set your environment variables inside `.env`:
    ```
    TELEGRAM_BOT_TOKEN=your_token
    UKASSA_TEST_TOKEN=...
    AMMER_PAY_TEST_TOKEN=...
    ```

2. **Build the Docker image**
    ```bash
    docker compose build
    ```

3. **Start the bot**
   ```bash
   docker compose up -d
   ```

> The `.env` file is used inside the container to load credentials.

#### 🐍 Plain Python

1. **Create a virtual environment**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure environment**
    ```bash
    cp .env.example .env  # Copy the example file and fill in your tokens
    ```

    Set the following values inside `.env`:

    ```
    TELEGRAM_BOT_TOKEN=your_token
    UKASSA_TEST_TOKEN=...
    AMMER_PAY_TEST_TOKEN=...
    ```

4. **Run the bot**
    ```bash
    python btc_price_bot.py
    ```
   
---

## 📘 Documentation

The following documentation is available in the [`docs/`](docs/) directory:

- **[Architecture](docs/architecture.md):** In-depth system architecture — async flow, scheduling, caching, database schema, diagrams.
- **[Commands](docs/commands.md):** Bot command reference — all user commands, button actions, and UX flows.
- **[Deployment](docs/deployment.md):** Deployment guide — Docker, local setup, environment variables, production tips.
- **[Monetization](docs/monetization.md):** Payment & subscription logic — tiers, provider integration, upgrade/donation flows.
- **[Git Workflow](https://github.com/hse7771/git-workflow):** Git standards — commit conventions, branch strategy, merge/rebase, troubleshooting.

---

## 🤝 Contributing

Contributions are welcome and appreciated! 🎉

If you'd like to improve this project — whether by fixing a bug, suggesting a feature, or refining 
the documentation — please follow these steps:

### 🔁 Contribution Workflow

1. Fork the repo and create a feature branch  
   ```bash
   git checkout -b feature/my-feature
   ```

2. Commit using [Conventional Commits](https://github.com/hse7771/git-workflow)
   
    Example:  
   ```bash
   git commit -m "feat(price): add support for new currency"
   ```

3. Run pre-commit hooks before pushing  
   ```bash
   pre-commit run --all-files
   ```

4. Push to your fork and open a pull request with a clear description

### ✅ Guidelines

- See established [Git Workflow Guide](https://github.com/hse7771/git-workflow).
- Follow existing code style and structure
- Keep PRs focused and scoped — one topic per PR
- Be respectful in code reviews and discussions

### 🛠️ Developer Standards

This project uses:

- `flake8` for linting
- `isort` (Black-style imports) + `autopep8` for formatting
- &nbsp;Pre-commit hooks (`.pre-commit-config.yaml`) to automate checks

> Tip: All commits are expected to pass formatting + lint checks before submission.


---

## 📄 License

<!-- MIT license with link to LICENSE -->

---

## 📬 Contact

[btcBotTg@proton.me](mailto:btcBotTg@proton.me)  
[GitHub](https://github.com/hse7771)  
[LinkedIn](https://www.linkedin.com/in/kirill-bukhteev-22154428a/)  




<!-- Badge Definitions -->
[Python-badge]: https://img.shields.io/badge/Python-3.11.5-blue?logo=python&logoColor=white&style=for-the-badge
[Python-url]: https://www.python.org/

[Telegram-badge]: https://img.shields.io/badge/Telegram%20Bot-Async-blueviolet?logo=telegram&style=for-the-badge
[Telegram-url]: https://core.telegram.org/bots/api

[PTB-badge]: https://img.shields.io/badge/python--telegram--bot-21.10-blue?style=for-the-badge&logo=python
[PTB-url]: https://docs.python-telegram-bot.org/

[Aiohttp-badge]: https://img.shields.io/badge/HTTP-aiohttp-green?logo=python&style=for-the-badge
[Aiohttp-url]: https://docs.aiohttp.org/

[SQLite-badge]: https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&style=for-the-badge
[SQLite-url]: https://www.sqlite.org/index.html

[Aiosqlite-badge]: https://img.shields.io/badge/DB%20Access-aiosqlite-lightgrey?style=for-the-badge
[Aiosqlite-url]: https://pypi.org/project/aiosqlite/

[Timezonefinder-badge]: https://img.shields.io/badge/Geo%20Timezone-timezonefinder-yellow?style=for-the-badge
[Timezonefinder-url]: https://pypi.org/project/timezonefinder/

[Pytz-badge]: https://img.shields.io/badge/Timezone-pytz-orange?style=for-the-badge
[Pytz-url]: https://pypi.org/project/pytz/

[Docker-badge]: https://img.shields.io/badge/Docker-Ready-blue?logo=docker&style=for-the-badge
[Docker-url]: https://www.docker.com/

[Precommit-badge]: https://img.shields.io/badge/Git-Hooks-critical?logo=pre-commit&style=for-the-badge
[Precommit-url]: https://pre-commit.com/

[Flake8-badge]: https://img.shields.io/badge/Linter-flake8-red?style=for-the-badge
[Flake8-url]: https://flake8.pycqa.org/

[Isort-badge]: https://img.shields.io/badge/Imports-isort-%23323330?style=for-the-badge
[Isort-url]: https://pycqa.github.io/isort/

[BlackStyle-badge]: https://img.shields.io/badge/style-black_profile-grey?style=for-the-badge
[Black-url]: https://black.readthedocs.io/en/stable/

[Autopep8-badge]: https://img.shields.io/badge/Formatter-autopep8-9cf?style=for-the-badge
[Autopep8-url]: https://pypi.org/project/autopep8/
