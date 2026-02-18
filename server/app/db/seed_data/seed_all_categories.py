import os

from datetime import datetime, timezone

from pathlib import Path

import importlib.util


from dotenv import load_dotenv

from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv()


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

DB_NAME = os.getenv("MONGO_DB_NAME", "quizApp_db")

COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "quizzes_category")


client = AsyncIOMotorClient(MONGO_URI)

db = client[DB_NAME]

quiz_collection = db[COLLECTION_NAME]


BASE_DIR = Path(__file__).resolve().parent / "categories"


def load_data_from_py(filepath):

    spec = importlib.util.spec_from_file_location("questions_module", filepath)

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return getattr(module, "data", [])



type_map = {

    "multiple choice": range(0, 10),

    "true or false": range(10, 20),

    "open ended": range(20, 30),

    "short answer": range(30, 40),

}


def assign_question_types(questions: list) -> list:

    for i, q in enumerate(questions):

        if "question_type" not in q or not q["question_type"].strip():

            for qtype, qrange in type_map.items():

                if i in qrange:

                    q["question_type"] = qtype

                    break

            else:

                q["question_type"] = "unknown"

    return questions


async def seed_category(category_dir: str, category: str, subcategory: str):

    questions_path = BASE_DIR / category_dir / subcategory / "questions.py"


    if not questions_path.exists():

        print(f"⚠️ No questions.py for {category} > {subcategory}")

        return


    try:

        questions = load_data_from_py(str(questions_path))

    except Exception as e:

        print(f"❌ Error loading {questions_path}: {e}")

        return


    if not questions:

        print(f"⚠️ No questions in {questions_path}")

        return



    questions = assign_question_types(questions)


    grouped = {}

    for q in questions:

        qtype = q.get("question_type", "unknown").strip().lower()

        grouped.setdefault(qtype, []).append(q)


    for qtype, group in grouped.items():

        exists = await quiz_collection.find_one({

            "category": category,

            "subcategory": subcategory,

            "question_type": qtype

        })

        if exists:

            print(f"⏩ Skipping {category} > {subcategory} ({qtype}) — already seeded.")

            continue


        doc = {

            "category": category,

            "subcategory": subcategory,

            "question_type": qtype,

            "questions": group,

            "created_at": datetime.now(timezone.utc)

        }

        await quiz_collection.insert_one(doc)

        print(f"✅ Seeded {len(group)} questions for {category} > {subcategory} ({qtype})")


async def seed_all():

    for category_dir in os.listdir(BASE_DIR):

        category_path = BASE_DIR / category_dir

        if not category_path.is_dir():

            continue


        category_name = category_dir.replace("_", " ").replace("&", "and").capitalize()


        for subcategory_dir in os.listdir(category_path):

            sub_path = category_path / subcategory_dir

            if not sub_path.is_dir():

                continue


            subcategory_name = subcategory_dir.replace("_", " ").replace("&", "and").capitalize()

            await seed_category(category_dir, category_name, subcategory_dir)


if __name__ == "__main__":

    import asyncio

    print("🚀 Seeding quizzes_category...")

    asyncio.run(seed_all())

    print("🎉 Done seeding!")

