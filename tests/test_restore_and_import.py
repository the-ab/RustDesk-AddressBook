from __future__ import annotations

import io
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import event
from werkzeug.datastructures import FileStorage

import app as application
import app.restore as restore
from app.crypto import encrypt_value
from app.extensions import db
from app.helpers import parse_csv_upload
from app.models import Device, Setting, User
from tests.conftest import set_csrf


@pytest.fixture
def store(clean_app):
    data_dir = Path(clean_app.config['DATA_DIR'])
    cfg_file = data_dir / 'config.json'
    original = cfg_file.read_bytes()
    with clean_app.app_context():
        admin = User(username='restore-admin', role='admin', active=True, auth_provider='local')
        admin.set_password('restore-regression-password')
        db.session.add(admin)
        application._sign_user_security_state(admin)
        db.session.add(Device(name='original', rustdesk_id='123', encrypted_password=encrypt_value('original-password')))
        db.session.commit()
        snapshot = application._sqlite_backup_bytes(data_dir / 'addressbook.db')
    yield data_dir, snapshot, json.loads(original)
    with restore.maintenance_lock(data_dir, exclusive=True):
        restore.recover_pending_restore(data_dir)
        restore.atomic_write(cfg_file, original)
        restore.atomic_write(data_dir / '.restore-generation', os.urandom(16))
    application._reload_runtime_keys(clean_app)


def full_archive(snapshot, cfg, extra=None):
    result = io.BytesIO()
    payloads = {
        'manifest.json': json.dumps({'format': 'rustdesk-addressbook-full-backup', 'version': 1}).encode(),
        'data/addressbook.db': snapshot,
        'data/config.json': json.dumps(cfg).encode(),
        **(extra or {}),
    }
    with tarfile.open(fileobj=result, mode='w:gz') as archive:
        for name, content in payloads.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
    return result.getvalue()


def test_schema_rejects_named_but_unusable_tables(clean_app, tmp_path):
    candidate = tmp_path / 'candidate.db'
    with sqlite3.connect(candidate) as connection:
        for name in ('users', 'devices', 'groups', 'settings'):
            connection.execute(f'CREATE TABLE {name}(unrelated TEXT)')
    with clean_app.app_context(), pytest.raises(ValueError, match='Spalten'):
        application._validate_addressbook_sqlite(candidate)


def test_schema_rejects_orphan_group(store, clean_app, tmp_path):
    _, snapshot, _ = store
    candidate = tmp_path / 'candidate.db'
    candidate.write_bytes(snapshot)
    with sqlite3.connect(candidate) as connection:
        connection.execute('UPDATE devices SET group_id=99999')
    with clean_app.app_context(), pytest.raises(ValueError, match='Gruppen'):
        application._validate_addressbook_sqlite(candidate)


def test_database_restore_rejects_wrong_key_before_replacement(store, clean_app, tmp_path):
    data_dir, snapshot, _ = store
    candidate = tmp_path / 'wrong-key.db'
    candidate.write_bytes(snapshot)
    with sqlite3.connect(candidate) as connection:
        connection.execute('UPDATE devices SET encrypted_password=?', (Fernet(Fernet.generate_key()).encrypt(b'other').decode(),))
    with clean_app.app_context(), pytest.raises(ValueError, match='schlüssel'):
        application._restore_database_from_file(candidate, data_dir / 'addressbook.db', tmp_path)
    with sqlite3.connect(data_dir / 'addressbook.db') as connection:
        assert connection.execute('SELECT name FROM devices').fetchone() == ('original',)


def test_full_restore_rolls_back_every_file_after_write_failure(store, clean_app, monkeypatch):
    data_dir, snapshot, cfg = store
    old_config = (data_dir / 'config.json').read_bytes()
    target = data_dir / 'ssh' / 'test-key'
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(b'old-key')
    original_write = restore.atomic_write
    failed = False

    def failing_write(path, content, mode=0o600):
        nonlocal failed
        if path == target and not failed:
            failed = True
            raise OSError('injected disk write failure')
        return original_write(path, content, mode)

    cfg['SECRET_KEY'] = 'new-test-session-key'
    monkeypatch.setattr(restore, 'atomic_write', failing_write)
    with clean_app.app_context(), pytest.raises(OSError, match='injected'):
        application._safe_extract_full_backup(full_archive(snapshot, cfg, {'data/ssh/test-key': b'new-key'}), data_dir)
    assert (data_dir / 'config.json').read_bytes() == old_config
    assert target.read_bytes() == b'old-key'
    assert not (data_dir / '.restore-transaction').exists()
    with clean_app.app_context():
        assert Device.query.one().name == 'original'


def test_full_restore_reloads_keys_and_disposes_other_worker_connections(store, clean_app):
    data_dir, snapshot, cfg = store
    other_worker = application.create_app()
    cfg['SECRET_KEY'] = 'new-session-test-key'
    with clean_app.app_context():
        application._safe_extract_full_backup(full_archive(snapshot, cfg), data_dir)
    assert clean_app.config['SECRET_KEY'] == cfg['SECRET_KEY']
    assert other_worker.config['SECRET_KEY'] != cfg['SECRET_KEY']
    response = other_worker.test_client().get('/healthz')
    assert response.status_code == 200
    response.close()
    assert other_worker.config['SECRET_KEY'] == cfg['SECRET_KEY']


def test_full_restore_rejects_mismatched_configuration(store, clean_app):
    data_dir, snapshot, cfg = store
    old = (data_dir / 'config.json').read_bytes()
    cfg['SECURITY_SIGNING_KEY'] = 'different-signing-key'
    with clean_app.app_context(), pytest.raises(ValueError, match='signaturen'):
        application._safe_extract_full_backup(full_archive(snapshot, cfg), data_dir)
    assert (data_dir / 'config.json').read_bytes() == old


def test_pending_restore_blocks_requests_and_recovers_after_process_exit(store, clean_app):
    data_dir, snapshot, _ = store
    old = (data_dir / 'config.json').read_bytes()
    code = '''
import os
from pathlib import Path
from app import restore
root = Path(os.environ['APP_DATA_DIR'])
original = restore.atomic_write
def die_after_write(path, content, mode=0o600):
    original(path, content, mode)
    if path == root / 'config.json':
        os._exit(9)
restore.atomic_write = die_after_write
with restore.maintenance_lock(root, exclusive=True):
    restore.replace_files(root, {'addressbook.db': (b'NEW DATABASE', 0o600), 'config.json': (b'NEW CONFIG', 0o600)}, database_snapshot=(root / 'snapshot').read_bytes())
'''
    (data_dir / 'snapshot').write_bytes(snapshot)
    result = subprocess.run([sys.executable, '-c', code], env={**os.environ, 'APP_DATA_DIR': str(data_dir)}, timeout=15)
    assert result.returncode == 9
    page = clean_app.test_client().get('/healthz')
    assert page.status_code == 503
    page.close()
    with clean_app.app_context():
        db.session.remove()
        db.engine.dispose()
    # create_app recovers before it opens the damaged database/config.
    fresh_worker = application.create_app()
    assert (data_dir / 'config.json').read_bytes() == old
    assert not (data_dir / '.restore-transaction').exists()
    with fresh_worker.app_context():
        assert Device.query.one().name == 'original'
    (data_dir / 'snapshot').unlink()


def test_restore_refuses_an_active_other_request(store, clean_app, tmp_path):
    data_dir, snapshot, _ = store
    candidate = tmp_path / 'candidate.db'
    candidate.write_bytes(snapshot)
    # Independent open file descriptions reproduce concurrent worker locks.
    with restore.maintenance_lock(data_dir), clean_app.app_context(), pytest.raises(ValueError, match='gesperrt'):
        application._restore_database_from_file(candidate, data_dir / 'addressbook.db', tmp_path)


def test_backup_names_do_not_overwrite_even_on_random_collision(store, clean_app, tmp_path, monkeypatch):
    data_dir, _, _ = store
    with clean_app.app_context():
        monkeypatch.setattr(application.secrets, 'token_hex', lambda size: 'fixed-token')
        filename = application._create_database_backup(data_dir / 'addressbook.db', tmp_path)
        original = (tmp_path / filename).read_bytes()
        db.session.add(Device(name='new', rustdesk_id='456'))
        db.session.commit()
        with pytest.raises(ValueError, match='Backupname'):
            application._create_database_backup(data_dir / 'addressbook.db', tmp_path)
        assert (tmp_path / filename).read_bytes() == original


def test_duplicate_ids_all_receive_one_live_query(clean_app, monkeypatch):
    calls = []
    with clean_app.app_context():
        db.session.add_all([Device(name='one', rustdesk_id=' 123 '), Device(name='two', rustdesk_id='123')])
        db.session.commit()
        monkeypatch.setattr(application, '_get_status_settings', lambda: {'hbbs_host': 'localhost', 'hbbs_port': 21116, 'hbbs_requester_id': '', 'hbbs_timeout': 1, 'hbbs_batch_size': 1})

        def query(host, port, ids, **kwargs):
            calls.append(ids)
            return SimpleNamespace(online={'123': True}, response_states_hex='01')

        monkeypatch.setattr(application, 'query_hbbs_online_status', query)
        result = application._sync_hbbs_live_status(trigger='manual')
        assert result['updated'] == result['online'] == 2
        assert all(device.online for device in Device.query.all())
        assert calls == [['123']]


@pytest.mark.parametrize('content', [b'name,id\na,123,extra\n', b'name,id\na\n', b'name,name,id\na,b,123\n', b'name,id\na,\xff\n', b'name,wrong\na,123\n', b'name,id\n"unterminated,123\n'])
def test_csv_rejects_malformed_input(content):
    with pytest.raises(ValueError):
        parse_csv_upload(FileStorage(stream=io.BytesIO(content)))


def test_csv_accepts_bom_semicolon_and_quoted_values():
    content = '\ufeffName;RustDesk-ID;notes\n"example;device";123;"two\nlines"\n'.encode()
    assert parse_csv_upload(FileStorage(stream=io.BytesIO(content))) == [{'name': 'example;device', 'rustdesk-id': '123', 'notes': 'two\nlines'}]


def test_invalid_csv_route_preserves_all_rows(store, clean_app, client):
    csrf = set_csrf(client)
    with client.session_transaction() as session:
        session['_user_id'] = '1'
        session['_fresh'] = True
        session['auth_session_version'] = 1
    page = client.post('/import', data={'csrf_token': csrf, 'csv_file': (io.BytesIO(b'name,id\nvalid,123\nbroken,456,extra\n'), 'test.csv')}, content_type='multipart/form-data')
    assert page.status_code == 302
    page.close()
    with clean_app.app_context():
        assert Device.query.count() == 1


def test_zip_rejects_duplicate_flattened_targets_before_extraction(clean_app, tmp_path):
    archive = tmp_path / 'upload.zip'
    with zipfile.ZipFile(archive, 'w') as output:
        output.writestr('first/db_v2.sqlite3', b'first')
        output.writestr('second/db_v2.sqlite3', b'second')
    with clean_app.app_context(), pytest.raises(ValueError, match='Mehrdeutiger'):
        application._extract_safe_zip_members(archive, tmp_path)
    assert not (tmp_path / 'db_v2.sqlite3').exists()


def test_request_settings_cache_is_invalidated_after_write(clean_app):
    with clean_app.app_context():
        db.session.add(Setting(key='cache-test', value='old'))
        db.session.commit()
        selects = []

        def track(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('SELECT') and 'settings' in statement:
                selects.append(statement)

        event.listen(db.engine, 'before_cursor_execute', track)
        try:
            with clean_app.test_request_context('/'):
                assert application._get_setting('cache-test') == 'old'
                assert application._get_setting('missing', 'fallback') == 'fallback'
                assert len(selects) == 1
                application._set_setting('cache-test', 'new')
                assert application._get_setting('cache-test') == 'new'
        finally:
            event.remove(db.engine, 'before_cursor_execute', track)


def test_database_restore_installs_valid_candidate_and_clears_session(store, clean_app, client, tmp_path):
    data_dir, snapshot, _ = store
    candidate = tmp_path / 'candidate.db'
    candidate.write_bytes(snapshot)
    with sqlite3.connect(candidate) as connection:
        connection.execute("UPDATE devices SET name='restored'")
    with clean_app.app_context():
        safety = application._restore_database_from_file(candidate, data_dir / 'addressbook.db', tmp_path)
        assert Device.query.one().name == 'restored'
        assert (tmp_path / safety).exists()


def test_full_restore_through_authenticated_route(store, clean_app, client, monkeypatch, tmp_path):
    import time

    _, snapshot, cfg = store
    cfg['SECRET_KEY'] = 'route-new-session-key'
    password = 'full-backup-test-password'
    with clean_app.app_context():
        archive = application._encrypt_backup_bytes(full_archive(snapshot, cfg), password)
    (tmp_path / 'candidate.rabfull').write_bytes(archive)
    monkeypatch.setitem(clean_app.config, 'BACKUP_DIR', tmp_path)
    csrf = set_csrf(client)
    with client.session_transaction() as session:
        session.update(_user_id='1', _fresh=True, auth_session_version=1, auth_time=int(time.time()))
    response = client.post('/backup', data={'csrf_token': csrf, 'action': 'restore_existing', 'filename': 'candidate.rabfull', 'restore_password': password})
    assert response.status_code == 302
    response.close()
    assert clean_app.config['SECRET_KEY'] == cfg['SECRET_KEY']
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_supported_legacy_user_schema_is_migrated_offline(store, clean_app, tmp_path):
    _, snapshot, cfg = store
    candidate = tmp_path / 'legacy.db'
    candidate.write_bytes(snapshot)
    with sqlite3.connect(candidate) as connection:
        values = connection.execute('SELECT id, username, password_hash, created_at, last_login_at FROM users').fetchall()
        connection.execute('DROP TABLE users')
        connection.execute('CREATE TABLE users(id INTEGER PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, created_at DATETIME NOT NULL, last_login_at DATETIME)')
        connection.executemany('INSERT INTO users VALUES(?,?,?,?,?)', values)
        connection.execute("DELETE FROM settings WHERE key='security_signature_version'")
    with clean_app.app_context():
        application._prepare_restore_database(candidate, cfg)
    with sqlite3.connect(candidate) as connection:
        columns = {row[1] for row in connection.execute('PRAGMA table_info(users)')}
        assert 'security_signature' in columns
        assert connection.execute('SELECT role FROM users').fetchone() == ('admin',)
        assert connection.execute('SELECT security_signature FROM users').fetchone()[0]
