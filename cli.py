import json
import sys
from pathlib import Path

from api.services.option_b_cleaner.render import render


def main() -> None:
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    data = json.loads(in_path.read_text(encoding="utf-8"))
    output = render(data)
    out_path.write_text(output, encoding="utf-8")
    print(f"Wrote cleaned JSON → {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python cli.py input.json output.json")
        sys.exit(1)
    main()
