# Import all SQLAlchemy models, so that Base has them before being
# imported by Alembic
from app.db.base import Base  # noqa
from app.models.user import User  # noqa
from app.models.audit_log import AuditLog  # noqa
from app.models.refresh_token import RefreshToken  # noqa