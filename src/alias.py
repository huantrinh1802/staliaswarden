import random
import string

from config import Config

FIRST_NAMES = [
    "alex",
    "ben",
    "chris",
    "dana",
    "emma",
    "frank",
    "gina",
    "henry",
    "irene",
    "jack",
    "kate",
    "liam",
    "maria",
    "nate",
    "olivia",
    "paul",
    "quinn",
    "rachel",
    "sam",
    "tina",
    "uma",
    "victor",
    "wanda",
    "xavier",
    "yara",
    "zane",
]

LAST_NAMES = [
    "adams",
    "baker",
    "cooper",
    "diaz",
    "evans",
    "fisher",
    "gomez",
    "hayes",
    "iverson",
    "jones",
    "khan",
    "lee",
    "morgan",
    "nelson",
    "owens",
    "patel",
    "quinn",
    "roberts",
    "smith",
    "turner",
    "uribe",
    "vargas",
    "watson",
    "xu",
    "young",
    "zimmerman",
]

SEPARATORS = ["", ".", "_", "-"]


def random_name():
    """Return a (first, last) tuple with random capitalization (Title or lower)."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    # randomize capitalization style
    style = random.choice(["lower", "title"])
    if style == "title":
        first = first.title()
        last = last.title()
    return first, last


def pattern_email(first: str, last: str, domain: str) -> str:
    """Create a realistic-looking local part based on name and common patterns."""
    sep = random.choice(SEPARATORS)
    pattern = random.choice(
        [
            "firstlast",
            "first.sep.last",
            "f.last",
            "firstl",
            "first_last",
            "last.first",
            "first",
            "last",
            "first.digits",
            "firstlast.digits",
            "initials",
        ]
    )
    if pattern == "firstlast":
        local = f"{first}{last}"
    elif pattern == "first.sep.last":
        local = f"{first}{sep}{last}"
    elif pattern == "f.last":
        local = f"{first[0]}{sep}{last}"
    elif pattern == "firstl":
        local = f"{first}{last[0]}"
    elif pattern == "first_last":
        local = f"{first}_{last}"
    elif pattern == "last.first":
        local = f"{last}{sep}{first}"
    elif pattern == "first":
        local = first
    elif pattern == "last":
        local = last
    elif pattern == "first.digits":
        local = f"{first}{sep}{random.randint(10, 99)}"
    elif pattern == "firstlast.digits":
        local = f"{first}{last}{sep}{random.randint(1, 999)}"
    else:
        # sometimes include middle initial
        middle = random.choice(string.ascii_lowercase) if random.random() < 0.3 else ""
        local = f"{first[0]}{middle}{sep}{last}"
    # normalize: remove accidental spaces, make ASCII-friendly (simple)
    local = local.replace(" ", "").replace("'", "").lower()
    # sometimes add a short year-like component (born year or joined year)
    if random.random() < 0.12:
        year = random.choice([str(random.randint(70, 99)), str(random.randint(2000, 2024))])
        local = f"{local}{year}"
    return f"{local}@{domain}"


def generate_alias(domain: str | None = "random") -> str:
    selected_domain = Config.alias_domain if domain == "random" or domain is None else domain
    first, last = random_name()
    return pattern_email(first, last, selected_domain)
