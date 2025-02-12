import sentry_sdk
from fastapi import FastAPI
from routers import users, gps
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import logfire
from fastapi.middleware.cors import CORSMiddleware

# Initialize Sentry
sentry_sdk.init(
    dsn="https://c1f9de5250642b93751d7e743444768f@o4508243862028288.ingest.de.sentry.io/4508799409061968",  # Replace with your actual Sentry DSN
    traces_sample_rate=1.0  # Adjust the sample rate as needed
)

app = FastAPI()

# Add Sentry middleware
app.add_middleware(SentryAsgiMiddleware)
logfire.configure(token='M3KR7WQ74BWYR26Xbtf7LqCNX8MgNGsdKwsgmPpGLqTj')
logfire.instrument_fastapi(app, capture_headers=True)
    
# Đăng ký router
app.include_router(users.router)
app.include_router(gps.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://103.176.179.183:3001"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
