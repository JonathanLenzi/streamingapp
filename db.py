from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///database/tokiobase.db', connect_args={'check_same_thread': False}, pool_recycle=3600, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()
