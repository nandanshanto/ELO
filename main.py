import json
from pathlib import Path
from src.commands import respond

ASSISTANT_NAME = "ELO"
MEMORY_FILE = Path(__file__).parent / "memory" / "memory.json"


def default_memory():
    return {
        "assistant_name": ASSISTANT_NAME,
        "user_name": "",
        "memories": [],
        "profile": {},
        "preferences": {}
    }


def load_memory():
    if not MEMORY_FILE.exists():
        memory = default_memory()
        save_memory(memory)
        return memory

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Memory data must be a JSON object.")

        defaults = default_memory()

        for key, value in defaults.items():
            if key not in data or not isinstance(data[key], type(value)):
                data[key] = value

        return data

    except (json.JSONDecodeError, OSError, ValueError):
        print(
            "ELO: Memory file could not be read. "
            "Your original file has not been overwritten."
        )
        return default_memory()


def save_memory(memory):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_file = MEMORY_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(
            memory,
            file,
            ensure_ascii=False,
            indent=4
        )

    temp_file.replace(MEMORY_FILE)


def run_cli():
    memory = load_memory()

    print(f"\n{ASSISTANT_NAME}: System online!")
    print("Type 'help' for commands or 'exit' to quit.")

    while True:
        user_input = input("\nYou: ")
        reply = respond(user_input, memory, save_memory)
        print(f"\n{ASSISTANT_NAME}: {reply}")

        if user_input.strip().lower() == "exit":
            break


if __name__ == "__main__":
    run_cli()
