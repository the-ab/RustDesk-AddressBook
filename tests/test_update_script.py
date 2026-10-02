from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


@pytest.mark.parametrize('failure', ['none', 'build', 'health', 'timeout'])
@pytest.mark.parametrize('quoted', [False, True])
def test_signed_zip_update_and_rollback_with_custom_persistence(tmp_path, failure, quoted):
    root = tmp_path / 'installation'
    scripts = root / 'scripts'
    (scripts / 'keys').mkdir(parents=True)
    for name in ('update.sh', 'update_transaction.py'):
        shutil.copy2(Path('scripts') / name, scripts / name)
    (root / 'app').mkdir()
    config = root / 'app' / 'config.py'
    config.write_text('APP_VERSION = "0.6.2-test"\n')
    (root / 'docker-compose.yml').write_text('old compose')
    (root / 'Dockerfile').write_text('old image')
    data = tmp_path / 'custom data'
    backups = tmp_path / 'custom backups'
    data.mkdir()
    backups.mkdir()
    (data / 'addressbook.db').write_bytes(b'old SQLite data')
    (data / 'config.json').write_bytes(b'old key configuration')
    (backups / 'keep.rabfull').write_bytes(b'old backup')
    data_value = f'"{data}"' if quoted else str(data)
    backup_value = f"'{backups}'" if quoted else str(backups)
    original_env = f'RAB_DATA_DIR={data_value}\nRAB_BACKUP_DIR={backup_value}\nRAB_CONTAINER_NAME=isolated-rab\nRAB_IMAGE_NAME=rustdesk-addressbook-v0.6.2\n'
    (root / '.env').write_text(original_env)
    (root / 'install-config.env').write_text('local config')
    updates = root / 'updates'
    updates.mkdir()
    package = updates / 'rustdesk-addressbook-update-flat-v0.6.3.zip'
    with zipfile.ZipFile(package, 'w') as archive:
        archive.writestr('app/config.py', 'APP_VERSION = "0.6.3-test"\n')
        archive.writestr('Dockerfile', 'new image')
        archive.writestr('docs/added.md', 'new file')
        archive.writestr('contrib/', b'')
        archive.writestr('contrib/fail2ban/filter.d/test.conf', 'new integration')
    # Fresh synthetic signing key; no real release credential is used by tests.
    key = Ed25519PrivateKey.generate()
    (scripts / 'keys' / 'update-signing-public-v1.pem').write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    Path(str(package) + '.sha256').write_text(hashlib.sha256(package.read_bytes()).hexdigest() + '  ' + package.name + '\n')
    Path(str(package) + '.sig').write_bytes(key.sign(Path(str(package) + '.sha256').read_bytes()))
    tools = tmp_path / 'bin'
    tools.mkdir()
    log = tmp_path / 'commands'
    docker = tools / 'docker'
    docker.write_text('''#!/usr/bin/env python3
import os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ['FAKE_LOG']).open('a') as log:
    log.write(' '.join(args) + '\\n')
new = '0.6.3' in Path('app/config.py').read_text()
if args[:2] == ['compose', 'version']:
    raise SystemExit(0)
if args and args[0] == 'inspect':
    if new:
        print({'health': 'unhealthy', 'timeout': 'starting'}.get(os.environ['FAILURE'], 'healthy'))
    else:
        print('healthy')
    raise SystemExit(0)
if args[:2] == ['compose', 'up'] and new:
    (Path(os.environ['CUSTOM_DATA']) / 'addressbook.db').write_bytes(b'new migrated SQLite')
    (Path(os.environ['CUSTOM_BACKUPS']) / 'new.rabfull').write_bytes(b'new backup')
if args[:2] == ['compose', 'build'] and new and os.environ['FAILURE'] == 'build':
    raise SystemExit(3)
''')
    docker.chmod(0o755)
    # Do not wait 60 seconds or change real host ownership in the isolated test.
    for name in ('sleep', 'chown'):
        shim = tools / name
        shim.write_text('#!/bin/sh\nexit 0\n')
        shim.chmod(0o755)
    env = {**os.environ, 'PATH': str(tools) + os.pathsep + os.environ['PATH'], 'FAKE_LOG': str(log), 'FAILURE': failure, 'CUSTOM_DATA': str(data), 'CUSTOM_BACKUPS': str(backups)}
    result = subprocess.run(['bash', str(scripts / 'update.sh'), str(package)], env=env, capture_output=True, text=True, timeout=30)
    snapshots = list(tmp_path.glob('rustdesk-addressbook-preupdate-*'))
    assert len(snapshots) == 1, result.stderr
    assert (snapshots[0] / 'data' / 'addressbook.db').read_bytes() == b'old SQLite data'
    commands = log.read_text().splitlines()
    assert not any('rustdesk-addressbook' == command.rsplit(' ', 1)[-1] for command in commands)
    assert commands.index('compose down --remove-orphans') < commands.index('compose build --no-cache')
    if failure == 'none':
        assert result.returncode == 0, result.stderr
        assert '0.6.3' in config.read_text()
        assert (data / 'addressbook.db').read_bytes() == b'new migrated SQLite'
        assert (updates / 'installed' / package.name).exists()
    else:
        assert result.returncode != 0
        assert 'Update abgeschlossen' not in result.stdout
        assert '0.6.2' in config.read_text()
        assert (root / 'Dockerfile').read_text() == 'old image'
        assert (root / '.env').read_text() == original_env
        assert not (root / 'docs' / 'added.md').exists()
        assert not (root / 'contrib' / 'fail2ban' / 'filter.d' / 'test.conf').exists()

        assert (data / 'addressbook.db').read_bytes() == b'old SQLite data'
        assert (data / 'config.json').read_bytes() == b'old key configuration'
        assert (backups / 'keep.rabfull').read_bytes() == b'old backup'
        assert not (backups / 'new.rabfull').exists()
        assert package.exists()
        assert 'compose build' in commands



def test_update_transaction_accepts_every_tracked_package_path():
    import importlib.util

    spec = importlib.util.spec_from_file_location('update_transaction', 'scripts/update_transaction.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Release ZIPs also ship this regression suite and do not contain .git.
    if Path('.git').exists():
        files = subprocess.check_output(['git', 'ls-files', '-z']).decode().rstrip('\0').split('\0')
    else:
        ignored = {'__pycache__', '.pytest_cache', '.ruff_cache', '.venv', 'venv'}
        files = [str(path) for path in Path('.').rglob('*') if path.is_file() and not ignored.intersection(path.parts)]
    assert all(module.managed(Path(path)) for path in files)
    directories = {parent for path in files for parent in Path(path).parents if parent.parts}
    assert all(module.managed(path) for path in directories)
