from fastapi import FastAPI, Depends, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from app.database import get_db, engine
from app.models import Base, User, Mission
from datetime import datetime, timezone, date, timedelta
from app import models

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# === 1. DECLARAÇÃO DA FUNÇÃO (Precisa vir antes das rotas!) ===
def atualizar_ofensivas_da_casa(user, db: Session):
    hoje = date.today()
    ontem = hoje - timedelta(days=1)

    # Busca todas as missões diárias do usuário
    missoes = db.query(models.Mission).filter(
        models.Mission.user_id == user.id,
        models.Mission.is_daily == True
    ).all()

    for missao in missoes:
        # Se a missão está marcada como concluída, mas a data ficou no passado...
        if missao.completed and missao.last_completed_date and missao.last_completed_date < hoje:
            # Resetamos o status para fazer hoje de novo
            missao.completed = False

        # CHECAGEM DE QUEBRA DE STREAK:
        if missao.last_completed_date and missao.last_completed_date < ontem and not missao.completed:
            missao.streak = 0

    db.commit()


# === 2. ROTA DA PÁGINA INICIAL ===
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=engine)
    usuario_real = db.query(User).first()

    if not usuario_real:
        # Criando apenas o usuário padrão limpo e bem estruturado
        usuario_real = User(
            name="Igor", email="igor@email.com", level=1, xp=30)
        db.add(usuario_real)
        db.commit()
        db.refresh(usuario_real)

    # Executa a validação do calendário antes de renderizar a página
    atualizar_ofensivas_da_casa(usuario_real, db)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "usuario": usuario_real}
    )


# === 3. ROTA DE CONCLUIR MISSÃO ===
@app.post("/missions/{mission_id}/complete")
def complete_mission(mission_id: int, db: Session = Depends(get_db)):
    missao = db.query(models.Mission).filter(
        models.Mission.id == mission_id).first()
    if not missao:
        raise HTTPException(status_code=404, detail="Missão não encontrada")

    hoje = date.today()
    ontem = hoje - timedelta(days=1)

    if not missao.completed:
        # Se ele completou ontem, o streak aumenta!
        if missao.last_completed_date == ontem:
            missao.streak += 1
        # Se ele nunca completou ou quebrou o ciclo, reseta para 1
        elif missao.last_completed_date != hoje:
            missao.streak = 1

        missao.completed = True
        missao.last_completed_date = hoje

        # Soma o XP no usuário
        usuario = db.query(models.User).filter(
            models.User.id == missao.user_id).first()
        usuario.xp += missao.xp_reward

        # Regra de subida de nível
        if usuario.xp >= 100:
            usuario.level += 1
            usuario.xp = usuario.xp - 100

        db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# === 4. ROTA DE CRIAR MISSÃO ===
@app.post("/missions/create")
def create_mission(
    title: str = Form(...),
    xp_reward: int = Form(10),
    db: Session = Depends(get_db)
):
    usuario = db.query(User).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    nova_missao = Mission(title=title, xp_reward=xp_reward,
                          is_daily=True, user_id=usuario.id)
    db.add(nova_missao)
    db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# === 5. ROTA DE DELETAR MISSÃO (AJAX) ===
@app.post("/missions/{mission_id}/delete")
def delete_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Missão não encontrada")

    db.delete(mission)
    db.commit()

    return {"sucesso": True}
