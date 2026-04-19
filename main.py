import asyncio
import boto3
import time
import io
import csv
import re  # 🛡️ Added for strict character validation
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, WebSocket, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import models
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from botocore.exceptions import ClientError

# ================= AWS CONFIGURATION =================
AWS_REGION = "us-east-1"
COGNITO_CLIENT_ID = "YOUR COGNITO_CLINT_ID"
USER_POOL_ID = "YOUR USER_POOL_ID"

# YOUR VERIFIED DETAILS
SENDER_EMAIL = "Your_Email"
SNS_TOPIC_ARN = "ARN_FOR_ALERT"

# Initialize AWS Clients
cognito_client = boto3.client(
    "cognito-idp",
    region_name=AWS_REGION,
    aws_access_key_id="YOUR_AWS_ACCESS_KEY",
    aws_secret_access_key="YOUR_AWS_SECRET_KEY"
)
ses_client = boto3.client('ses', region_name=AWS_REGION)
sns_client = boto3.client('sns', region_name=AWS_REGION)

# ================= APP SETUP =================
models.Base.metadata.create_all(bind=engine)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---


class UserCreate(BaseModel):
    email: str
    password: str


class UserVerify(BaseModel):
    email: str
    code: str


class UserLogin(BaseModel):
    email: str
    password: str

# --- WebSocket Manager ---


class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()
failed_login_attempts = {}

# ================= DEFENSE & ALERT LOGIC =================


def is_user_banned(email, db: Session):
    ban_entry = db.query(models.Blacklist).filter(
        models.Blacklist.email == email).first()
    if ban_entry:
        if datetime.utcnow() - ban_entry.banned_at < timedelta(minutes=30):
            return True
        db.delete(ban_entry)
        db.commit()
    return False


async def send_security_alerts(user_email, attack_type):
    subject = f"🚨 RAAMIAS Security Alert: {attack_type}"
    body = (f"CRITICAL SECURITY ALERT\n\nEvent: {attack_type}\nTarget: {user_email}\n"
            f"Time: {time.ctime()}\n\nACTION: Blacklisted for 30 minutes.")
    try:
        ses_client.send_email(
            Source=SENDER_EMAIL, Destination={'ToAddresses': [SENDER_EMAIL]},
            Message={'Subject': {'Data': subject},
                     'Body': {'Text': {'Data': body}}}
        )
        sns_client.publish(TopicArn=SNS_TOPIC_ARN,
                           Message=body, Subject=subject)
    except ClientError as e:
        print(f"❌ Alert Error: {e}")

# ================= CORE ENDPOINTS =================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except:
        manager.disconnect(websocket)


@app.get("/check-availability/{email}")
async def check_email_availability(email: str):
    """Real-time Google-style username check."""
    try:
        cognito_client.admin_get_user(UserPoolId=USER_POOL_ID, Username=email)
        return {"available": False, "message": "Username taken."}
    except cognito_client.exceptions.UserNotFoundException:
        return {"available": True, "message": "Available."}
    except Exception:
        raise HTTPException(status_code=500, detail="Identity check error")


@app.post("/register")
async def register(user: UserCreate):
    try:
        # Split the email into username and domain
        username_part, domain_part = user.email.lower().split('@')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email format.")

    # 🛡️ LAYER 1: DOMAIN WHITELIST
    # Only allow these specific domains. Everything else is rejected.
    ALLOWED_DOMAINS = ["gmail.com", "mail.com"]
    if domain_part not in ALLOWED_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail=f"🚨 SECURITY POLICY: '@{domain_part}' is not an authorized provider. Only @gmail.com or @mail.com are allowed."
        )

    # 🛡️ LAYER 2: CHARACTER SHIELD (Blocks #, &, $, etc.)
    if not re.match(r"^[a-z0-9.]+$", username_part):
        raise HTTPException(
            status_code=400,
            detail="🚨 SECURITY POLICY: Usernames can only contain letters (a-z), numbers (0-9), and periods (.)."
        )

    # 🛡️ LAYER 3: RESERVED KEYWORDS
    RESERVED = ["admin", "root", "support", "system", "raamias", "official"]
    if username_part in RESERVED:
        raise HTTPException(status_code=400, detail="Username reserved.")

    # If all 3 shields are passed, talk to AWS Cognito
    try:
        cognito_client.sign_up(ClientId=COGNITO_CLIENT_ID,
                               Username=user.email, Password=user.password)
        await manager.broadcast(f"🔵 INFO: Registration initiated for {user.email}.")
        return {"message": "Code sent"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/verify")
async def verify_email(user: UserVerify, db: Session = Depends(get_db)):
    try:
        cognito_client.confirm_sign_up(
            ClientId=COGNITO_CLIENT_ID, Username=user.email, ConfirmationCode=user.code)
        new_user = models.User(email=user.email, is_online=False)
        db.add(new_user)
        db.commit()
        await manager.broadcast(f"✅ SUCCESS: Verified identity - {user.email}")
        return {"message": "Verified"}
    except:
        raise HTTPException(status_code=400, detail="Invalid code.")


@app.post("/login")
async def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    client_ip = request.client.host
    if is_user_banned(user.email, db):
        await manager.broadcast(f"🚫 BLOCK: Banned user {user.email} from {client_ip}")
        raise HTTPException(status_code=403, detail="Banned.")
    try:
        response = cognito_client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID, AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": user.email, "PASSWORD": user.password}
        )
        token = response["AuthenticationResult"]["AccessToken"]
        db_user = db.query(models.User).filter(
            models.User.email == user.email).first()
        if not db_user:
            db_user = models.User(email=user.email, is_online=True)
            db.add(db_user)
        else:
            db_user.is_online = True
        db.commit()
        failed_login_attempts.pop(user.email, None)
        await manager.broadcast(f"🟢 INFO: Authorized Access - {user.email}")
        return {"access_token": token}
    except cognito_client.exceptions.NotAuthorizedException:
        attempts = failed_login_attempts.get(user.email, [])
        attempts = [t for t in attempts if time.time() - t < 10]
        attempts.append(time.time())
        failed_login_attempts[user.email] = attempts
        if len(attempts) >= 3:
            db.add(models.Blacklist(email=user.email, banned_at=datetime.utcnow()))
            db.commit()
            await send_security_alerts(user.email, "BRUTE FORCE DETECTED")
            await manager.broadcast(f"🔒 DEFENSE: {user.email} BLACKLISTED.")
        else:
            await manager.broadcast(f"🛑 WARNING: Failed Login - {user.email}")
        raise HTTPException(status_code=400, detail="Invalid password")

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        res = cognito_client.get_user(AccessToken=credentials.credentials)
        return next(a['Value'] for a in res['UserAttributes'] if a['Name'] == 'email')
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/logout")
async def logout(email: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if db_user:
        db_user.is_online = False
        db.commit()
    await manager.broadcast(f"🚨 ALERT: {email} logged out")
    return {"message": "Logged out"}

# ================= ENTERPRISE HEALTH SYNC =================


@app.get("/system/health")
def get_system_health(db: Session = Depends(get_db)):
    bans = [b.email for b in db.query(models.Blacklist).all()]
    online = [u.email for u in db.query(models.User).filter(
        models.User.is_online == True).all()]
    try:
        aws_res = cognito_client.list_users(UserPoolId=USER_POOL_ID)
        master = [a['Value'] for u in aws_res['Users']
                  for a in u['Attributes'] if a['Name'] == 'email']
    except:
        master = [u.email for u in db.query(models.User).all()]

    data = []
    for email in master:
        status = "BANNED 🚫" if email in bans else (
            "ONLINE 🟢" if email in online else "OFFLINE ⚪")
        data.append({"email": email, "status": status})

    return {
        "threat_level": "CRITICAL" if bans else "NORMAL",
        "active_bans": len(bans),
        "user_health": data
    }


@app.get("/audit/logs")
def get_audit_logs(db: Session = Depends(get_db)):
    bans = db.query(models.Blacklist).all()
    return {"audit_trail": [{"id": b.id, "account": b.email, "time": b.banned_at} for b in bans]}


@app.get("/export/audit-csv")
def export_audit_csv(db: Session = Depends(get_db)):
    bans = db.query(models.Blacklist).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Incident ID", "Account", "Timestamp (UTC)", "Action"])
    for b in bans:
        writer.writerow([b.id, b.email, b.banned_at.strftime(
            "%Y-%m-%d %H:%M:%S"), "30-Min Ban"])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=Forensic_Audit.csv"})
