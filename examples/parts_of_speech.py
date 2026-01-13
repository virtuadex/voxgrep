import sys
import os

# Set environment variables to store heavy models on D: drive
os.environ["WHISPER_CACHE_DIR"] = "D:/models/whisper"
os.environ["HF_HOME"] = "D:/models/huggingface"
os.environ["TORCH_HOME"] = "D:/models/torch"
import argparse
import videogrep
from videogrep import transcribe
import spacy

"""
Make a supercut of different types of words, for example, all nouns.

To use:

1) Install spacy: pip3 install spacy
2) Download models: 
   python -m spacy download en_core_web_sm
   python -m spacy download pt_core_news_sm
3) Run: python3 parts_of_speech.py somevideo.mp4 --lang pt
"""

def load_spacy_model(lang):
    """Tries to load the best available model for the language."""
    if lang == "en":
        models = ["en_core_web_trf", "en_core_web_lg", "en_core_web_sm"]
    else:
        models = ["pt_core_news_lg", "pt_core_news_sm"]

    for model in models:
        try:
            print(f"Attempting to load spacy model: {model}")
            return spacy.load(model)
        except OSError:
            continue
    
    print(f"Error: No spacy models found for language '{lang}'.")
    print(f"Please run: python -m spacy download {models[0]}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Make a supercut of different types of words.")
    parser.add_argument("videos", nargs="+", help="The videos we are working with")
    parser.add_argument("--lang", choices=["en", "pt"], default="en", help="Language: en or pt. Default: en.")
    parser.add_argument("--pos", nargs="+", default=["NOUN"], help="Parts of speech to search for. Default: NOUN.")
    parser.add_argument("--output", "-o", default="part_of_speech_supercut.mp4", help="Output filename.")
    
    args = parser.parse_args()

    # Enable GPU if available
    if spacy.prefer_gpu():
        print("GPU detected! Using GPU for spacy processing.")
    else:
        print("No GPU detected or spacy-transformers not configured for GPU. Using CPU.")

    nlp = load_spacy_model(args.lang)

    search_words = []

    for video in args.videos:
        # ensure transcript exists
        if not videogrep.find_transcript(video):
            print(f"Transcript not found for {video}. Transcribing with Whisper...")
            transcribe.transcribe(video, method="whisper")

        transcript = videogrep.parse_transcript(video)
        if not transcript:
            continue

        for sentence in transcript:
            doc = nlp(sentence["content"])
            for token in doc:
                if token.pos_ in args.pos:
                    # ensure we're only going to grab exact words
                    search_words.append(f"^{token.text}$")

    if search_words:
        query = "|".join(search_words)
        videogrep.videogrep(
            args.videos, query, search_type="fragment", output=args.output
        )
    else:
        print("No matching parts of speech found.")

if __name__ == "__main__":
    main()
