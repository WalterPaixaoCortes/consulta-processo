# app.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
from enum import Enum
from uuid import uuid4
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Text,
    Enum as SAEnum,
    JSON as SAJSON,
    select,
    func,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# --------- Configuração do banco ---------
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class StatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    status = Column(
        SAEnum(StatusEnum), nullable=False, index=True, default=StatusEnum.PENDING
    )
    result_json = Column(SAJSON, nullable=True)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


Base.metadata.create_all(bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------- Schemas ---------
class SendRequest(BaseModel):
    text: str


class SendResponse(BaseModel):
    id: str
    status: StatusEnum = StatusEnum.PENDING


class RetrieveDoneResponse(BaseModel):
    status: StatusEnum
    content: Dict[str, Any]


class RetrievePendingResponse(BaseModel):
    status: StatusEnum


class RetrieveErrorResponse(BaseModel):
    status: StatusEnum
    error: str


class NextResponse(BaseModel):
    id: str
    text: str
    status: StatusEnum


# --------- App ---------
app = FastAPI(title="Mini Queue API", version="1.1.0")


@app.post(
    "/send", response_model=SendResponse, summary="Enfileira um texto e retorna um id"
)
def send(payload: SendRequest, db: Session = Depends(get_db)):
    job_id = str(uuid4())
    record = Message(
        id=job_id,
        text=payload.text,
        status=StatusEnum.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    return SendResponse(id=job_id, status=StatusEnum.PENDING)


@app.get(
    "/retrieve/{job_id}",
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "Retorna pending (inclui processing), error ou done com o conteúdo.",
        },
        404: {"description": "ID não encontrado"},
    },
    summary="Consulta status pelo id",
)
def retrieve(job_id: str, db: Session = Depends(get_db)):
    record: Optional[Message] = db.get(Message, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="id not found")

    if record.status in (StatusEnum.PENDING, StatusEnum.PROCESSING):
        return {"status": "pending"}  # mantém contrato original
    elif record.status == StatusEnum.ERROR:
        return {"status": "error", "error": record.error_msg or "unknown error"}
    else:  # DONE
        return {"status": "done", "content": record.result_json or {}}


@app.post(
    "/next",
    response_model=NextResponse,
    responses={
        200: {
            "description": "Reserva o registro mais antigo pendente e o marca como processing."
        },
        404: {"description": "Não há registros pendentes."},
        409: {"description": "Já existe um registro em processamento."},
    },
    summary="Busca e reserva o mais antigo em pending, se não houver outro em processing",
)
def next_pending(db: Session = Depends(get_db)):
    """
    Regras:
    - Se existir QUALQUER registro em PROCESSING -> 409
    - Senão, pega o mais antigo em PENDING, marca como PROCESSING e retorna
    """
    # Inicia uma transação para garantir atomicidade
    with db.begin():
        processing_exists = db.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.status == StatusEnum.PROCESSING)
        ).scalar_one()

        processing_exists = 0
        if processing_exists and processing_exists > 0:
            raise HTTPException(status_code=409, detail="a job is already processing")

        # pega o mais antigo pending
        record: Optional[Message] = (
            db.execute(
                select(Message)
                .where(Message.status == StatusEnum.PENDING)
                .order_by(Message.created_at.asc())
                .limit(1)
            )
            .scalars()
            .first()
        )

        if not record:
            raise HTTPException(status_code=404, detail="no pending jobs")

        # reserva: marca como processing
        record.status = StatusEnum.PROCESSING
        record.updated_at = datetime.utcnow()
        db.add(record)
        # commit acontece ao sair do bloco with

    return NextResponse(id=record.id, text=record.text, status=record.status)


# --- Utilidades opcionais para "concluir" ou "falhar" um job reservado ---
# Essas rotas não foram pedidas, mas geralmente o worker precisa finalizar o job:


class FinishRequest(BaseModel):
    content: Dict[str, Any]


@app.post(
    "/finish/{job_id}", summary="(Opcional) Marca um job como DONE com result_json"
)
def finish(job_id: str, payload: FinishRequest, db: Session = Depends(get_db)):
    record = db.get(Message, job_id)
    if not record:
        raise HTTPException(404, "id not found")
    if record.status != StatusEnum.PROCESSING:
        raise HTTPException(409, "job is not in processing")
    record.result_json = payload.content
    record.status = StatusEnum.DONE
    record.updated_at = datetime.utcnow()
    db.add(record)
    db.commit()
    return {"status": "done"}


class FailRequest(BaseModel):
    error: str


@app.post("/fail/{job_id}", summary="(Opcional) Marca um job como ERROR")
def fail(job_id: str, payload: FailRequest, db: Session = Depends(get_db)):
    record = db.get(Message, job_id)
    if not record:
        raise HTTPException(404, "id not found")
    if record.status != StatusEnum.PROCESSING:
        raise HTTPException(409, "job is not in processing")
    record.error_msg = payload.error
    record.status = StatusEnum.ERROR
    record.updated_at = datetime.utcnow()
    db.add(record)
    db.commit()
    return {"status": "error", "error": payload.error}


# ... (mesmo código anterior acima)

from fastapi import Query
from typing import List


# ---- Schemas novos/ajustados ----
class JobOut(BaseModel):
    id: str
    text: str
    status: StatusEnum
    result_json: Optional[Dict[str, Any]] = None
    error_msg: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # pydantic v2


@app.get(
    "/jobs",
    response_model=List[JobOut],
    summary="Lista jobs (tudo ou filtrado por status)",
    responses={
        200: {"description": "Lista paginada de jobs"},
    },
)
def list_jobs(
    db: Session = Depends(get_db),
    status: Optional[StatusEnum] = Query(
        default=None, description="Filtrar por status"
    ),
    limit: int = Query(default=50, ge=1, le=500, description="Máximo de itens"),
    offset: int = Query(default=0, ge=0, description="Deslocamento para paginação"),
    newest: bool = Query(
        default=False, description="Ordenar do mais novo para o mais antigo"
    ),
):
    stmt = select(Message)
    if status:
        stmt = stmt.where(Message.status == status)
    order_col = Message.created_at.desc() if newest else Message.created_at.asc()
    stmt = stmt.order_by(order_col).offset(offset).limit(limit)

    items = db.execute(stmt).scalars().all()
    return [JobOut.model_validate(i) for i in items]
