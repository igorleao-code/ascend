import time
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
    # 1. Garante que as tabelas existem no banco
    Base.metadata.create_all(bind=engine)

    # 2. Busca o primeiro usuário
    usuario_real = db.query(User).first()

    # 3. Se não existir, cria o usuário "Igor"
    if not usuario_real:
        usuario_real = User(
            name="Igor", email="igor@email.com", level=1, xp=30)
        db.add(usuario_real)
        db.commit()
        db.refresh(usuario_real)

    # 4. Busca as missões QUE PERTENCEM a esse usuário específico
    # (Em vez de buscar todas as missões globais)
    missoes_do_usuario = db.query(Mission).filter(
        Mission.user_id == usuario_real.id).all()

    # 5. Envia o usuário e as missões dele para o HTML
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "usuario": usuario_real,
            "missions": missoes_do_usuario  # <-- Garanta que está a enviar as missões aqui!
        }
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
    # Busca o usuário no banco de dados
    usuario = db.query(User).first()

    # Segurança básica: se não houver usuário criado, impede a ação
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Cria o objeto da nova missão vinculando ao ID do usuário encontrado
    nova_missao = Mission(
        title=title,
        xp_reward=xp_reward,
        is_daily=True,
        user_id=usuario.id  # <-- O vínculo que ativa a Chave Estrangeira
    )

    # Salva as alterações no banco de dados
    db.add(nova_missao)
    db.commit()

    # Redireciona de volta para a página inicial com o "Cache-Buster"
    return RedirectResponse(url=f"/?t={time.time()}", status_code=status.HTTP_303_SEE_OTHER)


# === 5. ROTA DE DELETAR MISSÃO (AJAX) ===
@app.post("/missions/{mission_id}/delete")
def delete_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Missão não encontrada")

    db.delete(mission)
    db.commit()

    return {"sucesso": True}
