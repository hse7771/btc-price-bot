# Deployment & Hosting

This guide covers production hosting, environment considerations, and practical advice for running **BTC Price Bot** reliably at scale.

For basic installation and running instructions, see [Getting Started](../README.md#-getting-started).

---

## Table of Contents

- [Hosting Platform Options](#hosting-platform-options)
  - [VPS / Cloud Servers (Recommended)](#vps--cloud-servers-recommended)
  - [Home Server or Always-on PC](#home-server-or-always-on-pc)
  - [Free / Serverless / Cloud App Platforms](#free--serverless--cloud-app-platforms)
- [Docker in Production](#docker-in-production)
- [Environment Variables & Secrets](#environment-variables--secrets)
- [Database Location](#database-location)
- [Logging, Monitoring, and Updates](#logging-monitoring-and-updates)

---

## Hosting Platform Options

### VPS / Cloud Servers (Recommended)

- **Examples:** Hetzner, DigitalOcean, AWS EC2/Lightsail, Yandex.Cloud, Vultr, Linode, Azure, Google Cloud, Fly.io (see notes below).
- **Pros:** Always-on, persistent storage, Docker support, full control, no artificial sleep limits.
- **Free Tier?**
  - **AWS:** 12 months free (t2.micro/t3.micro). Ideal for dev, test, or early production.
  - **Google Cloud:** Micro VM free tier (limited resources, good for learning/testing).
  - **Azure:** Free trial credits for new accounts.
  - **Hetzner, DigitalOcean, Vultr, Linode:** No free tier, but stable and affordable (from ~$4–$5/month).
  - **Fly.io:** Small free tier (limited CPU/memory/persistence), suitable for demos or light production—may require upgrade for heavy use.
- **Best for:** Production bots needing always-on uptime, scheduled notifications, and persistent DB.

---

### Home Server or Always-on PC

- Good for personal development, hobby, or private demo.
- **Pros:** Free, full control, persistent storage.
- **Cons:** Not as reliable as cloud (risk of downtime, hardware/network issues).

---

### Free / Serverless / Cloud App Platforms

- **Not suitable for BTC Price Bot.**
  - **Why:** These platforms sleep or shut down after inactivity, killing scheduled/background jobs. Persistent storage 
    is not guaranteed. No support for always-on, scheduled notifications, or robust payment/DB management.
- **Free Tier?** Most offer some free tier, but with severe restrictions for this use-case.
- **Best for:** Bots that only respond to direct user-triggered commands (no background tasks or persistent notifications).

---

> **Summary:**  
> For BTC Price Bot, a VPS/cloud server should be used for production and real users (e.g., AWS, Hetzner, Fly.io with paid plan).  
> Free platforms are *not* suitable for bots with scheduled/background jobs or persistent storage needs.

---

## Docker in Production

- **Best Practice:**  
  Use Docker Compose for reproducible, maintainable, and scalable deployments.
- **Auto-Restart:**  
  Compose services can be configured to always restart on failure.
- **Volume Mapping:**  
  Persistent data (DB/logs) should be mapped to host volumes for reliability.

The project includes a ready-to-use [`docker-compose.yml`](../docker-compose.yml).

---

## Environment Variables & Secrets

- **Never** commit tokens or secrets to Git.
- Use `.env` or platform secret management tools (AWS SSM, Docker secrets, etc).

---

## Database Location

- By default, SQLite DB is local to the bot’s working directory (or `/app/db` in Docker).
- For reliability, map to a persistent volume or mount a directory on your server.

---

## Logging, Monitoring, and Updates

- **Logs:**  
  Use `docker logs <container>` or redirect logs to file for later analysis.
- **Uptime checks:**  
  Consider a simple uptime robot or healthcheck script to alert you if the bot goes offline.
- **Updating:**  
  Pull latest code, rebuild/restart the container or process.
