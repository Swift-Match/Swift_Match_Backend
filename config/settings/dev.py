from .base import *

DEBUG = True

INSTALLED_APPS += [
    "drf_spectacular_sidecar",
]

SPECTACULAR_SETTINGS.update(
    {
        "SERVE_INCLUDE_SCHEMA": True,
    }
)
