import argparse
import json
import urllib.request

MODEL = "llama3.2:latest"


def call_ollama(prompt, temperature):
    data = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature
        }
    }

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())

    return json.loads(result["response"])


def planner(title, content, temperature):
    prompt = f"""
You are a planner.

Title: {title}
Content: {content}

Create exactly 3 tags and a summary with no more than 25 words.

Return only JSON like this:
{{
    "tags": ["tag1", "tag2", "tag3"],
    "summary": "short summary"
}}
"""

    return call_ollama(prompt, temperature)


def reviewer(title, content, plan, temperature):
    prompt = f"""
You are a reviewer.

Title: {title}
Content: {content}

Planner result:
{json.dumps(plan)}

Check that there are exactly 3 relevant tags and that the summary is accurate
and no longer than 25 words.

Return only JSON like this:
{{
    "tags": ["tag1", "tag2", "tag3"],
    "summary": "short summary",
    "changed": true,
    "reason": "short reason"
}}
"""

    return call_ollama(prompt, temperature)


def finalize(review):
    tags = review["tags"][:3]
    words = review["summary"].split()

    if len(words) > 25:
        words = words[:25]

    return {
        "tags": tags,
        "summary": " ".join(words)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--temperature", type=float, default=0.0)

    args = parser.parse_args()

    plan = planner(args.title, args.content, args.temperature)

    print("\nPlanner output:")
    print(json.dumps(plan, indent=2))

    review = reviewer(
        args.title,
        args.content,
        plan,
        args.temperature
    )

    print("\nReviewer output:")
    print(json.dumps(review, indent=2))

    final = finalize(review)

    print("\nFinalized output:")
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    main()