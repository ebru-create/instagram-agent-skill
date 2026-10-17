#!/usr/bin/env python3
"""Build/verify a deterministic source ZIP from a clean committed checkout."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {'README.md', 'CHANGELOG.md', 'LICENSE', '.gitignore', 'instagram-agent.json'}
DIRECTORIES = {'docs', 'scripts', 'skills', 'templates', 'evaluation', 'validation', 'tests', '.claude-plugin'}
REQUIRED = {'instagram-agent.json', 'README.md', 'CHANGELOG.md', 'LICENSE', '.claude-plugin/plugin.json',
            '.claude-plugin/marketplace.json', 'scripts/install.py', 'scripts/package_release.py',
            'docs/quickstart.tr.md', 'docs/walkthrough.tr.md', 'docs/installation.md', 'docs/release.md'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def git(source, *args):
    result = subprocess.run(['git', '-C', str(source), *args], capture_output=True)
    if result.returncode:
        raise ValueError('a Git checkout and Git executable are required to build a release')
    return result.stdout


def check_links(files):
    """Check local Markdown destinations in the release-facing docs, without network calls."""
    for name, raw in files.items():
        if name != 'README.md' and not name.startswith('docs/'):
            continue
        if not name.endswith('.md'):
            continue
        for link in re.findall(r'\]\(([^\s)]+)\)', raw.decode('utf-8')):
            if '://' in link or link.startswith(('#', 'mailto:')):
                continue
            target = link.split('#', 1)[0]
            parts = []
            for part in (PurePosixPath(name).parent / target).parts:
                if part == '..':
                    if not parts:
                        raise ValueError('documentation link leaves the package: ' + link)
                    parts.pop()
                elif part not in ('.', ''):
                    parts.append(part)
            resolved = '/'.join(parts)
            if resolved not in files:
                raise ValueError(f'broken packaged documentation link: {name} -> {link}')


def inventory(source):
    source = Path(source).resolve()
    top = Path(git(source, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    if top != source or git(source, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('build from the root of a clean committed checkout; tracked changes are not packaged')
    tracked = git(source, 'ls-files', '-z').decode('utf-8').split('\0')
    files = {}
    for name in sorted(filter(None, tracked)):
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('unsafe tracked path')
        included = name in ROOT_FILES or relative.parts[0] in DIRECTORIES or name.startswith('.github/workflows/')
        if not included or any(part in ('__pycache__', '.venv', '.DS_Store') for part in relative.parts) or name.endswith(('.pyc', '.tmp')):
            continue
        path = source / name
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != source.parent):
            raise ValueError('symbolic links are not supported in release files: ' + name)
        if not path.is_file() or not path.resolve().is_relative_to(source):
            raise ValueError('release files must be regular files inside the checkout')
        files[name] = path.read_bytes()
    if not REQUIRED <= set(files):
        raise ValueError('release source is incomplete; required documentation/metadata is missing')
    plugin = json.loads(files['.claude-plugin/plugin.json'])
    version = json.loads(files['instagram-agent.json'])['version']
    if plugin['version'] != version:
        raise ValueError('core and Claude adapter version do not match')
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('release version must have major.minor.patch form')
    if f'## [{version}]' not in files['CHANGELOG.md'].decode('utf-8'):
        raise ValueError('changelog does not contain the package version')
    market = json.loads(files['.claude-plugin/marketplace.json'])
    if not any(item.get('name') == plugin['name'] and item.get('source') == './' for item in market['plugins']):
        raise ValueError('plugin and marketplace identity do not match')
    # Validate only selected tracked files, excluding unrelated untracked source data.
    with tempfile.TemporaryDirectory() as temporary:
        staged = Path(temporary)
        for name, raw in files.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        spec = importlib.util.spec_from_file_location('release_installer', staged / 'scripts/install.py')
        installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
        _, state = installer.bundle(staged)
    check_links(files)
    manifest = {'schema_version': 1, 'version': version,
                'git_commit': git(source, 'rev-parse', 'HEAD').decode().strip(),
                'skills': state['skills'], 'files': {name: sha(raw) for name, raw in files.items()}}
    return files, manifest


def archive_bytes(files, manifest):
    stream = io.BytesIO()
    prefix = 'instagram-agent-skill-' + manifest['version'] + '/'
    members = {**files, 'RELEASE-MANIFEST.json': encoded(manifest)}
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(members.items()):
            entry = zipfile.ZipInfo(prefix + name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, raw)
    return stream.getvalue()


def verify(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or not names:
            raise ValueError('archive entries are empty or duplicated')
        manifest_names = [name for name in names if len(PurePosixPath(name).parts) == 2 and name.endswith('/RELEASE-MANIFEST.json')]
        if len(manifest_names) != 1:
            raise ValueError('archive must contain one release manifest')
        manifest = json.loads(archive.read(manifest_names[0]))
        if not isinstance(manifest, dict):
            raise ValueError('release manifest must be an object')
        version = manifest.get('version')
        if type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1 or not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
            raise ValueError('invalid release manifest version')
        prefix = 'instagram-agent-skill-' + version + '/'
        files = manifest.get('files')
        if not isinstance(files, dict) or not REQUIRED <= set(files):
            raise ValueError('invalid release file inventory')
        for name in files:
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name:
                raise ValueError('unsafe release manifest path')
        expected = {prefix + name for name in files} | {prefix + 'RELEASE-MANIFEST.json'}
        if set(names) != expected:
            raise ValueError('archive and manifest file inventories differ')
        for name, digest in files.items():
            if sha(archive.read(prefix + name)) != digest:
                raise ValueError('release file hash mismatch: ' + name)
    return {'status': 'verified', 'version': version, 'git_commit': manifest['git_commit'],
            'file_count': len(files), 'archive_sha256': sha(Path(path).read_bytes())}


def build(output, source=ROOT):
    output = Path(output).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('choose a new release output directory; existing files are preserved')
    files, manifest = inventory(source)
    raw = archive_bytes(files, manifest)
    filename = 'instagram-agent-skill-' + manifest['version'] + '.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.release-stage-', dir=output.parent))
    try:
        (stage / filename).write_bytes(raw)
        (stage / 'release-manifest.json').write_bytes(encoded(manifest))
        (stage / 'SHA256SUMS').write_text(f"{sha(raw)}  {filename}\n{sha(encoded(manifest))}  release-manifest.json\n", encoding='utf-8')
        verify(stage / filename)
        if output.exists() or output.is_symlink():
            raise ValueError('release output appeared during build; choose a new directory')
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {'status': 'prepared', 'version': manifest['version'], 'git_commit': manifest['git_commit'],
            'file_count': len(files), 'archive': str(output / filename), 'archive_sha256': sha(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out', type=Path, help='new local release directory; requires clean Git source')
    mode.add_argument('--verify', type=Path, help='verify an existing ZIP without extracting or running it')
    args = parser.parse_args()
    try:
        result = verify(args.verify) if args.verify else build(args.out)
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        parser.exit(2, f'error: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
