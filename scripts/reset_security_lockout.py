"""Emergency helper for RustDesk AddressBook.

Run inside the container if a test instance was locked by a broken security-signature
migration:

    docker exec -it rustdesk-addressbook python /app/scripts/reset_security_lockout.py

It clears authentication lockout events and re-signs existing user security state using
the current data/config.json SECURITY_SIGNING_KEY. It does not change passwords or 2FA.
"""
from app import _sign_user_security_state, create_app
from app.extensions import db
from app.models import AuthEvent, User

app = create_app()
with app.app_context():
    users = User.query.all()
    for user in users:
        _sign_user_security_state(user)
    deleted = AuthEvent.query.filter(AuthEvent.success.is_(False)).delete(synchronize_session=False)
    db.session.commit()
    print(f"Re-signed {len(users)} user(s). Deleted {deleted} failed auth event(s).")
