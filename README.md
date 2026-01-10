# SimplyToast  
<img align="right" src="https://raw.githubusercontent.com/toast1599/SimplyToast/main/assets/logo.png" width="120">

**SimplyToast** is a lightweight GTK4 utility for managing user-level startup applications and background processes on Linux. It provides a clean interface for session management without requiring root access or manual editing of `.desktop` files.

Created and maintained by **@toast1599** | Licensed under **GPL-3.0**

---

## Overview

SimplyToast is designed to give you visibility into your login session. It focuses on:

* **User Autostart:** Managing entries in standard XDG autostart locations.
* **Session Processes:** Inspecting background apps running under your current user.
* **Resource Impact:** Understanding which apps contribute to login delay.
* **User-Space Safety:** No systemd manipulation, no root permissions, and no system-wide changes.

If it affects your personal session, SimplyToast handles it. If it’s a system-level service, it stays out of the way.

## Key Features

### Startup Management
Enable, disable, or edit your autostart entries via a GUI. It follows XDG standards, so changes are transparent and compatible with most desktop environments.

### Background Visibility
View running processes specifically relevant to your user session. This is designed to highlight startup-related background apps rather than acting as a full-system process manager.

### Impact Estimation
Startup entries are assigned a relative "impact score" based on CPU and memory usage. This helps you identify which apps are actually slowing down your login over time.

### Zero-Root Design
The app runs entirely with user permissions. It does not modify system configuration files or require `sudo` to function.

---

## Installation

### Arch Linux (AUR)
You can install SimplyToast using an AUR helper:

```bash
yay -S simplytoast
# or
paru -S simplytoast
```

### Binary Packages
Prebuilt binaries are available on the [Releases](https://github.com/toast1599/SimplyToast/releases) page:
* **Debian / Ubuntu / Mint** (.deb)
* **Fedora / RPM distros** (.rpm)
* **AppImage** (Universal/Portable)

---

## Development

To run from source for testing or development:

```bash
git clone [https://github.com/toast1599/SimplyToast](https://github.com/toast1599/SimplyToast)
cd SimplyToast
python3 src/main.py
```
*Note: Ensure GTK4 libraries are installed on your system.*

---

## Philosophy

SimplyToast intentionally avoids feature creep. It is not a system monitor or a systemd frontend. There are already excellent tools for those tasks. 

This tool exists to answer three simple questions:
1. What launches when I log in?
2. Is it still running?
3. What is it costing my system?

---

## Community

* **Discord:** [Join the server](https://discord.gg/yX92vzqvwd)
* **Issues:** Report bugs or request features via [GitHub Issues](https://github.com/toast1599/SimplyToast/issues)
* 
