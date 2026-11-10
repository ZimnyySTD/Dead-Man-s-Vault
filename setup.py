from setuptools import setup, find_packages

setup(
    name="DeadMansVault",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PySide6",
        "requests",
        "zstandard",
        "cryptography",
    ],
    entry_points={
        "console_scripts": [
            "deadmansvault=DeadMansVault.Launcher.Application.main:main",
        ],
    },
)
