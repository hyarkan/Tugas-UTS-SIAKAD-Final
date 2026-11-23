
"""Database-enforced grade audit trail.

Revision ID: 0008_grade_audit_trigger
Revises: 0007_grade_management
"""

from alembic import op

revision = "0008_grade_audit_trigger"
down_revision = "0007_grade_management"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE grade_audit_context (
            grade_id INTEGER PRIMARY KEY,
            changed_by INTEGER NOT NULL,
            reason TEXT,
            FOREIGN KEY (grade_id)
                REFERENCES krs_detail(id)
                ON DELETE CASCADE,
            FOREIGN KEY (changed_by)
                REFERENCES dosen(id)
                ON DELETE RESTRICT
        )
    """)

    op.execute("""
        CREATE TRIGGER trg_grade_audit_guard
        BEFORE UPDATE OF nilai ON krs_detail
        WHEN OLD.nilai IS NOT NEW.nilai
        BEGIN
            SELECT RAISE(
                ABORT,
                'Perubahan nilai memerlukan konteks audit'
            )
            WHERE NOT EXISTS (
                SELECT 1
                FROM grade_audit_context
                WHERE grade_id = OLD.id
            );
        END
    """)

    op.execute("""
        CREATE TRIGGER trg_grade_audit_history
        AFTER UPDATE OF nilai ON krs_detail
        WHEN OLD.nilai IS NOT NEW.nilai
        BEGIN
            INSERT INTO grade_history (
                grade_id,
                old_value,
                new_value,
                changed_by,
                changed_at,
                reason
            )
            SELECT
                NEW.id,
                OLD.nilai,
                NEW.nilai,
                ctx.changed_by,
                CURRENT_TIMESTAMP,
                ctx.reason
            FROM grade_audit_context AS ctx
            WHERE ctx.grade_id = NEW.id;

            DELETE FROM grade_audit_context
            WHERE grade_id = NEW.id;
        END
    """)


def downgrade():
    op.execute(
        "DROP TRIGGER IF EXISTS trg_grade_audit_history"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_grade_audit_guard"
    )
    op.execute(
        "DROP TABLE IF EXISTS grade_audit_context"
    )
