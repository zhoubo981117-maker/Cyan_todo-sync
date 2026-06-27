"""Vercel Python serverless entrypoint.

Vercel runs any ``api/*.py`` that exposes a ``handler`` subclass of
``BaseHTTPRequestHandler``. server.py already defines exactly such a class
(``Handler``), so we just put the repo root on the path and re-export it.
All routes are funnelled here by the catch-all rewrite in vercel.json, and
``Handler`` does its own path-based routing (static files + /api/*).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import Handler as handler  # noqa: E402,F401
