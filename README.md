# poputi_bot

## Setup (Windows / VS Code F5 friendly)

1) Install dependencies:
```bash
python -m pip install -r requirements.txt
```

2) Create `.env` (or rename `.env.example` -> `.env`) and set your token:
```env
BOT_TOKEN=YOUR_TOKEN_HERE
```

3) Run:
```bash
python main.py
```

## What it does
- /start: shows a download button to https://short.poputi.am
- Notifies admins (IDs inside main.py) about each /start click
