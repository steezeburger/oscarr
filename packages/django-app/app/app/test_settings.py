from .settings import INSTALLED_APPS  # noqa: F401

"""
Adds `common` app to installed apps so that test models are only created for tests.
"""
INSTALLED_APPS = INSTALLED_APPS + ["common"]

LOGGING = None
