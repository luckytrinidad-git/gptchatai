"""
WSGI config for gptchatbot project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

from django.core.wsgi import get_wsgi_application
import os
import sys
from pathlib import Path

# Add the project root to the sys.path
path_home = str(Path(__file__).resolve().parent.parent)
if path_home not in sys.path:
    sys.path.append(path_home)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gptchatbot.settings')

application = get_wsgi_application()
