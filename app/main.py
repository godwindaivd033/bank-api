#---Kick starting the database--
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import time
from app.routers.auth_router import router as signup
from app.routers.admin_router import router as admin
from app.routers.accounts_router import router as account
from app.routers.beneficiary_router import router as beneficiaries
from app.routers.transaction_router import router as transactions
from app.routers.profile_router import router as profile
from app.routers.dashboard_router import router as dashboard
from app.routers.websocket import router as websocket_router
from test.test_redis import router as redis_router
from fastapi import FastAPI, Request
from app.database import create_db_and_table, create_admin



#---Configuring the database---
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_table()
    create_admin()
    yield

app= FastAPI(lifespan= lifespan)





#---Creating the custom middleware---
@app.middleware('http')

async def log_requests(request: Request, call_next):
#---Code runs before the route handler---

    start_time= time.time()
    print(f'Incoming: {request.method} {request.url}')
    response= await call_next(request)# run the route

#---Code runs after the router---
    duration= time.time() - start_time
    print(f'Completed in {duration:.3f}s | Status: {response.status_code}')
    response.headers['X-Process-Time'] = str(duration)
    return response



#---Configuring the CORS
origins= ["http://localhost:8000"]
app.add_middleware(CORSMiddleware,
                   allow_origins= origins,
                   allow_credentials= True,
                   allow_methods= ["GET", "POST", "PATCH"],
                   allow_headers= ["*"])


app.include_router(signup)
app.include_router(admin)
app.include_router(account)
app.include_router(beneficiaries)
app.include_router(profile)
app.include_router(transactions)
app.include_router(dashboard)
app.include_router(websocket_router)
app.include_router(redis_router)


