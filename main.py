import asyncio
import boto3
import random
import time
from fastapi import FastAPI, Depends, HTTPException, WebSocket
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import models
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# SETUP AWS COGNITO
AWS_REGION = "us-east-1"
COGNITO_CLIENT_ID = "7a6urthaebehhh5br16m41erbp"

cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# NEW: The CORS Bouncer! Tell Python to allow React to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # <--- Your exact React address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schemas


class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


@app.get("/")
def home():
    return {"message": "RAAMIAS AWS system is running"}

# Register with AWS


@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):  # <--- Changed to async!
    try:
        response = cognito_client.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=user.email,
            Password=user.password
        )
        new_user = models.User(email=user.email)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # NEW: Blast the new registration to the SOC Dashboard!
        await manager.broadcast(f"🔵 INFO: New Security Clearance Granted - {user.email} Registered")

        return {"message": "User created securely in AWS Cognito!"}
    except cognito_client.exceptions.UsernameExistsException:
        raise HTTPException(
            status_code=400, detail="Email already registered in AWS")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# WebSocket Manager (Now Bulletproof! 🛡️)
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
        print("Sending:", message)
        # We loop through a copy of the list so we can safely delete dead ones
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception:
                # If the connection is dead (tab closed/refreshed), remove it silently!
                self.disconnect(connection)


# NEW: In-memory tracker for failed logins (Brute Force Detection)
failed_login_attempts = {}

manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except:
        manager.disconnect(websocket)

# Login with AWS


@app.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        response = cognito_client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": user.email,
                "PASSWORD": user.password
            }
        )
        token = response["AuthenticationResult"]["AccessToken"]

        db_user = db.query(models.User).filter(
            models.User.email == user.email).first()
        if db_user:
            db_user.is_online = True
            db.commit()

        # If they finally log in successfully, clear their fail history!
        if user.email in failed_login_attempts:
            del failed_login_attempts[user.email]

        await manager.broadcast(f"🟢 INFO: Authorized Access - {user.email} logged in")
        return {"message": "AWS Login successful", "status": "online", "access_token": token}

    except cognito_client.exceptions.NotAuthorizedException:
        # NEW: BRUTE FORCE ALGORITHM
        current_time = time.time()

        # Get past attempts for this email, but throw away ones older than 5 seconds
        past_attempts = failed_login_attempts.get(user.email, [])
        recent_attempts = [t for t in past_attempts if current_time - t < 5]

        # Add THIS new failed attempt to the list
        recent_attempts.append(current_time)
        failed_login_attempts[user.email] = recent_attempts

        # Check the threshold: Did they fail 3 or more times in 5 seconds?
        if len(recent_attempts) >= 3:
            await manager.broadcast(f"🚨 CRITICAL: BRUTE FORCE DETECTED! Rapid failed logins for {user.email}")
        else:
            await manager.broadcast(f"🛑 WARNING: Failed Login Attempt for {user.email} (Invalid Password)")

        raise HTTPException(status_code=400, detail="Invalid password")

    except cognito_client.exceptions.UserNotFoundException:
        await manager.broadcast(f"🛑 WARNING: Unauthorized access attempt with unknown email: {user.email}")
        raise HTTPException(status_code=400, detail="User not found in AWS")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# NEW: This tells Swagger to just give us a blank box for the token
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Extract the token from the credentials
    token = credentials.credentials
    try:
        # Pass the token to AWS
        response = cognito_client.get_user(AccessToken=token)

        # Dig out the email
        for attr in response['UserAttributes']:
            if attr['Name'] == 'email':
                return attr['Value']
    except Exception as e:
        raise HTTPException(
            status_code=401, detail="Invalid token! Access Denied.")


# NEW: Upgraded Secure Logout
@app.post("/logout")
async def logout(email: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if db_user:
        db_user.is_online = False
        db.commit()

    # 🔔 Added some visual flair to the broadcast!
    await manager.broadcast(f"🚨 ALERT: {email} just logged OUT")
    return {"message": f"Logged out securely", "status": "offline"}

# Status


@app.get("/status/{email}")
def get_status(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": user.email, "is_online": user.is_online}
