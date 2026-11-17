from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Category

# Para acrescentar categorias basta juntar uma linha aqui (o arranque insere as que faltam).
INITIAL_CATEGORIES = [
    ("entradas", "Entradas"),
    ("sopas", "Sopas"),
    ("carnes", "Carnes"),
    ("peixes", "Peixes"),
    ("massas-arroz", "Massas e arroz"),
    ("vegetarianas", "Vegetarianas"),
    ("sobremesas", "Sobremesas"),
    ("pequenos-almocos", "Pequenos-almoços"),
    ("bebidas", "Bebidas"),
]


def ensure_categories(db: Session) -> None:
    existing = set(db.scalars(select(Category.slug)))
    for order, (slug, name) in enumerate(INITIAL_CATEGORIES):
        if slug not in existing:
            db.add(Category(slug=slug, name=name, sort_order=order))
    db.commit()
