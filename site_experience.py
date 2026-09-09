"""Small shared HTTP improvements; no third-party runtime dependency."""
from functools import lru_cache
import gzip
from hashlib import sha256
from pathlib import Path

from flask import request


@lru_cache(maxsize=512)
def _asset_digest(path, modified_ns, size):
    return sha256(Path(path).read_bytes()).hexdigest()[:12]


@lru_cache(maxsize=32)
def _gzip_asset(path, modified_ns, size):
    return gzip.compress(Path(path).read_bytes(), compresslevel=6, mtime=0)


def install_experience(app):
    static_root = Path(app.static_folder).resolve()

    def asset_version(filename):
        path = (static_root / filename).resolve()
        if not path.is_relative_to(static_root) or not path.is_file():
            return None
        stat = path.stat()
        return _asset_digest(str(path), stat.st_mtime_ns, stat.st_size)

    @app.url_defaults
    def version_static_assets(endpoint, values):
        if endpoint == 'static' and 'filename' in values and 'v' not in values:
            version = asset_version(values['filename'])
            if version:
                values['v'] = version

    @app.after_request
    def response_policy(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if request.endpoint == 'static' and response.status_code in (200, 304):
            filename = (request.view_args or {}).get('filename', '')
            path = (static_root / filename).resolve()
            textual = path.suffix.lower() in ('.css','.js','.json','.html','.svg')
            if textual:
                response.vary.add('Accept-Encoding')
            if (textual and response.status_code == 200 and request.method == 'GET'
                    and request.accept_encodings['gzip'] > 0 and 'Range' not in request.headers
                    and not response.headers.get('Content-Encoding')
                    and path.is_relative_to(static_root) and path.is_file()):
                stat = path.stat()
                if 1024 <= stat.st_size <= 2 * 1024 * 1024:
                    compressed = _gzip_asset(str(path), stat.st_mtime_ns, stat.st_size)
                    if len(compressed) < stat.st_size:
                        response.close()
                        response.direct_passthrough = False
                        response.set_data(compressed)
                        response.headers['Content-Encoding'] = 'gzip'
            if textual and response.get_etag()[0]:
                response.set_etag(response.get_etag()[0], weak=True)
            if request.args.get('v') and request.args['v'] == asset_version(filename):
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            else:
                response.headers['Cache-Control'] = 'public, max-age=3600'
        elif response.mimetype == 'text/html' or request.path.startswith('/api/'):
            # Account pages and CSRF tokens must never enter a shared HTTP cache.
            response.headers['Cache-Control'] = 'private, no-store'
            response.vary.add('Cookie')
        return response
