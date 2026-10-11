"""py2app build for Morning Agent.app.

Alias build (fast, references this repo/venv):
    .venv/bin/python setup_app.py py2app -A
Output: dist/Morning Agent.app
"""
from setuptools import setup

OPTIONS = {
    "iconfile": "morning_agent/assets/app_icon.icns",
    "plist": {
        "CFBundleName": "Morning Agent",
        "CFBundleDisplayName": "Morning Agent",
        "CFBundleIdentifier": "com.morning-agent",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "LSMultipleInstancesProhibited": True,
    },
    "packages": ["morning_agent"],
}

setup(
    app=["morning_launch.py"],
    name="Morning Agent",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
