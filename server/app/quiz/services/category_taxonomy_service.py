import asyncio
import functools
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from huggingface_hub import InferenceClient


load_dotenv()


SEED_CATEGORIES_DIR = Path(__file__).resolve().parents[1] / "seed_data" / "categories"
CANONICAL_QUIZ_TYPES = {"multichoice", "true-false", "open-ended", "short-answer"}
API_QUIZ_TYPE_LABELS = {
    "multichoice": "multiple choice",
    "true-false": "true or false",
    "open-ended": "open ended",
    "short-answer": "short answer",
}
QUIZ_TYPE_ALIASES = {
    "multiple choice": "multichoice",
    "multiple-choice": "multichoice",
    "multichoice": "multichoice",
    "true false": "true-false",
    "true-false": "true-false",
    "true or false": "true-false",
    "open ended": "open-ended",
    "open-ended": "open-ended",
    "short answer": "short-answer",
    "short-answer": "short-answer",
}
STOP_WORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "into",
    "quiz",
    "questions",
    "question",
    "answer",
    "answers",
    "learners",
    "students",
    "general",
}
TAXONOMY_ALIASES = {
    "programming": {"software", "coding", "code", "developer", "developers", "algorithm", "algorithms"},
    "computer-basics": {"computer", "computers", "hardware", "software", "operating", "systems"},
    "internet-and-web": {"web", "website", "websites", "browser", "browsers", "html", "css", "http"},
    "cybersecurity": {"security", "password", "malware", "phishing", "encryption", "hacking"},
    "tech-companies": {"google", "apple", "microsoft", "amazon", "meta", "tesla", "startup"},
    "biology": {"cells", "cell", "organism", "organisms", "human", "body", "life"},
    "chemistry": {"chemical", "chemicals", "atom", "atoms", "molecule", "molecules", "elements"},
    "physics": {"force", "motion", "energy", "electricity", "gravity", "mechanics"},
    "astronomy": {"space", "planet", "planets", "star", "stars", "galaxy", "universe"},
    "environmental-science": {"environment", "climate", "ecosystem", "pollution", "conservation"},
    "world-capitals": {"capital", "capitals", "cities", "city"},
    "countries-and-flags": {"country", "countries", "flag", "flags", "nation", "nations"},
    "physical-geography": {"landform", "landforms", "climate", "terrain"},
    "rivers-and-mountains": {"river", "rivers", "mountain", "mountains"},
    "continents-and-oceans": {"continent", "continents", "ocean", "oceans"},
    "algebra": {"equation", "equations", "variable", "variables", "polynomial"},
    "arithmetic": {"addition", "subtraction", "multiplication", "division", "numbers"},
    "geometry": {"shape", "shapes", "angle", "angles", "triangle", "circle"},
    "calculus": {"derivative", "integral", "limits", "differentiation"},
    "trigonometry": {"sine", "cosine", "tangent", "triangle", "angles"},
    "word-problems": {"problem", "problems", "scenario", "scenarios"},
    "football-soccer": {"football", "soccer", "fifa", "goal", "goals"},
    "basketball": {"nba", "hoop", "court", "dunk"},
    "olympics": {"olympic", "medals", "athlete", "athletes"},
    "athletes-and-records": {"athlete", "athletes", "record", "records"},
    "authors-and-books": {"author", "authors", "book", "books", "novel", "novels"},
    "poetry": {"poem", "poems", "poet", "poets", "verse"},
    "art-movements": {"painting", "paintings", "artist", "artists", "impressionism", "cubism"},
    "famous-paintings": {"painting", "paintings", "artwork", "artist", "artists"},
    "literary-devices": {"metaphor", "simile", "literature", "language"},
    "grammar": {"sentence", "sentences", "verb", "verbs", "noun", "nouns"},
    "vocabulary": {"word", "words", "meaning", "meanings"},
    "spelling": {"spell", "spelling"},
    "synonyms-and-antonyms": {"synonym", "synonyms", "antonym", "antonyms"},
    "idioms-and-phrases": {"idiom", "idioms", "phrase", "phrases"},
    "reading-comprehension": {"reading", "passage", "comprehension"},
}
CORPORATE_CATEGORY_DIRS = {"Onboarding", "Compliance"}


@dataclass(frozen=True)
class TaxonomyEntry:
    category: str
    category_slug: str
    subcategory: str
    subcategory_slug: str
    persona_category: str = "school"


@dataclass(frozen=True)
class TaxonomyClassification:
    category: str
    category_slug: str
    subcategory: str
    subcategory_slug: str
    tags: tuple[str, ...]
    method: str
    confidence: float
    persona_category: str = "school"

    def to_quiz_fields(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "category_slug": self.category_slug,
            "subcategory": self.subcategory,
            "subcategory_slug": self.subcategory_slug,
            "tags": list(self.tags),
            "classification": {
                "method": self.method,
                "confidence": round(self.confidence, 4),
            },
        }


def slugify(value: str) -> str:
    normalized = value.replace("&", " and ")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-").lower()


def display_name_from_path(value: str) -> str:
    normalized = value.replace("_", " ").replace("&", "and")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    words = []
    for word in normalized.split(" "):
        if word.upper() in {"TV", "AI", "API"}:
            words.append(word.upper())
        elif word.lower() in {"and", "of", "the"}:
            words.append(word.lower())
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


def normalize_quiz_type(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("_", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = QUIZ_TYPE_ALIASES.get(normalized, normalized)
    if normalized not in CANONICAL_QUIZ_TYPES:
        raise ValueError(f"Unsupported quiz type: {value}")
    return normalized


def quiz_type_to_api_label(value: str) -> str:
    return API_QUIZ_TYPE_LABELS.get(normalize_quiz_type(value), value)


def quiz_type_to_title(value: str) -> str:
    return quiz_type_to_api_label(value).title()


def tokenize(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def build_tags(entry: TaxonomyEntry, quiz_type: str, extra_tags: Iterable[str] | None = None) -> list[str]:
    tags = [entry.category_slug, entry.subcategory_slug, normalize_quiz_type(quiz_type)]
    if extra_tags:
        tags.extend(slugify(tag) for tag in extra_tags if str(tag).strip())
    return list(dict.fromkeys(tag for tag in tags if tag))


@lru_cache(maxsize=1)
def get_taxonomy_entries() -> tuple[TaxonomyEntry, ...]:
    entries: list[TaxonomyEntry] = []
    if not SEED_CATEGORIES_DIR.exists():
        return tuple(entries)

    for category_dir in sorted(path for path in SEED_CATEGORIES_DIR.iterdir() if path.is_dir()):
        category = display_name_from_path(category_dir.name)
        category_slug = slugify(category)
        for subcategory_dir in sorted(path for path in category_dir.iterdir() if path.is_dir()):
            questions_file = subcategory_dir / "questions.py"
            if not questions_file.exists():
                continue
            subcategory = display_name_from_path(subcategory_dir.name)
            entries.append(
                TaxonomyEntry(
                    category=category,
                    category_slug=category_slug,
                    subcategory=subcategory,
                    subcategory_slug=slugify(subcategory),
                    persona_category="corporate" if category_dir.name in CORPORATE_CATEGORY_DIRS else "school",
                )
            )
    return tuple(entries)


def get_taxonomy_entry(category: str, subcategory: str) -> TaxonomyEntry | None:
    category_slug = slugify(category)
    subcategory_slug = slugify(subcategory)
    return get_taxonomy_entry_by_slugs(category_slug, subcategory_slug)


def get_taxonomy_entry_by_slugs(category_slug: str, subcategory_slug: str) -> TaxonomyEntry | None:
    for entry in get_taxonomy_entries():
        if entry.category_slug == category_slug and entry.subcategory_slug == subcategory_slug:
            return entry
    return None


def build_classification(entry: TaxonomyEntry, quiz_type: str, *, method: str, confidence: float) -> TaxonomyClassification:
    return TaxonomyClassification(
        category=entry.category,
        category_slug=entry.category_slug,
        subcategory=entry.subcategory,
        subcategory_slug=entry.subcategory_slug,
        tags=tuple(build_tags(entry, quiz_type)),
        method=method,
        confidence=max(0, min(confidence, 1)),
        persona_category=entry.persona_category,
    )


def build_classification_text(
    *,
    title: str | None = None,
    profession: str | None = None,
    custom_instruction: str | None = None,
    questions: list[Any] | None = None,
) -> str:
    parts = [title or "", profession or "", custom_instruction or ""]
    for question in questions or []:
        if isinstance(question, dict):
            parts.append(str(question.get("question", "")))
            parts.append(str(question.get("answer") or question.get("correct_answer") or ""))
        else:
            parts.append(str(getattr(question, "question", "")))
            parts.append(str(getattr(question, "answer", "") or getattr(question, "correct_answer", "")))
    return " ".join(part for part in parts if part).strip()


def classify_deterministically(text: str, quiz_type: str) -> TaxonomyClassification | None:
    entries = get_taxonomy_entries()
    if not entries or not text.strip():
        return None

    normalized_text = normalize_text(text)
    input_tokens = tokenize(text)
    best_entry: TaxonomyEntry | None = None
    best_score = 0.0

    for entry in entries:
        category_phrase = normalize_text(entry.category)
        subcategory_phrase = normalize_text(entry.subcategory)
        category_tokens = tokenize(entry.category)
        subcategory_tokens = tokenize(entry.subcategory)
        aliases = TAXONOMY_ALIASES.get(entry.subcategory_slug, set())

        score = 0.0
        if subcategory_phrase and subcategory_phrase in normalized_text:
            score += 0.65
        if category_phrase and category_phrase in normalized_text:
            score += 0.2
        if subcategory_tokens:
            score += 0.45 * (len(subcategory_tokens & input_tokens) / len(subcategory_tokens))
        if category_tokens:
            score += 0.15 * (len(category_tokens & input_tokens) / len(category_tokens))
        alias_hits = len(aliases & input_tokens)
        if alias_hits:
            score += min(0.45, alias_hits * 0.18)

        if score > best_score:
            best_score = score
            best_entry = entry

    if not best_entry or best_score < 0.35:
        return None
    return build_classification(best_entry, quiz_type, method="deterministic", confidence=best_score)


def parse_ai_classification_response(response_text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", response_text or "", re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


async def classify_with_huggingface(text: str, quiz_type: str, token: str) -> TaxonomyClassification | None:
    taxonomy = [
        {
            "category_slug": entry.category_slug,
            "subcategory_slug": entry.subcategory_slug,
            "category": entry.category,
            "subcategory": entry.subcategory,
        }
        for entry in get_taxonomy_entries()
    ]
    if not taxonomy:
        return None

    prompt = f"""
Classify this quiz using exactly one category and one subcategory from the allowed taxonomy.
Return only JSON with category_slug, subcategory_slug, tags, and confidence.
Do not invent categories, subcategories, or tags outside the allowed taxonomy.
If no category is suitable, return null category_slug and subcategory_slug values.

Allowed taxonomy:
{json.dumps(taxonomy, ensure_ascii=True)}

Quiz type: {quiz_type}
Quiz content:
{text[:4000]}
"""
    loop = asyncio.get_event_loop()
    client = InferenceClient(token=token)
    response = await loop.run_in_executor(
        None,
        functools.partial(
            client.chat.completions.create,
            model="deepseek-ai/DeepSeek-V3-0324",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0,
        ),
    )
    parsed = parse_ai_classification_response(response.choices[0].message.content)
    if not parsed:
        return None

    category_slug = parsed.get("category_slug")
    subcategory_slug = parsed.get("subcategory_slug")
    if not category_slug or not subcategory_slug:
        return None

    entry = get_taxonomy_entry_by_slugs(slugify(str(category_slug)), slugify(str(subcategory_slug)))
    if not entry:
        return None

    try:
        confidence = float(parsed.get("confidence", 0.7))
    except (TypeError, ValueError):
        confidence = 0.7
    return build_classification(entry, quiz_type, method="ai", confidence=confidence)


async def classify_quiz_taxonomy(
    *,
    quiz_type: str,
    title: str | None = None,
    profession: str | None = None,
    custom_instruction: str | None = None,
    questions: list[Any] | None = None,
    token: str | None = None,
    use_ai: bool = True,
) -> TaxonomyClassification | None:
    canonical_quiz_type = normalize_quiz_type(quiz_type)
    text = build_classification_text(
        title=title,
        profession=profession,
        custom_instruction=custom_instruction,
        questions=questions,
    )
    deterministic = classify_deterministically(text, canonical_quiz_type)
    if deterministic and deterministic.confidence >= 0.72:
        return deterministic

    final_token = token or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if use_ai and final_token:
        try:
            ai_classification = await classify_with_huggingface(text, canonical_quiz_type, final_token)
            if ai_classification:
                return ai_classification
        except Exception:
            pass

    return deterministic
