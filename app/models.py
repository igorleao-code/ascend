from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone, date, timedelta

Base = declarative_base()


#  USUÁRIO
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)

    # O streak geral saiu daqui!
    missions = relationship("Mission", back_populates="owner")

# MISSÕES


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    xp_reward = Column(Integer)
    completed = Column(Boolean, default=False)
    is_daily = Column(Boolean, default=True)
    completed_at = Column(DateTime, nullable=True)

    # --- AGORA CADA MISSÃO TEM SEU PRÓPRIO FOGO ---
    # Dias seguidos desta missão
    streak = Column(Integer, default=0)
    # Último dia que você concluiu ELA
    last_completed_date = Column(Date, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="missions")
