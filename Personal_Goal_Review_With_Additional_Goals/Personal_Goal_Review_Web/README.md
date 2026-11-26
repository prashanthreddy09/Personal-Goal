# Personal Goal Review

A beginner-friendly goal tracker with two interfaces:
- A terminal application (`main.py`)
- A browser interface with a separate `index.html` file

The website is served by `api_server.py` using Python's standard library. No framework or pip installation is required.

## Project files

- `index.html` — website structure
- `static/style.css` — website design
- `static/script.js` — browser interactions
- `api_server.py` — local API and web server
- `main.py` — original terminal application
- `data/goals.json` — shared saved goals
- `reports/` — exported reports

## Run the website

1. Extract the ZIP file.
2. Open the extracted folder in VS Code.
3. Open the terminal in that folder.
4. Run:

   ```powershell
   py api_server.py
   ```

5. Open `http://127.0.0.1:8000` in your browser.

Keep the terminal open while using the website. Press `Ctrl+C` to stop the server.

## Run the terminal version

Open a second terminal in the same project folder and run:

```powershell
py main.py
```

Both versions read and update the same `data/goals.json` file.

## Features

- Add, edit and delete goals
- Set category, description and deadline
- Track progress from 0% to 100%
- Add and complete milestones
- Add reflection notes
- Search and filter goals
- Dashboard summary and category analytics
- Export CSV and Markdown reports
- Local JSON storage

This application runs locally on your computer. Keep the project folder together so the HTML, static files and JSON data remain in their expected locations.
