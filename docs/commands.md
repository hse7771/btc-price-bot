# Bot Commands & User Experience

This document lists all available commands, inline button actions, and explains the typical user flows for **BTC Price Bot**.

---

## Slash Commands

| Command          | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| `/start`         | Start the bot, view the main menu, and see your current status               |
| `/price`         | Get the current BTC price in your selected currencies                        |
| `/currency`      | Open the currency selection menu                                             |
| `/base`          | Manage or subscribe to standard (base) price alert plans                     |
| `/personal`      | Manage or create personalized (timezone-aware) alert plans                   |
| `/upgrade`       | View upgrade options and access payment/upgrade menus                        |
| `/donate`        | Open the donation menu                                                       |
| `/timezone`      | Set or update your local timezone                                            |
| `/help`          | Show help information and bot usage tips                                     |

---

## Inline Buttons

| Button Label        | Action                                          |
|---------------------|------------------------------------------------|
| Check Price         | Show live BTC price in your selected currencies |
| Change Currency     | Toggle preferred currencies                     |
| Subscribe (Base)    | Set up fixed interval alerts                    |
| Add/Cancel Personal | Manage custom alerts                            |
| Upgrade             | Start payment/upgrade flow                      |
| Donate              | Open donation options                           |
| Time Settings       | Set or review your timezone                     |
| Back/Close          | Return/dismiss menus                            |

---

## User Flows

### 1. **Get BTC Price Now**
- User presses "Check Price" (button) or uses `/price`
- Bot returns live BTC price (uses cache for efficiency)

### 2. **Change Currency Preferences**
- User presses "Change Currency" or `/currency`
- Bot displays a multi-select menu with all supported currencies
- User toggles their preferred currencies and presses "Close" to save

### 3. **Set Up a Base Plan Subscription**
- User accesses via "Base Plan" button or `/base`
- Selects desired interval (e.g., 15m, 1h, 24h)
- Bot schedules notifications at that UTC interval

### 4. **Set Up a Personal Plan Subscription**
- User accesses via "Personal Plan" button or `/personal`
- Enters or selects a custom time and frequency
- Bot creates a personalized alert, respecting user’s timezone

### 5. **Upgrade or Donate**
- User opens "Upgrade" or "Donate" menu
- Chooses payment method (YooMoney or Smart Glocal)
- Completes payment (upgrade: unlocks Pro/Ultra tier; donate: thanks message)

### 6. **Set or Change Timezone**
- User opens "Time Settings" or `/timezone`
- Shares location or enters timezone manually
- Bot updates local time settings for accurate notifications
