# SimplyToast  
<img align="right" src="https://raw.githubusercontent.com/toast1599/SimplyToast/main/assets/logo.png" width="120">

**SimplyToast** is a lightweight GTK4 application for managing **user-level startup applications and background processes** on Linux — without root access, system-wide changes, or hidden magic.

It’s designed for people who want **visibility and control** over what runs in their session, without touching system services or writing `.desktop` files by hand.

Created and maintained by **@toast1599**  
Licensed under **GPL-3.0**

---

## 🚀 Overview

SimplyToast focuses on one problem and stays in its lane:

- Managing **user startup applications**
- Inspecting **session-level background processes**
- Understanding **resource impact at login**
- Making changes safely, without root

**What it does NOT do:**
- ❌ No system services
- ❌ No root access
- ❌ No systemd unit manipulation
- ❌ No kernel-level monitoring

If it affects your *user session*, SimplyToast cares.  
If it affects the *entire system*, it stays out of the way.

---

## ✨ Features

### 🔧 Startup Application Management
- Enable, disable, or edit user autostart entries
- Uses standard XDG autostart locations
- No manual file editing required

### 📊 Background Process Visibility
- View running **user-session processes**
- See CPU and RAM usage relevant to your session
- Focused on startup-related background apps, not full system monitoring

### ⚡ Resource Impact Estimation
- Startup entries receive an **impact score** based on observed CPU and memory usage
- Designed to highlight *relative* cost, not replace system profilers
- Helps identify what slows down login over time

### 🎨 Theme Support
- Light
- Mid
- Dark

### 🔐 Safe by Design
- Runs entirely as a normal user
- No root permissions required
- No system configuration files modified

---

## 📸 Screenshots

> **Screenshot placeholder #1**  
> *(Startup application list / overview screen)*

> **Screenshot placeholder #2**  
> *(Background process view or resource impact view)*

---

## 📦 Installation

### Recommended: Prebuilt Binaries

Download the latest release here:  
👉 https://github.com/toast1599/SimplyToast/releases

Available formats:
- **Arch Linux / AUR** (.pkg.tar.zst)
- **Debian / Ubuntu / Mint** (.deb)
- **Fedora / RPM-based distros** (.rpm)
- **AppImage** (portable, most distros)

If your distro supports native packages, use those first.  
AppImage is best for testing or portable use.

---

## 🛠 Running from Source (Development)

This is intended for development and testing — not required for normal use.

```
git clone https://github.com/toast1599/SimplyToast  
cd SimplyToast  
python3 src/main.py
```

GTK4 must be available on your system.

---

## 🧭 Project Scope & Philosophy

SimplyToast intentionally avoids becoming:
- a system monitor
- a service manager
- a systemd frontend

There are already excellent tools for those jobs.

The goal here is **clarity at startup**:
- What launches with my session?
- What keeps running?
- What actually costs resources?

Nothing more, nothing less.

---

## 💬 Community & Support

- Discord: https://discord.gg/yX92vzqvwd
- Issues & feature requests: GitHub Issues

If something feels unsafe, unclear, or misleading — that’s a bug.

---

## 📄 License

SimplyToast is licensed under the **GNU GPL-3.0**.  
You are free to use, modify, and redistribute it under the terms of the license.
