from sqlmodel import SQLModel, create_engine, Session
from ..utils.config import ServerConfig, get_data_dir

# Get config
config = ServerConfig()

# Determine DB path
# We use get_data_dir() to be XDG compliant
db_path = get_data_dir() / config.db_name
sqlite_url = f"sqlite:///{db_path}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    """Initializes the database schema."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency for providing a database session."""
    with Session(engine) as session:
        yield session
