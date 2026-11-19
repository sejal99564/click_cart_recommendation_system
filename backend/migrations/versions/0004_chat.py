from alembic import op
import sqlalchemy as sa

revision = "0004_chat"
down_revision = "0003_collections"


def upgrade():
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_table(
        "chat_turns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.String(32), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.String(2000), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("products", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
    )
    op.create_index("ix_chat_turns_conversation_id", "chat_turns", ["conversation_id"])


def downgrade():
    op.drop_table("chat_turns")
    op.drop_table("conversations")
