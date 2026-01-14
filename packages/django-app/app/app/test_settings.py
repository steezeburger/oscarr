from .settings import *  # noqa: F403, F401

"""
Adds `common` app to installed apps so that test models are only created for tests.
"""
INSTALLED_APPS += ["common"]  # noqa: F405

LOGGING = None
