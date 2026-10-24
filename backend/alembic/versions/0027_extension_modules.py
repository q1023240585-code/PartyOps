"""党务扩展模块：党员名册、党费、考核评议、群团、品牌舆情、标准化对标、教育培训。

Revision ID: 0027
Revises: 0026

中核四〇四定制扩展：12 张业务台账表，全部遵循既有审计与版本字段约定，
不改动既有表结构，可独立回滚。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

AUDIT_COLUMNS = [
    sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
]

UPDATED_TRIGGER = """
CREATE TRIGGER {table}_updated_at AFTER UPDATE ON {table}
BEGIN
  UPDATE {table} SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""


def _audit():
    return [column.copy() for column in AUDIT_COLUMNS]


def upgrade() -> None:
    op.create_table(
        "party_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, index=True),
        sa.Column("gender", sa.String(length=8), nullable=False, server_default="男"),
        sa.Column("birth_date", sa.DateTime(timezone=True)),
        sa.Column("joined_party_at", sa.DateTime(timezone=True), index=True),
        sa.Column("branch", sa.String(length=160), nullable=False, index=True),
        sa.Column("party_post", sa.String(length=80), nullable=False, server_default="党员"),
        sa.Column("education", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("member_kind", sa.String(length=24), nullable=False, server_default="正式党员", index=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="在册", index=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "party_fee_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=12), nullable=False, server_default="income", index=True),
        sa.Column("member_name", sa.String(length=80), nullable=False, server_default="", index=True),
        sa.Column("member_ref", sa.String(length=36), sa.ForeignKey("party_members.id", ondelete="SET NULL"), index=True),
        sa.Column("branch", sa.String(length=160), nullable=False, server_default="", index=True),
        sa.Column("year", sa.Integer(), nullable=False, index=True),
        sa.Column("month", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("base_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("ratio", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="已缴", index=True),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("method", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("purpose", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("approver", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "democratic_reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False, index=True),
        sa.Column("member_name", sa.String(length=80), nullable=False, index=True),
        sa.Column("member_ref", sa.String(length=36), sa.ForeignKey("party_members.id", ondelete="SET NULL"), index=True),
        sa.Column("branch", sa.String(length=160), nullable=False, server_default="", index=True),
        sa.Column("self_rating", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("peer_rating", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("final_rating", sa.String(length=24), nullable=False, server_default="未定格", index=True),
        sa.Column("issues_found", sa.Text(), nullable=False, server_default=""),
        sa.Column("rectification", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="进行中", index=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "assessment_indicators",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False, index=True),
        sa.Column("category", sa.String(length=80), nullable=False, index=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("score", sa.Numeric(6, 1), nullable=False, server_default="0"),
        sa.Column("owner_role", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "assessment_scores",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("indicator_ref", sa.String(length=36), sa.ForeignKey("assessment_indicators.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("year", sa.Integer(), nullable=False, index=True),
        sa.Column("branch", sa.String(length=160), nullable=False, index=True),
        sa.Column("score_obtained", sa.Numeric(6, 1), nullable=False, server_default="0"),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("assessor", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "mass_activities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=24), nullable=False, server_default="union", index=True),
        sa.Column("title", sa.String(length=240), nullable=False, index=True),
        sa.Column("held_at", sa.DateTime(timezone=True)),
        sa.Column("location", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("participants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("budget", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("organizer", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="已举办", index=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "league_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, index=True),
        sa.Column("gender", sa.String(length=8), nullable=False, server_default="男"),
        sa.Column("birth_date", sa.DateTime(timezone=True)),
        sa.Column("league_joined_at", sa.DateTime(timezone=True), index=True),
        sa.Column("branch", sa.String(length=160), nullable=False, index=True),
        sa.Column("league_post", sa.String(length=80), nullable=False, server_default="团员"),
        sa.Column("education", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="在册", index=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "league_elections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("branch", sa.String(length=160), nullable=False, index=True),
        sa.Column("term", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("election_date", sa.DateTime(timezone=True)),
        sa.Column("new_secretary", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("committee", sa.Text(), nullable=False, server_default=""),
        sa.Column("approval_status", sa.String(length=24), nullable=False, server_default="待报批", index=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "brand_projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=240), nullable=False, index=True),
        sa.Column("category", sa.String(length=60), nullable=False, server_default="党建品牌", index=True),
        sa.Column("slogan", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="培育中", index=True),
        sa.Column("highlights", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "public_opinion_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=240), nullable=False, index=True),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="", index=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("severity", sa.String(length=24), nullable=False, server_default="一般", index=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("disposition", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="登记", index=True),
        sa.Column("responder", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "standard_check_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("branch", sa.String(length=160), nullable=False, index=True),
        sa.Column("category", sa.String(length=80), nullable=False, index=True),
        sa.Column("item", sa.String(length=240), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False, server_default=""),
        sa.Column("compliant", sa.String(length=24), nullable=False, server_default="未查", index=True),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )
    op.create_table(
        "training_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=240), nullable=False, index=True),
        sa.Column("category", sa.String(length=60), nullable=False, server_default="集中培训", index=True),
        sa.Column("start_date", sa.DateTime(timezone=True)),
        sa.Column("end_date", sa.DateTime(timezone=True)),
        sa.Column("hours", sa.Numeric(6, 1), nullable=False, server_default="0"),
        sa.Column("participants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("branch", sa.String(length=160), nullable=False, server_default="", index=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_audit(),
    )


def downgrade() -> None:
    for table in (
        "training_records", "standard_check_items", "public_opinion_items",
        "brand_projects", "league_elections", "league_members", "mass_activities",
        "assessment_scores", "assessment_indicators", "democratic_reviews",
        "party_fee_records", "party_members",
    ):
        op.drop_table(table)
