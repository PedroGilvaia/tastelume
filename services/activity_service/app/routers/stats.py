"""Estatísticas do utilizador autenticado, calculadas a partir dos eventos recebidos.

Atenção: são *atividade registada* (quantas visualizações/gostos/comentários chegaram ao longo do
período), não totais atuais. Um «gosto» retirado não desce aqui; os totais atuais de cada receita
vêm do Recipe Service (contadores). Receitas entretanto apagadas continuam a contar nos totais.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from .. import clients
from ..auth import AuthUser, get_current_user
from ..database import get_db
from ..models import Event
from ..schemas import DayPoint, StatsOut, StatsTotals, TopRecipe

router = APIRouter(prefix="/stats", tags=["stats"])

RECIPE_METRICS = ("view", "like", "comment", "rating", "share")


def _window(days: int) -> tuple[date, datetime]:
    """Janela de `days` dias UTC que inclui hoje: devolve o primeiro dia e o seu início."""
    first = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    return first, datetime(first.year, first.month, first.day, tzinfo=timezone.utc)


def _on_my_recipes(user_id: int, since: datetime):
    """Eventos de outras pessoas (ou visitantes) nas receitas deste utilizador."""
    return (
        Event.recipe_owner_id == user_id,
        Event.recipe_id.is_not(None),
        Event.event_type.in_(RECIPE_METRICS),
        or_(Event.actor_id.is_(None), Event.actor_id != user_id),
        Event.created_at >= since,
    )


def _count(db: Session, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(Event).where(*conditions)) or 0


@router.get("/me", response_model=StatsOut)
def my_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    _, since = _window(days)
    per_type = dict(db.execute(
        select(Event.event_type, func.count()).where(*_on_my_recipes(user.id, since)).group_by(Event.event_type)
    ).all())
    return StatsOut(
        period_days=days,
        totals=StatsTotals(
            views=per_type.get("view", 0), likes=per_type.get("like", 0),
            comments=per_type.get("comment", 0), ratings=per_type.get("rating", 0),
            shares=per_type.get("share", 0),
            new_followers=_count(db, Event.event_type == "follow", Event.target_user_id == user.id,
                                 Event.created_at >= since),
            recipes_published=_count(db, Event.event_type == "recipe_created", Event.actor_id == user.id,
                                     Event.created_at >= since),
        ),
    )


@router.get("/me/timeline", response_model=list[DayPoint])
def my_timeline(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Um ponto por dia (UTC), do mais antigo para hoje; dias sem atividade vêm a zero."""
    first, since = _window(days)
    day = func.date(Event.created_at)
    rows = db.execute(
        select(day, Event.event_type, func.count())
        .where(*_on_my_recipes(user.id, since)).group_by(day, Event.event_type)
    ).all()
    series = {first + timedelta(days=i): {m: 0 for m in RECIPE_METRICS} for i in range(days)}
    for d, kind, n in rows:
        key = date.fromisoformat(str(d)[:10])
        if key in series:
            series[key][kind] = n
    return [
        DayPoint(date=d, views=v["view"], likes=v["like"], comments=v["comment"],
                 ratings=v["rating"], shares=v["share"])
        for d, v in series.items()
    ]


@router.get("/me/top-recipes", response_model=list[TopRecipe])
def my_top_recipes(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(5, ge=1, le=20),
    sort: Literal["views", "likes", "comments", "ratings", "shares"] = "views",
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """As receitas do utilizador com mais atividade no período. `title` é null se o Recipe Service não responder."""
    _, since = _window(days)

    def total(kind: str):
        return func.coalesce(func.sum(case((Event.event_type == kind, 1), else_=0)), 0)

    cols = {m: total(m).label(m) for m in RECIPE_METRICS}
    rows = db.execute(
        select(Event.recipe_id, *cols.values()).where(*_on_my_recipes(user.id, since))
        .group_by(Event.recipe_id)
        .order_by(cols[sort[:-1]].desc(), Event.recipe_id.desc()).limit(limit)
    ).all()
    titles = clients.recipes_map({r.recipe_id for r in rows})
    return [
        TopRecipe(
            recipe_id=r.recipe_id, title=(titles.get(r.recipe_id) or {}).get("title"),
            views=r.view, likes=r.like, comments=r.comment, ratings=r.rating, shares=r.share,
        )
        for r in rows
    ]
