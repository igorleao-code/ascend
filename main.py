from app.security import gerar_hash_senha, verificar_senha
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
from fastapi import Cookie

app = FastAPI()

Base.metadata.create_all(bind=engine)

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
def home(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Cookie(None)
):
    if not user_id:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Busca o usuário logado
    usuario_real = db.query(User).filter(User.id == int(user_id)).first()

    if not usuario_real:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Força o SQLAlchemy a atualizar os dados do usuário e buscar as suas missões frescas
    db.refresh(usuario_real)

    return templates.TemplateResponse(
        "index.html",
        # <--- Passando apenas o usuario_real atualizado
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
def criar_missao(
    title: str = Form(...),
    xp_reward: int = Form(...),
    is_daily: bool = Form(...),
    db: Session = Depends(get_db),
    user_id: str = Cookie(None)  # <--- Lendo quem está logado
):
    # Se alguém tentar criar missão sem estar logado, manda pro login
    if not user_id:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Cria a nova missão amarrada ao ID do usuário logado
    nova_missao = Mission(
        title=title,
        xp_reward=xp_reward,
        is_daily=is_daily,
        completed=False,
        streak=0,
        user_id=int(user_id)  # <--- O segredo está aqui!
    )

    db.add(nova_missao)
    db.commit()

    # Redireciona de volta para a Home atualizada
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

# === ROTA PARA MOSTRAR A TELA DE CADASTRO (GET) ===


@app.get("/cadastro", response_class=HTMLResponse)
def mostrar_tela_cadastro(request: Request):
    return templates.TemplateResponse("cadastro.html", {"request": request})


# === ROTA PARA PROCESSAR O FORMULÁRIO DE CADASTRO (POST) ===
@app.post("/cadastro")
def processar_cadastro(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Verifica se o e-mail já está cadastrado no banco
    usuario_existente = db.query(User).filter(User.email == email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=400, detail="Este e-mail já está cadastrado.")

    senha_criptografada = gerar_hash_senha(password)

    novo_usuario = User(
        name=name,
        email=email,
        hashed_password=senha_criptografada,
        level=1,
        xp=0
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    # 5. Por enquanto, redireciona para a Home (no futuro será para o Login)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

# === ROTA PARA MOSTRAR A TELA DE LOGIN (GET) ===


@app.get("/login", response_class=HTMLResponse)
def mostrar_tela_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# === ROTA PARA PROCESSAR O LOGIN (POST) ===


@app.post("/login")
def processar_login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    usuario = db.query(User).filter(User.email == email).first()

    if not usuario or not verificar_senha(password, usuario.hashed_password):
        raise HTTPException(
            status_code=400, detail="E-mail ou senha incorretos.")

    print(f"Usuário {usuario.name} logado com sucesso!")

    # 1. Criamos a resposta de redirecionamento
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # 2. Salvamos o ID do usuário num cookie seguro dentro do navegador
    response.set_cookie(key="user_id", value=str(usuario.id), httponly=True)

    return response

# === ROTA PARA FAZER LOGOUT (SAIR) ===


@app.get("/logout")
def processar_logout():
    # 1. Prepara o redirecionamento para a tela de login
    response = RedirectResponse(
        url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # 2. Apaga o cookie do navegador definindo o valor como vazio
    response.delete_cookie(key="user_id")

    print("Usuário deslogado com sucesso. Cookie removido!")
    return response
