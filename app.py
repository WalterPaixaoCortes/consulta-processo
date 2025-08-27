# app.py
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
from enum import Enum
from uuid import uuid4
from datetime import datetime
import json
import time

import solver

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Text,
    Enum as SAEnum,
    JSON as SAJSON,
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


# --------- App ---------
app = FastAPI(title="Consulta Processos API", version="1.0.0")


def do_processing(job_id: str):
    """Exemplo de 'worker' simples que processa o registro e atualiza o status."""
    db: Session = SessionLocal()
    try:
        msg: Optional[Message] = db.get(Message, job_id)
        if not msg:
            return  # registro removido/inesperado

        result = solver.run(msg.text)
        if result:
            msg.result_json = result
            msg.status = StatusEnum.DONE
            msg.updated_at = datetime.utcnow()
        else:
            msg.status = StatusEnum.ERROR
            msg.error_msg = "NOT SOLVED"
            msg.updated_at = datetime.utcnow()
        db.add(msg)
        db.commit()
    except Exception as e:
        try:
            msg = db.get(Message, job_id)
            if msg:
                msg.status = StatusEnum.ERROR
                msg.error_msg = f"{type(e).__name__}: {e}"
                msg.updated_at = datetime.utcnow()
                db.add(msg)
                db.commit()
        finally:
            pass
    finally:
        db.close()


@app.post(
    "/send",
    response_model=SendResponse,
    summary="Enfileira uma consulta e retorna um job id",
)
def send(
    payload: SendRequest, background: BackgroundTasks, db: Session = Depends(get_db)
):
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

    # dispara processamento em segundo plano (exemplo simples)
    background.add_task(do_processing, job_id)

    return SendResponse(id=job_id, status=StatusEnum.PENDING)


@app.get(
    "/retrieve/{job_id}",
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "Retorna pending, error ou done com o conteúdo.",
        },
        404: {"description": "ID não encontrado"},
    },
    summary="Consulta status pelo id",
)
def retrieve(job_id: str, db: Session = Depends(get_db)):
    record: Optional[Message] = db.get(Message, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="id not found")

    if record.status == StatusEnum.PENDING:
        return {"status": "pending"}
    elif record.status == StatusEnum.ERROR:
        return {"status": "error", "error": record.error_msg or "unknown error"}
    else:  # DONE
        return {"status": "done", "content": record.result_json or {}}
