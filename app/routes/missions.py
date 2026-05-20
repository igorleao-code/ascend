from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Mission, User

router = APIRouter(prefix="/missions", tags=["Missions"])

# ADICIONAMOS O response_class AQUI PARA CORRIGIR O REDIRECIONAMENTO


@router.post("/{mission_id}/complete", response_class=RedirectResponse)
def complete_mission(mission_id: int, db: Session = Depends(get_db)):
    # 1. Busca a missão no banco
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Missão não encontrada")

    # 2. Se já estiver concluída, apenas ignora e volta
    if mission.completed:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # 3. Marca como concluída
    mission.completed = True

    # 4. Busca o jogador dono da missão para dar a recompensa
    usuario = db.query(User).filter(User.id == mission.user_id).first()
    if usuario:
        usuario.xp += mission.xp_reward

        # Sistema de Level Up automático (Se passar de 100 XP, ganha um nível)
        if usuario.xp >= 100:
            usuario.level += 1
            usuario.xp = usuario.xp - 100  # Mantém a sobra do XP

    # Salva todas as alterações no banco
    db.commit()

    # Redireciona o navegador de volta para a página principal usando o status correto
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
