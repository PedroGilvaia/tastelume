"""comments, ratings, likes, favoritos, partilhas, mensagens

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def TS():
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", TS(), nullable=False),
        sa.Column("updated_at", TS(), nullable=True),
    )
    op.create_index("ix_comments_recipe_created", "comments", ["recipe_id", "created_at"])
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", TS(), nullable=False),
        sa.Column("updated_at", TS(), nullable=False),
        sa.UniqueConstraint("recipe_id", "user_id", name="uq_rating_recipe_user"),
        sa.CheckConstraint("score BETWEEN 1 AND 5", name="ck_rating_score"),
    )
    op.create_table(
        "likes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", TS(), nullable=False),
        sa.UniqueConstraint("recipe_id", "user_id", name="uq_like_recipe_user"),
    )
    op.create_table(
        "favorite_collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("created_at", TS(), nullable=False),
    )
    op.create_index("uq_collection_user_name", "favorite_collections", ["user_id", sa.text("lower(name)")], unique=True)
    op.create_table(
        "favorite_collection_recipes",
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("favorite_collections.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("recipe_id", sa.Integer(), primary_key=True),
        sa.Column("added_at", TS(), nullable=False),
    )
    op.create_index("ix_fcr_recipe_id", "favorite_collection_recipes", ["recipe_id"])
    op.create_table(
        "recipe_shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("created_at", TS(), nullable=False),
    )
    op.create_index("ix_shares_recipient", "recipe_shares", ["recipient_id", "created_at"])
    op.create_index("ix_shares_recipe", "recipe_shares", ["recipe_id"])
    op.create_table(
        "direct_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", TS(), nullable=False),
        sa.Column("read_at", TS(), nullable=True),
        sa.CheckConstraint("sender_id <> recipient_id", name="ck_message_not_self"),
    )
    op.create_index("ix_messages_pair", "direct_messages", ["sender_id", "recipient_id"])
    op.create_index("ix_messages_recipient_read", "direct_messages", ["recipient_id", "read_at"])


def downgrade() -> None:
    for table in ("direct_messages", "recipe_shares", "favorite_collection_recipes", "favorite_collections",
                  "likes", "ratings", "comments"):
        op.drop_table(table)
