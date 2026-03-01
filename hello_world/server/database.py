from neo4j import AsyncGraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jConnection:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None
    
    async def connect(self):
        if not self.driver:
            self.driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
        return self.driver
    
    async def close(self):
        if self.driver:
            await self.driver.close()
            self.driver = None
    
    async def get_session(self):
        driver = await self.connect()
        return driver.session()


neo4j_conn = Neo4jConnection()

async def get_db():
    session = await neo4j_conn.get_session()
    try:
        yield session
    finally:
        await session.close()