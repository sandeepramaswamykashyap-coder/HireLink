import os
import sys
import subprocess
from setuptools import setup, find_packages

def install_dependencies():
    print("Installing dependencies from requirements.txt...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def download_spacy_model():
    print("Downloading spaCy model 'en_core_web_sm'...")
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])

def setup_project():
    # Only run these if executed as a script (not during pip install)
    if __name__ == "__main__":
        try:
            # Check if requirements are installed, if not, install them
            import spacy
        except ImportError:
            install_dependencies()
        
        try:
            import en_core_web_sm
        except ImportError:
            download_spacy_model()
            
        print("\n✅ Setup complete! You can now run the application.")
        print("Run: streamlit run app.py")

setup(
    name="IndianSmartApplier",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "flask",
        "selenium",
        "beautifulsoup4",
        "webdriver_manager",
        "spacy",
        "scikit-learn",
        "pandas",
        "pymupdf",
        "transformers",
        "torch",
        "pytesseract",
        "fake-useragent",
        "requests"
    ],
    entry_points={
        'console_scripts': [
            'indian-smart-applier=app:main',
        ],
    },
)

if __name__ == "__main__":
    setup_project()
