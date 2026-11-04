"""Run the whole site locally (API + pages) on one port: python app.py

On Vercel the pages are served as static files and the API runs from api/index.py,
so this file is excluded from deployments (.vercelignore).
"""

import os

from flask import abort, send_from_directory

from backend import create_app

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
PAGE_TYPES = {'.html', '.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.ico'}

app = create_app()


@app.get('/', defaults={'path': 'index.html'})
@app.get('/<path:path>')
def site(path):
    if path.startswith('api/') or os.path.splitext(path)[1].lower() not in PAGE_TYPES:
        abort(404)
    return send_from_directory(ROOT, path)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5000')), debug=os.getenv('FLASK_DEBUG') == '1')
