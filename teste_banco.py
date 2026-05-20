import os
from app.database import SessionLocal, engine  # Adicionado engine aqui
from app.models import Base, User, Mission


def testar_sistema():
    # Garante que as tabelas serão criadas no arquivo correto antes do teste
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()


print("--- INICIANDO TESTE DO BANCO DE DADOS ---")

try:
    from app.database import SessionLocal
    from app.models import User, Mission
    print("Módulos importados com sucesso!")

    db = SessionLocal()
    print("Conexão com o banco estabelecida!")

    # Testando a busca (deve retornar vazio se o banco for novo)
    usuarios = db.query(User).all()
    print(f"Sucesso! Usuários encontrados no banco: {len(usuarios)}")

    db.close()
except Exception as e:
    print(f"Erro detectado: {e}")

print("--- FIM DO TESTE ---")
