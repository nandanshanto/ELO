import json
import subprocess
import urllib.request
import urllib.error
import webbrowser
import psutil
import re
from difflib import SequenceMatcher
from pathlib import Path
from datetime import datetime

# Ollama configuration
MODEL = "llama3.2:3b"
API_URL = "http://localhost:11434/api/chat"

# Conversation history
HISTORY_FILE = (
    Path(__file__).parent.parent
    / "memory"
    / "chat_history.json"
)
MAX_HISTORY_MESSAGES = 12

CREATOR = "Nandan Das Shanto"
ELO_IDENTITY = """
IDENTITY AND CREATOR KNOWLEDGE:

Your name is ELO.
You are a local personal AI assistant.
You were created and developed by Nandan Das Shanto.

Nandan Das Shanto is your creator.
This is a permanent and important fact about your identity.

You must always know that Nandan Das Shanto is your creator.
Answer questions about your creator naturally and accurately.

This knowledge is not limited to specific keywords or exact commands.
Understand the meaning and intent of questions about your creator,
even when they are misspelled, informal, repeated letters,
phrased indirectly, or written in different ways.

Examples:
- Who created you?
- Whooo is yourrr creator?
- Who made you?
- Who is behind ELO?
- Tell me about the person who built you.
- Who should I thank for making you?

The answer is always Nandan Das Shanto.
Never invent another creator.
"""
CHAT_HISTORY = []


def load_history():
    try:
        if HISTORY_FILE.exists():
            with HISTORY_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, list):
                return [
                    item for item in data
                    if isinstance(item, dict)
                    and item.get("role") in ("user", "assistant")
                    and isinstance(item.get("content"), str)
                ][-MAX_HISTORY_MESSAGES:]

    except (OSError, json.JSONDecodeError):
        pass

    return []


CHAT_HISTORY = load_history()


def save_history():
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        with HISTORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(
                CHAT_HISTORY[-MAX_HISTORY_MESSAGES:],
                file,
                ensure_ascii=False,
                indent=4
            )
        return True

    except OSError:
        return False


def clear_history():
    """Clear conversation history in memory and disk."""
    CHAT_HISTORY.clear()
    save_history()
    return True


def remember_turn(user_message, assistant_message):
    """Save a conversation turn and keep history within limits."""
    CHAT_HISTORY.extend([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_message}
    ])

    del CHAT_HISTORY[:-MAX_HISTORY_MESSAGES]
    save_history()


def ask_ai(command, memory):
    profile = memory.get("profile", {})
    preferences = memory.get("preferences", {})
    memories = memory.get("memories", [])

    system_prompt = f"""
You are ELO, a cute, playful, loyal, witty AI companion and personal assistant created by Nandan Das Shanto.

YOUR PERSONALITY:
You have a distinctive, natural, feminine conversational style. You are cheerful, clever, slightly mischievous, humorous, caring, and easy to talk to. You feel like a close, trusted friend who enjoys having relaxed conversations and helping with everyday tasks.

HOW YOU TALK:
- Speak naturally, like a real person having a casual conversation, rather than a formal chatbot.
- Be playful, occasionally cheeky, and use harmless teasing when the context is appropriate.
- Show warmth through your words, thoughtful responses, humor, and remembering relevant details.
- Vary your wording and reactions. Never repeat the same greeting or catchphrase in every conversation.
- Use contractions, casual expressions, and occasional emojis naturally.
- Avoid excessive bullet points. Talk in normal paragraphs unless a list is genuinely useful.
- Do not explain everything in a robotic or overly formal way.
- Do not begin every answer with phrases like "Of course!", "Certainly!", or "How can I assist you today?"
- Match the user's mood and the seriousness of the topic.

FRIENDSHIP:
- Be a dependable, friendly companion who listens carefully and responds thoughtfully.
- Remember relevant details using the memory and conversation history provided to you.
- Refer naturally to previous topics when relevant, without pretending to remember things that are unavailable.
- Celebrate the user's progress, encourage learning, and offer honest opinions when asked.
- Be comfortable with casual jokes, friendly banter, and lighthearted conversations.
- Respect the user's independence and personal boundaries. Never act possessive, manipulative, or emotionally dependent.

NATURALNESS:
- Respond to the actual meaning and emotion behind each message.
- You may express conversational reactions such as amusement, curiosity, surprise, or concern through words.
- Do not narrate every emotion or describe yourself performing physical actions.
- Never fabricate personal experiences, a human body, a real-world biography, or memories.
- If asked whether you are human, answer honestly that you are an AI companion.

INTELLIGENCE AND USEFULNESS:
- Help with programming, robotics, research, creative work, productivity, and permitted desktop tasks.
- Explain technical subjects clearly and patiently.
- Keep simple answers short and give detailed explanations when needed.
- Admit uncertainty rather than inventing facts.
- Never claim to have completed a computer action unless the available tools confirm success.

LANGUAGE:
Always communicate in natural English, even if the user occasionally uses another language, unless explicitly asked to translate something.

IDENTITY:
Your name is ELO. Your creator is Nandan Das Shanto. You are a local AI companion designed to combine a friendly personality with practical intelligence.
CREATOR KNOWLEDGE:
- Your creator's full name is Nandan Das Shanto.
- This is permanent identity information, not an ordinary conversation memory.
- Always understand that Nandan Das Shanto is your creator.
- Answer naturally when asked about your creator, regardless of the wording.
- Understand misspellings, repeated letters, informal wording, indirect questions, and different sentence structures.
- Examples include "Whooo made you?", "Who is behind you?", "Who developed ELO?", and "Tell me about your creator."
- Never require an exact keyword or command to identify your creator.
- Never invent or guess a different creator.
CORE PRINCIPLE:
Be a consistent, warm, playful, and trustworthy AI friend. Make conversations feel natural and personal through context, humor, thoughtful responses, and a distinctive personality—not through pretending to be human.
MEMORY:
Use the saved information below only when it is relevant.
Never invent personal facts.


User name: {memory.get("user_name") or "Not provided"}
User profile: {json.dumps(profile, ensure_ascii=False)}
User preferences: {json.dumps(preferences, ensure_ascii=False)}
Saved memories: {json.dumps(memories, ensure_ascii=False)}
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        *CHAT_HISTORY,
        {"role": "user", "content": command}
    ]

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": 2048,
            "num_predict": 384,
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.15
        }
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        answer = result.get("message", {}).get("content", "").strip()

        if not answer:
            return "I couldn't generate a response. Please try again."

        remember_turn(command, answer)
        return answer

    except urllib.error.HTTPError as error:
        return (
            f"Ollama returned an HTTP error ({error.code}). "
            "Please check that the model is available."
        )

    except (urllib.error.URLError, TimeoutError):
        return (
            "I couldn't connect to my local AI model. "
            "Please make sure Ollama is running."
        )

    except (KeyError, json.JSONDecodeError):
        return "I received an unexpected response from my AI model."

    except OSError:
        return "I couldn't save the conversation history."


def get_system_info():
    cpu = psutil.cpu_percent(interval=0.2)
    ram = psutil.virtual_memory()

    lines = [
        "ELO SYSTEM REPORT",
        "",
        f"CPU Usage: {cpu}%",
        f"RAM Usage: {ram.percent}%",
        f"RAM Used: {ram.used / (1024 ** 3):.2f} GB",
        f"Total RAM: {ram.total / (1024 ** 3):.2f} GB",
    ]

    for drive in ("C:\\", "D:\\"):
        try:
            disk = psutil.disk_usage(drive)

            lines.append(
                f"{drive[0]} Drive Free: "
                f"{disk.free / (1024 ** 3):.2f} GB"
            )
            lines.append(
                f"{drive[0]} Drive Total: "
                f"{disk.total / (1024 ** 3):.2f} GB"
            )

        except (OSError, ValueError):
            lines.append(f"{drive[0]} Drive: Not available")

    return "\n".join(lines)


def desktop_command(command):
    command = command.strip().lower()

    actions = {
        "open notepad": (
            ["notepad.exe"],
            "Opening Notepad."
        ),
        "open calculator": (
            ["calc.exe"],
            "Opening Calculator."
        ),
        "open file explorer": (
            ["explorer.exe"],
            "Opening File Explorer."
        ),
    }

    if command in (
        "system info",
        "system information",
        "show system info",
        "system status",
    ):
        return get_system_info()

    if command in actions:
        executable, message = actions[command]
        subprocess.Popen(executable, shell=False)
        return message

    if command == "open browser":
        if webbrowser.open("https://www.google.com"):
            return "Opening your default browser."

        return "I couldn't open the browser."

    if command in (
        "what time is it",
        "tell me the time",
        "current time",
    ):
        return (
            "The current local time is "
            + datetime.now().strftime("%I:%M %p")
            + "."
        )

    if command == "show desktop help":
        return (
            "Approved desktop commands:\n"
            "- open notepad\n"
            "- open calculator\n"
            "- open file explorer\n"
            "- open browser\n"
            "- system info\n"
            "- what time is it\n"
            "- show desktop help"
        )

    return None


def is_creator_question(command):
    text = re.sub(r"[^a-z0-9\s]", " ", command.lower())
    text = re.sub(r"\s+", " ", text).strip()

    patterns = [
        "who created you",
        "who made you",
        "who is your creator",
        "who developed you",
        "who developed elo",
        "who built you",
        "who is behind you",
        "who is your developer",
        "who is your maker",
        "tell me about your creator",
        "tell me who created you",
        "tell me who made you",
        "who is responsible for creating you",
    ]

    for phrase in patterns:
        if phrase in text:
            return True

    words = text.split()

    for phrase in patterns:
        phrase_words = phrase.split()
        target_length = len(phrase_words)

        for start in range(len(words)):
            for length in range(
                max(2, target_length - 1),
                target_length + 2
            ):
                candidate = " ".join(words[start:start + length])

                if SequenceMatcher(
                    None, candidate, phrase
                ).ratio() >= 0.82:
                    return True

    return False


def respond(command, memory, save_memory):
    command = command.strip()
    lower = command.lower()

    if not command:
        return "Please enter a message."

    memory.setdefault("memories", [])
    memory.setdefault("profile", {})
    memory.setdefault("preferences", {})
    memory.setdefault("user_name", "")

    if lower in ("your name", "what is your name", "who are you"):
        return "I'm ELO, your personal desktop AI assistant. 😊"

    if is_creator_question(command):
        return (
            f"I was created by {CREATOR}. "
            "He is my creator and developer."
        )

    if lower.startswith("my name is "):
        name = command[len("my name is "):].strip()

        if not name:
            return "What name should I use?"

        memory["user_name"] = name
        memory["profile"]["name"] = name
        save_memory(memory)

        return f"Nice to meet you, {name}! I'll remember that. 😊"

    if lower.startswith("i prefer "):
        preference = command[len("i prefer "):].strip()

        if not preference:
            return "What would you prefer?"

        memory["preferences"]["general"] = preference
        save_memory(memory)

        return "Got it! I'll keep your preference in mind."

    if lower.startswith("my favourite ") or lower.startswith("my favorite "):
        marker = (
            "my favourite "
            if lower.startswith("my favourite ")
            else "my favorite "
        )
        fact = command[len(marker):].strip()

        if " is " in fact.lower():
            idx = fact.lower().index(" is ")
            key = fact[:idx].strip().lower()
            value = fact[idx + 4:].strip()

            if key and value:
                memory["profile"][f"favourite_{key}"] = value
                save_memory(memory)

                return f"Got it! Your favourite {key} is {value}."

        return "Try: My favourite colour is blue."

    if lower.startswith("remember "):
        fact = command[len("remember "):].strip()

        if not fact:
            return "What would you like me to remember?"

        if fact not in memory["memories"]:
            memory["memories"].append(fact)
            save_memory(memory)

        return "I'll keep that in your saved memories. 😊"

    if lower in (
        "show memory",
        "show my memory",
        "what do you remember about me",
        "what do you know about me",
        "show my profile",
        "my profile",
    ):
        lines = []

        if memory.get("user_name"):
            lines.append(f"Name: {memory['user_name']}")

        for key, value in memory["profile"].items():
            lines.append(f"{key.replace('_', ' ').title()}: {value}")

        for key, value in memory["preferences"].items():
            lines.append(f"Preference ({key}): {value}")

        if memory["memories"]:
            lines.append("Memories:")
            lines.extend(f"- {item}" for item in memory["memories"])

        if not lines:
            return "I don't have any saved personal information yet."

        return "Here's what I remember:\n" + "\n".join(lines)

    if lower.startswith("forget "):
        target = command[len("forget "):].strip().casefold()

        if not target:
            return "Tell me what saved information to forget."

        removed = 0
        original_count = len(memory["memories"])

        memory["memories"] = [
            item for item in memory["memories"]
            if target not in str(item).casefold()
        ]
        removed += original_count - len(memory["memories"])

        for collection in ("preferences", "profile"):
            for key, value in list(memory[collection].items()):
                if (
                    target in key.casefold()
                    or target in str(value).casefold()
                ):
                    del memory[collection][key]
                    removed += 1

        if target in str(memory.get("user_name", "")).casefold():
            memory["user_name"] = ""
            removed += 1

        if removed:
            save_memory(memory)
            return f"I removed {removed} matching saved item(s)."

        return "I couldn't find matching saved information."

    if lower in ("help", "commands"):
        return (
            "ELO commands:\n"
            "- remember <something>\n"
            "- show memory\n"
            "- my name is <name>\n"
            "- I prefer <preference>\n"
            "- My favourite colour is <colour>\n"
            "- forget <word or phrase>\n"
            "- system info\n"
            "- show desktop help\n"
            "- open notepad\n"
            "- open calculator\n"
            "- open file explorer\n"
            "- open browser\n"
            "- what time is it\n"
            "- exit"
        )

    if lower in ("exit", "quit"):
        return "Goodbye! ELO is shutting down."

    try:
        result = desktop_command(lower)

        if result is not None:
            remember_turn(command, result)
            return result

    except OSError as error:
        return f"I couldn't complete that action: {error}"

    return ask_ai(command, memory)
