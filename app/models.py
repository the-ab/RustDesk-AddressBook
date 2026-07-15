from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


user_groups = db.Table(
    "user_groups",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False, default="")
    role = db.Column(db.String(16), nullable=False, default="user", index=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    auth_provider = db.Column(db.String(16), nullable=False, default="local", index=True)
    oidc_issuer = db.Column(db.String(255), nullable=True, index=True)
    oidc_subject = db.Column(db.String(255), nullable=True, index=True)
    display_name = db.Column(db.String(180), nullable=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    preferred_language = db.Column(db.String(8), nullable=False, default="de")
    preferred_theme = db.Column(db.String(16), nullable=False, default="light")
    totp_secret_encrypted = db.Column(db.Text, nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    totp_recovery_hashes = db.Column(db.Text, nullable=True)
    security_signature = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    groups = db.relationship("Group", secondary=user_groups, back_populates="users", lazy="selectin")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if self.auth_provider != "local" or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        return bool(self.active)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AuthEvent(db.Model):
    __tablename__ = "auth_events"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    username = db.Column(db.String(120), nullable=True, index=True)
    ip_address = db.Column(db.String(64), nullable=True, index=True)
    user_agent = db.Column(db.String(255), nullable=True)
    success = db.Column(db.Boolean, default=False, nullable=False, index=True)
    message = db.Column(db.Text, nullable=True)


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    color = db.Column(db.String(32), default="secondary", nullable=False)
    icon = db.Column(db.String(64), default="collection", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    devices = db.relationship("Device", back_populates="group", lazy="dynamic")
    users = db.relationship("User", secondary=user_groups, back_populates="groups", lazy="selectin")


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ImportBlocklistEntry(db.Model):
    __tablename__ = "import_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    rustdesk_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    device_name = db.Column(db.String(180), nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    rustdesk_id = db.Column(db.String(80), nullable=False, index=True)
    encrypted_password = db.Column(db.Text, nullable=True)
    customer = db.Column(db.String(180), nullable=True, index=True)
    location = db.Column(db.String(180), nullable=True)
    os = db.Column(db.String(64), nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    favorite = db.Column(db.Boolean, default=False, nullable=False)
    online = db.Column(db.Boolean, default=False, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    group = db.relationship("Group", back_populates="devices")
