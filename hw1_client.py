import json
from src.model_client import complete

with open("AGENT.md") as file:
    system_prompt = file.read()

messages = [
    {
        "role": "system",
        "content": system_prompt
    }
]

turns = 0
total_input = 0
total_output = 0
token_data = []


def show_stats():
    print("\nStats")
    print("Turns:", turns)
    print("Input tokens:", total_input)
    print("Output tokens:", total_output)
    print("History length:", len(str(messages)))


print("Code Review Client")
print("Type /stats for statistics or /exit to quit.")

while True:
    user_input = input("\nYou: ")

    # Ignore blank input
    if not user_input.strip():
        continue

    if user_input == "/exit":
        break

    if user_input == "/stats":
        show_stats()
        continue

    messages.append({
        "role": "user",
        "content": user_input
    })

    result = complete(messages)

    messages.append({
        "role": "assistant",
        "content": result["message"]
    })

    turns += 1
    total_input += result["input_tokens"]
    total_output += result["output_tokens"]

    token_data.append({
        "turn": turns,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "total_tokens": result["input_tokens"] + result["output_tokens"]
    })

    print("\nAssistant:")
    print(result["message"])

    print(
        "\nTokens - Input:",
        result["input_tokens"],
        "Output:",
        result["output_tokens"],
        "Total:",
        result["input_tokens"] + result["output_tokens"]
    )


print("\nFinal Stats")
show_stats()

with open("reports/hw01/raw/part4_tokens.json", "w") as file:
    json.dump(
        {
            "turns": token_data,
            "total_turns": turns,
            "cumulative_input_tokens": total_input,
            "cumulative_output_tokens": total_output
        },
        file,
        indent=2
    )

print("\nToken data saved to reports/hw01/raw/part4_tokens.json")