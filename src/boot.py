import micropython
import upip

try:
    import HCSR04  # noqa
except ImportError:
    upip.install("mPython-hcsr04")

try:
    import logging  # noqa
except ImportError:
    upip.install("pycopy-logging")


micropython.opt_level(3)
