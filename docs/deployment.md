# Deployment & Hosting

This guide covers production hosting, environment considerations, and practical advice for running **BTC Price Bot** reliably at scale.

For basic installation and running instructions, see [Getting Started](../README.md#-getting-started).

---

## Table of Contents

- [Hosting Platform Options](#hosting-platform-options)
  - [Home Server or Always-on PC](#home-server-or-always-on-pc)
  - [Free / Serverless / Cloud App Platforms](#free--serverless--cloud-app-platforms)
  - [VPS / Cloud Servers (Recommended)](#vps--cloud-servers-recommended)
  - [Production Choice for BTC Price Bot: AWS EC2](#production-choice-for-btc-price-bot-aws-ec2)
- [Docker in Production](#docker-in-production)
- [Environment Variables & Secrets](#environment-variables--secrets)
- [Database Location](#database-location)
- [Logging, Monitoring, and Updates](#logging-monitoring-and-updates)

---

## Hosting Platform Options

When choosing a platform for hosting BTC Price Bot, several options were considered. Here’s a practical comparison, 
with final production decision highlighted.

### Home Server or Always-on PC

- **Good for:** Personal development, hobby use, or private demos.
- **Pros:** Free, full control, persistent storage.
- **Cons:** Less reliable than cloud hosting (prone to downtime, hardware/network issues, and limited remote access).

---

### Free / Serverless / Cloud App Platforms

- **Not suitable for BTC Price Bot.**
  - **Why:** These platforms sleep or shut down after inactivity, killing scheduled/background jobs. Persistent storage 
    is not guaranteed. No support for always-on, scheduled notifications, or robust payment/DB management.
- **Free Tier?** Most offer some free tier, but with severe restrictions for this use-case.
- **Best for:** Bots that only respond to direct user-triggered commands (no background tasks or persistent notifications).

---

### VPS / Cloud Servers (Recommended)

- **Examples:** AWS EC2/Lightsail, Hetzner, DigitalOcean, Yandex.Cloud, Vultr, Linode, Azure, Google Cloud, Fly.io, etc.
- **Pros:** Always-on, persistent storage, Docker support, full control, no artificial sleep limits.
- **Free Tier/Trial?**
    - **AWS:** 12 months free (t2.micro/t3.micro). Ideal for dev, test, or early production.
    - **Google Cloud:** Micro VM free tier (limited resources, best for learning/testing).
    - **Azure:** Free trial credits for new accounts.
    - **Hetzner, DigitalOcean, Vultr, Linode:** No free tier, but stable and affordable (from ~$4–$5/month).
    - **Fly.io:** Small free tier (limited CPU/memory/persistence), suitable for demos or light production—may require upgrade for heavy use.
- **Best for:** Production bots needing always-on uptime, scheduled notifications, and persistent DB.

---

### Production Choice for BTC Price Bot: AWS EC2

> **BTC Price Bot is deployed in production on an [AWS EC2](https://aws.amazon.com/ec2/) instance (t3.micro, Ubuntu 24.04), using Docker Compose and persistent EBS volumes for database storage.**

**Why AWS EC2?**
- **12 months Free Tier**: Covers one always-on micro instance (750 hours/month).
- **Full Docker & Compose support**: Industry-standard and easy to automate.
- **Reliable persistent storage**: With EBS volumes, backups are simple.
- **Scalability**: Easy to scale up resources or migrate as needed.
- **Cloud monitoring & billing**: Proactive resource/budget management via AWS tools.

> **Bottom Line:**  
> BTC Price Bot is currently hosted 24/7 on AWS EC2 for maximum reliability, persistence, and cost efficiency.  
> For real-world, always-on, persistent bots, cloud VPS (especially AWS Free Tier) is the recommended platform.

---

## Docker in Production

- **Best Practice:**  
  Use Docker Compose for reproducible, maintainable, and scalable deployments.
- **Auto-Restart:**  
  Compose services can be configured to always restart on failure.
- **Volume Mapping:**  
  Persistent data (DB/logs) should be mapped to host volumes for reliability. Be sure to mount only the persistent data 
  subfolder.

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
