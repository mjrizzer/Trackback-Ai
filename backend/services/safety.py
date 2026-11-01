"""Small single-process controls. Hosted replicas need shared rate-limit storage."""

import time
from collections import OrderedDict, deque
from threading import Lock
from starlette.responses import JSONResponse
from backend.config import settings


class LoginLimiter:
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = Lock()

    def allow(self, address):
        timestamp = time.monotonic()
        with self.lock:
            queue = self.entries.setdefault(address, deque())
            self.entries.move_to_end(address)
            while queue and queue[0] < timestamp - 60:
                queue.popleft()
            if len(queue) >= settings.auth_rate_limit:
                return False
            queue.append(timestamp)
            if len(self.entries) > 10000:
                self.entries.popitem(last=False)
            return True


login_limiter = LoginLimiter()


class SafetyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = {key.decode().lower(): value.decode() for key, value in scope['headers']}
        path, method = scope['path'], scope['method']
        unsafe = method not in ('GET', 'HEAD', 'OPTIONS')
        if unsafe and path.startswith('/api/'):
            origin = headers.get('origin')
            if origin and origin not in settings.cors_origins.split(','):
                return await JSONResponse(
                    {'detail': 'Request origin is not allowed'}, status_code=403
                )(scope, receive, send)
            if (
                'traceback_session=' in headers.get('cookie', '')
                and 'authorization' not in headers
                and headers.get('x-csrf-protection') != '1'
            ):
                return await JSONResponse(
                    {'detail': 'CSRF protection header required'}, status_code=403
                )(scope, receive, send)
        if path in ('/api/auth/login', '/api/auth/register') and unsafe:
            address = scope.get('client', ('unknown', 0))[0]
            if not login_limiter.allow(address):
                return await JSONResponse(
                    {'detail': 'Too many authentication attempts. Try again in one minute.'},
                    status_code=429,
                    headers={'Retry-After': '60'},
                )(scope, receive, send)
        if unsafe:
            limit = 10 * 1024 * 1024 + 256 * 1024 if path == '/api/documents' else 256 * 1024
            try:
                declared_size = int(headers.get('content-length', '0'))
            except ValueError:
                return await JSONResponse({'detail': 'Invalid Content-Length'}, status_code=400)(
                    scope, receive, send
                )
            if declared_size < 0 or declared_size > limit:
                return await JSONResponse(
                    {'detail': 'Request body exceeds the allowed size'}, status_code=413
                )(scope, receive, send)
            body, more = bytearray(), True
            while more:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                if len(body) + len(chunk) > limit:
                    return await JSONResponse(
                        {'detail': 'Request body exceeds the allowed size'}, status_code=413
                    )(scope, receive, send)
                body.extend(chunk)
                more = message.get('more_body', False)
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()

        async def secure_send(message):
            if message['type'] == 'http.response.start':
                extra = [
                    (b'x-content-type-options', b'nosniff'),
                    (b'x-frame-options', b'DENY'),
                    (b'referrer-policy', b'strict-origin-when-cross-origin'),
                    (b'permissions-policy', b'camera=(), microphone=(), geolocation=()'),
                ]
                if path.startswith('/api/'):
                    extra.append((b'cache-control', b'no-store'))
                if settings.environment == 'production':
                    extra.append(
                        (b'strict-transport-security', b'max-age=31536000; includeSubDomains')
                    )
                if not path.startswith(('/docs', '/redoc')):
                    extra.append(
                        (
                            b'content-security-policy',
                            b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
                        )
                    )
                message['headers'] = list(message.get('headers', [])) + extra
            await send(message)

        await self.app(scope, bounded_receive if unsafe else receive, secure_send)
