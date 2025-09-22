from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.websocket_routes import register_websockets
from app.api.kafka_consumer import start_consumer_thread
from app.core.logger import setup_logger
from app.api.init_endpoints import router as init_router
from app.api.bridge_endpoint import router as bridge_router

app = FastAPI()
setup_logger()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from contextlib import asynccontextmanager
from app.db.mongo import close_mongo_connection, mongo_client, create_indexes

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_indexes()
    start_consumer_thread()
    yield
    close_mongo_connection()

app.router.lifespan_context = lifespan
register_websockets(app)
app.include_router(init_router)
app.include_router(bridge_router)
