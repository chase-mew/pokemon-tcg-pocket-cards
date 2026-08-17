import json

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def collect(cards, check):
    """check(card) -> message when broken, None when fine."""
    out = []
    for card in cards:
        msg = check(card)
        if msg:
            out.append(f"{card['id']} ({card.get('name')}): {msg}")
    return out


def report(fails):
    """Assertion message: first 20 failures plus a count."""
    return f"{len(fails)} failure(s)\n" + "\n".join(fails[:20])