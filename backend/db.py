import os
import logging
from contextlib import contextmanager
import oracledb
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_module")

# Load environment variables
load_dotenv()

# Try enabling Oracle Client (Thick Mode) to support older database password verifiers (like DPY-3015 for FORTUMED)
try:
    # If the Oracle Instant Client libraries are on the system PATH, this will initialize Thick Mode automatically.
    oracledb.init_oracle_client()
    logger.info("Oracle Instant Client initialized successfully. Running in THICK MODE (supports verifier 0x939).")
except Exception as e:
    logger.warning(f"Could not initialize oracledb THICK MODE (Instant Client libraries not detected). Running in default THIN MODE. Error: {e}") 

class DatabaseManager:
    def __init__(self):
        self.pool_cauca = None
        self.pool_fortuna = None

    def init_pools(self):
        # CAUCAMED config
        host_cauca = os.getenv("DB_HOST_CAUCAMED", "172.17.101.5")
        port_cauca = int(os.getenv("DB_PORT_CAUCAMED", "1521"))
        service_cauca = os.getenv("DB_SERVICE_NAME_CAUCAMED", "CAUCAMED")
        user_cauca = os.getenv("DB_USERNAME_CAUCAMED", "JEREPORTES")
        password_cauca = os.getenv("DB_PASSWORD_CAUCAMED", "JEreportes2021*")

        # FORTUMED config
        host_fortuna = os.getenv("DB_HOST_FORTUMED", "172.17.101.5")
        port_fortuna = int(os.getenv("DB_PORT_FORTUMED", "1521"))
        service_fortuna = os.getenv("DB_SERVICE_NAME_FORTUMED", "FORTUNA")
        user_fortuna = os.getenv("DB_USERNAME_FORTUMED", "JEREPORTES")
        password_fortuna = os.getenv("DB_PASSWORD_FORTUMED", "JEreportes2021*")

        # Create CAUCAMED pool if not already active
        if not self.pool_cauca:
            try:
                dsn_cauca = oracledb.makedsn(host_cauca, port_cauca, service_name=service_cauca)
                logger.info(f"Creating CAUCAMED pool to {host_cauca}:{port_cauca}/{service_cauca}")
                self.pool_cauca = oracledb.create_pool(
                    user=user_cauca,
                    password=password_cauca,
                    dsn=dsn_cauca,
                    min=1,
                    max=5,
                    increment=1
                )
                logger.info("CAUCAMED pool created successfully.")
            except Exception as e:
                logger.error(f"Error creating CAUCAMED pool: {e}")

        # Create FORTUMED pool if not already active
        if not self.pool_fortuna:
            try:
                dsn_fortuna = oracledb.makedsn(host_fortuna, port_fortuna, service_name=service_fortuna)
                logger.info(f"Creating FORTUMED pool to {host_fortuna}:{port_fortuna}/{service_fortuna}")
                self.pool_fortuna = oracledb.create_pool(
                    user=user_fortuna,
                    password=password_fortuna,
                    dsn=dsn_fortuna,
                    min=1,
                    max=5,
                    increment=1
                )
                logger.info("FORTUMED pool created successfully.")
            except Exception as e:
                logger.error(f"Error creating FORTUMED pool: {e}")

    def close_pools(self):
        if self.pool_cauca:
            try:
                self.pool_cauca.close()
                logger.info("CAUCAMED pool closed.")
            except Exception as e:
                logger.error(f"Error closing CAUCAMED pool: {e}")
            finally:
                self.pool_cauca = None
        if self.pool_fortuna:
            try:
                self.pool_fortuna.close()
                logger.info("FORTUMED pool closed.")
            except Exception as e:
                logger.error(f"Error closing FORTUMED pool: {e}")
            finally:
                self.pool_fortuna = None

    @contextmanager
    def get_cauca_connection(self):
        # Auto-retry pool initialization if not loaded
        if not self.pool_cauca:
            try:
                self.init_pools()
            except Exception as e:
                logger.error(f"On-demand CAUCAMED pool init retry failed: {e}")
        
        if not self.pool_cauca:
            raise Exception("CAUCAMED connection pool is not initialized.")
        
        conn = None
        try:
            conn = self.pool_cauca.acquire()
            yield conn
        except oracledb.DatabaseError as e:
            logger.error(f"Database error on CAUCAMED connection: {e}")
            error_obj, = e.args
            # DPY-4011, DPY-3015 or standard Oracle ORA-xxxxx connection lost codes
            # Reset pool to allow a clean retry initialization next time
            if any(code in str(e) for code in ["12170", "12541", "12535", "12543", "03113", "03135", "12514", "DPY-4011", "DPY-3015"]):
                logger.warning("Connection failure/timeout detected. Resetting CAUCAMED pool for automatic recovery on next retry.")
                self.pool_cauca = None
            raise
        finally:
            if conn and self.pool_cauca:
                try:
                    self.pool_cauca.release(conn)
                except Exception:
                    pass

    @contextmanager
    def get_fortuna_connection(self):
        # Auto-retry pool initialization if not loaded
        if not self.pool_fortuna:
            try:
                self.init_pools()
            except Exception as e:
                logger.error(f"On-demand FORTUMED pool init retry failed: {e}")
        
        if not self.pool_fortuna:
            raise Exception("FORTUMED connection pool is not initialized.")
        
        conn = None
        try:
            conn = self.pool_fortuna.acquire()
            yield conn
        except oracledb.DatabaseError as e:
            logger.error(f"Database error on FORTUMED connection: {e}")
            error_obj, = e.args
            # Reset pool to allow a clean retry initialization next time
            if any(code in str(e) for code in ["12170", "12541", "12535", "12543", "03113", "03135", "12514", "DPY-4011", "DPY-3015"]):
                logger.warning("Connection failure/timeout detected. Resetting FORTUMED pool for automatic recovery on next retry.")
                self.pool_fortuna = None
            raise
        finally:
            if conn and self.pool_fortuna:
                try:
                    self.pool_fortuna.release(conn)
                except Exception:
                    pass

# Singleton manager instance
db_manager = DatabaseManager()
