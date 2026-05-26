import pytest

BILINGUAL_BLOCK = (
    "இந்தியாவின் தேசிய கொடி விதி 2002-ன்படி, கல்வி நிறுவனங்களில் "
    "தேசியக் கொடியை ஏற்றுவதற்கான வழிமுறைகளின் மாதிரி தொகுப்பை ஆய்வு செய்க.\n"
    "Examine the model set of instructions for hoisting National Flag in "
    "educational institutions as per the Flag Code of India 2002."
)

NOISE_LINES = [
    "SHANKAR IAS ACADEMY, Plot No 1742, 1st Floor, 18th Main Road",
    "www.shankariasacademy.com",
    "044-43533445, 044-45543082",
    "5",
    "GS1MII/24",
    "திருப்புக/Turn over",
]

MINIMAL_QUESTIONS = [
    {
        "year": 2024, "paper": "Paper II", "unit_number": "I",
        "unit_name": None, "section": "A", "question_number": 1,
        "marks": 10, "word_limit": 150,
        "tamil": "இந்தியாவின் தேசிய கொடி விதி...",
        "english": "Examine the model set of instructions...",
        "sub_questions": [], "noise_flagged": False,
        "tags": {
            "paper": "Paper II",
            "unit": "Unit I: Modern History of India and Indian Culture",
            "heading": "Indian Culture and Heritage",
            "theme": "National Symbols and Identity",
            "keyword": "National Symbols"
        }
    }
]
