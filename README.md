# PDF Quote Editor

A small web tool to fill out PDF quotes faster. Place text fields and a signature on top of any PDF, save the layout as a **template**, and reuse it on the next document. You only type the data.

I built it (with Claude's help) while bidding on public contracts, where every quote asks for the same basic details over and over. It cut my filling time from **10 minutes to 3**, leaving more time to price the product or service.

## Features

- Upload a PDF and preview it page by page
- Click anywhere on the PDF to add a text field
- Drag fields, and right-click to change the font size
- Add a signature image, then move and resize it
- Save field positions as a reusable template
- Apply a template to a new PDF and download the finished file

## Tech stack

- **Backend:** Python, FastAPI, pypdf, ReportLab
- **Frontend:** HTML + JavaScript, PDF.js

## Getting started

```bash
# 1. Clone the repository
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO

# 2. (Optional) create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
uvicorn main:app --reload
```

Then open http://127.0.0.1:8000 in your browser.

## How to use

1. Upload a PDF.
2. Click on the PDF to place the fields you need.
3. Type a name and click **Save as template**.
4. Next time, upload a new PDF and pick your template. The fields appear in place.
5. Type the data, add your signature if needed, and click **Save PDF**.

## Project structure

```
.
├── main.py            # FastAPI server
├── static/
│   └── index.html     # Editor interface
├── requirements.txt
└── README.md
```

The `subidos/` (uploads) and `plantillas/` (templates) folders are created automatically on first run and are not tracked by Git, so your documents stay private.

## Privacy note

Uploaded PDFs and templates are stored locally in `subidos/` and `plantillas/`. Do not commit real client documents or signature images to a public repository.

## License

MIT
