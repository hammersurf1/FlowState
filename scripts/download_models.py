import subprocess
import sys


def main():
    try:
        import spacy
        spacy.load("en_core_web_md")
        print("spaCy model 'en_core_web_md' already installed.")
    except OSError:
        print("Downloading spaCy model 'en_core_web_md'...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_md"])


if __name__ == "__main__":
    main()
