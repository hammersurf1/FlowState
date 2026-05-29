"""Download spaCy and NLTK language data required by FlowState.

Run with uv so dependencies come from the project environment:

    uv run python scripts/download_models.py
"""

import subprocess
import sys


def _ensure_spacy_model():
    try:
        import spacy
        spacy.load("en_core_web_md")
        print("spaCy model 'en_core_web_md' already installed.")
    except OSError:
        print("Downloading spaCy model 'en_core_web_md'...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_md"])


def _ensure_wordnet():
    try:
        import nltk
        nltk.data.find("corpora/wordnet")
        print("NLTK WordNet already installed.")
    except LookupError:
        print("Downloading NLTK WordNet corpora...")
        import nltk
        nltk.download("wordnet")
        nltk.download("omw-1.4")


def main():
    _ensure_spacy_model()
    _ensure_wordnet()


if __name__ == "__main__":
    main()
