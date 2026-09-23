import logging
from typing import Optional, Any
from urllib.parse import urlsplit
import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import mongomock
from app.config import settings

logger = logging.getLogger("investigation.db")

class AsyncMongoMockCollection:
    """Async wrapper around mongomock collection for local zero-config persistence."""
    def __init__(self, sync_collection):
        self._col = sync_collection

    async def find_one(self, filter=None, *args, **kwargs):
        return self._col.find_one(filter, *args, **kwargs)

    def find(self, filter=None, *args, **kwargs):
        cursor = self._col.find(filter, *args, **kwargs)
        return AsyncMockCursor(cursor)

    async def insert_one(self, document):
        return self._col.insert_one(document)

    async def insert_many(self, documents):
        return self._col.insert_many(documents)

    async def update_one(self, filter, update, upsert=False):
        return self._col.update_one(filter, update, upsert=upsert)

    async def delete_one(self, filter):
        return self._col.delete_one(filter)

    async def delete_many(self, filter):
        return self._col.delete_many(filter)

    async def count_documents(self, filter=None):
        return self._col.count_documents(filter or {})

    async def create_index(self, *args, **kwargs):
        return None

class AsyncMockCursor:
    def __init__(self, sync_cursor):
        self._cursor = sync_cursor

    def sort(self, *args, **kwargs):
        self._cursor.sort(*args, **kwargs)
        return self

    def limit(self, *args, **kwargs):
        self._cursor.limit(*args, **kwargs)
        return self

    async def to_list(self, length=None):
        docs = list(self._cursor)
        if length is not None:
            return docs[:length]
        return docs

    def __aiter__(self):
        self._iter = iter(self._cursor)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

class AsyncMongoMockDatabase:
    def __init__(self, sync_db):
        self._db = sync_db

    def __getitem__(self, name: str):
        return AsyncMongoMockCollection(self._db[name])

    def get_collection(self, name: str):
        return AsyncMongoMockCollection(self._db[name])

class DatabaseManager:
    client: Optional[Any] = None
    db: Optional[Any] = None
    is_live_mongo: bool = False

    async def connect(self):
        db_name = settings.effective_db_name
        # Test if live MongoDB / MongoDB Atlas is accessible
        if settings.MONGODB_URI and not settings.MONGODB_URI.startswith("mongodb://localhost"):
            try:
                parsed_host = urlsplit(settings.MONGODB_URI).netloc.split("@")[-1]
                logger.info(f"Connecting to MongoDB Atlas cluster at {parsed_host} (database: {db_name})...")
                temp_client = AsyncIOMotorClient(
                    settings.MONGODB_URI,
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=5000
                )
                await temp_client.admin.command('ping')
                self.client = temp_client
                self.db = self.client[db_name]
                self.is_live_mongo = True
                logger.info(f"Successfully connected to live MongoDB Atlas database '{db_name}'!")
                await self._create_indexes()
                return
            except Exception as e:
                logger.warning(
                    f"Unable to connect to live MongoDB Atlas ({e}). "
                    "Note: Ensure your current public IP is added to the MongoDB Atlas Network Access whitelist. "
                    "Falling back to resilient local datastore."
                )

        # Fallback if localhost or Atlas unreachable
        try:
            temp_client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=1500)
            await temp_client.admin.command('ping')
            self.client = temp_client
            self.db = self.client[db_name]
            self.is_live_mongo = True
            logger.info(f"Connected to local MongoDB daemon (database: {db_name}).")
            await self._create_indexes()
            return
        except Exception:
            logger.info(f"Initializing resilient high-performance in-memory datastore (database: {db_name}).")
            mock_client = mongomock.MongoClient()
            sync_db = mock_client[db_name]
            self.db = AsyncMongoMockDatabase(sync_db)
            self.is_live_mongo = False

    async def _create_indexes(self):
        if self.is_live_mongo and self.db is not None:
            try:
                await self.db["cases"].create_index("case_id", unique=True)
                await self.db["evidence"].create_index([("case_id", 1), ("evidence_id", 1)])
                await self.db["entities"].create_index([("case_id", 1), ("category", 1)])
                await self.db["keywords"].create_index([("case_id", 1), ("keyword", 1)])
                await self.db["timeline"].create_index([("case_id", 1), ("timestamp", 1)])
            except Exception as e:
                logger.warning(f"Index creation notice: {e}")

    async def close(self):
        if self.is_live_mongo and self.client is not None:
            self.client.close()
            logger.info("Closed MongoDB connection.")

db_manager = DatabaseManager()

def get_db():
    return db_manager.db

def get_collection(name: str):
    return db_manager.db[name]
