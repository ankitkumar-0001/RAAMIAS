# 🛡️ RAAMIAS - Cybersecurity Command Center

**RAAMIAS** is a full-stack Security Operations Center (SOC) dashboard designed for incident management and real-time threat monitoring.

## 🚀 Key Features
* **AWS Cognito Integration:** Secure Admin authentication using industry-standard cloud identity providers.
* **Real-time Threat Feed:** Live WebSocket connection for monitoring system alerts and authorized access.
* **Incident Management:** Automated Brute Force detection and unauthorized login alerting.
* **Dynamic Status Tracking:** Real-time Online/Offline status indicators for system admins.

## 💻 Tech Stack
* **Frontend:** React, Vite, CSS3
* **Backend:** FastAPI (Python), SQLAlchemy
* **Database:** SQLite / PostgreSQL
* **Security:** AWS Boto3 (Cognito IDP)

## 🛠️ How to Run
1. **Backend:** `uvicorn main:app --reload`
2. **Frontend:** `cd raamas-frontend && npm run dev`