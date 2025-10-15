from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import auth as auth_router
from .routers import anaf as anaf_router
from .routers import companies as companies_router
from .routers import invites as invites_router
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette import status
from .routers import billing as billing_router
from .routers import collections as collections_router
from .routers import collections as collections_router
from .routers import invoices as invoices_router
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("app")

app = FastAPI(title="App API", version="0.1.0")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # păstrează mesajul tău (raise HTTPException(..., detail="..."))
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # un mesaj scurt + lista completă (utile în dev)
    first = exc.errors()[0] if exc.errors() else {}
    friendly = first.get("msg", "Cerere invalidă")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": friendly, "errors": exc.errors()},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    # nu expune mesajul intern către client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A apărut o eroare internă. Încercați din nou."},
    )

origins = [
    "http://localhost:54322",
    "http://127.0.0.1:54322",
    "http://192.168.8.33:54322",
    "http://86.120.164.67:54322",   # <= add this
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     # must be explicit when allow_credentials=True
    allow_credentials=True,    # set True only if you use cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

from app.routers import recyclings as recyclings_router
app.include_router(recyclings_router.router)
from app.routers import packages as packages_router
app.include_router(packages_router.router)

app.include_router(auth_router.router)
app.include_router(anaf_router.router)
app.include_router(companies_router.router)
app.include_router(invites_router.router)
app.include_router(billing_router.router)
app.include_router(collections_router.router)
app.include_router(collections_router.router)
app.include_router(invoices_router.router)