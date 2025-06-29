"""
Setup script for Agent Zero Gemini
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="agent-zero-gemini",
    version="1.0.0",
    author="Agent Zero Gemini Team",
    author_email="contact@agentzerogemini.com",
    description="A powerful AI agent framework powered by Gemini AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/agent-zero-gemini",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.9.0",
            "flake8>=6.1.0",
            "mypy>=1.6.0",
        ],
        "audio": [
            "speechrecognition>=3.10.0",
            "pyttsx3>=2.90",
            "pyaudio>=0.2.11",
        ],
        "browser": [
            "selenium>=4.15.0",
            "playwright>=1.40.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agent-zero-gemini=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yaml", "*.json"],
        "web_ui": ["templates/*", "static/*/*"],
        "prompts": ["*.md", "*.txt", "*.yaml"],
    },
)
