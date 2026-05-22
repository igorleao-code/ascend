from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
# Importa o ÚNICO Base que existe no projeto
from app.database import Base

# === USUÁRIO ===


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)

    # RELAÇÃO: Diz ao SQLAlchemy que o Usuário tem várias missões
    missions = relationship(
        "Mission", back_populates="dono", cascade="all, delete-orphan")

# === MISSÕES ===


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    xp_reward = Column(Integer, default=10)
    completed = Column(Boolean, default=False)
    is_daily = Column(Boolean, default=True)
    last_completed_date = Column(String, nullable=True)

    streak = Column(Integer, default=0)
    # CHAVE ESTRANGEIRA: O vínculo real no banco de dados
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # RELAÇÃO: Permite fazer "missao.dono" para ver os dados do usuário
    dono = relationship("User", back_populates="missions")
