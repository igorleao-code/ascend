from fastapi import FastAPI, Depends, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from app.database import get_db, engine
from app.models import Base, User, Mission
from datetime import datetime, timezone

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


# 1. ROTA DA PÁGINA INICIAL
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=engine)
    usuario_real = db.query(User).first()

    if not usuario_real:
        usuario_real = User(
            name="Igor", email="igor@email.com", level=1, xp=30)
        db.add(usuario_real)
        db.commit()
        db.refresh(usuario_real)

        missao1 = Mission(title="Treinar jiu-jitsu",
                          xp_reward=20, user_id=usuario_real.id)
        missao2 = Mission(title="Ir pra academia",
                          xp_reward=15, user_id=usuario_real.id)
        missao3 = Mission(title="Ler 20 páginas",
                          xp_reward=10, user_id=usuario_real.id)

        db.add_all([missao1, missao2, missao3])
        db.commit()
        db.refresh(usuario_real)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "usuario": usuario_real}
    )


# 2. ROTA DE CONCLUIR MISSÃO (Unificada aqui para não dar erro de rota)
@app.post("/missions/{mission_id}/complete")
def complete_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Missão não encontrada")

    if not mission.completed:
        mission.completed = True

        # 🌟 CARIMBO DE DATA/HORA INJETADO AQUI:
        mission.completed_at = datetime.now(timezone.utc)

        # Sua lógica de XP e Nível que já está perfeita:
        usuario = db.query(User).filter(User.id == mission.user_id).first()
        if usuario:
            usuario.xp += mission.xp_reward
            if usuario.xp >= 100:
                usuario.level += 1
                usuario.xp = usuario.xp - 100
        db.commit()

    # Força o redirecionamento limpando o histórico para a Home
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

# 3. NOVA ROTA: CRIAR MISSÃO (CUSTOMIZADA OU PRE-SELECIONADA)


@app.post("/missions/create")
def create_mission(
    title: str = Form(...),
    xp_reward: int = Form(10),  # Valor padrão se não for preenchido
    db: Session = Depends(get_db)
):
    # Busca o usuário ativo
    usuario = db.query(User).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Cria a nova missão no banco de dados
    nova_missao = Mission(title=title, xp_reward=xp_reward, user_id=usuario.id)
    db.add(nova_missao)
    db.commit()

    # Redireciona de volta para a Home atualizada
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# 4. ROTA: DELETAR MISSÃO (AGORA TRABALHANDO COM AJAX)
@app.post("/missions/{mission_id}/delete")
def delete_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Missão não encontrada")

    db.delete(mission)
    db.commit()

    # Em vez de redirecionar, responde um status de sucesso para o JS ler
    return {"sucesso": True}
