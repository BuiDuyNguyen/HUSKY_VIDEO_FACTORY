import json

from src.ai.script_generator import (
    generate_script,
)


content = {
    "title": "Husky tries to work from home",

    "idea": (
        "A husky starts working from home "
        "and thinks life will be relaxing. "
        "But meetings, emails and deadlines "
        "slowly destroy his mental peace."
    ),

    "duration": 3,

    "language": "English",

    "tone": (
        "Funny, sarcastic, relatable"
    ),

    "audience": (
        "Office workers, young adults"
    ),

    "notes": (
        "Keep the humor simple. "
        "Use awkward meme-like reactions. "
        "Keep the story focused on the husky "
        "struggling with working from home."
    ),
}


result = generate_script(
    content
)


print()
print("=" * 70)
print("FINAL SCRIPT")
print("=" * 70)

print(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=4,
    )
)