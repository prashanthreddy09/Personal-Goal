"""Local API server and static website for Personal Goal Review.

Run from this project folder with: py api_server.py
Then open: http://127.0.0.1:8000
"""
import csv
import io
import json
import mimetypes
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
DATA_FILE = DATA_DIR / "goals.json"
STATIC_DIR = BASE_DIR / "static"


def load_goals():
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        save_goals([])
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_goals(goals):
    DATA_DIR.mkdir(exist_ok=True)
    temp = DATA_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(goals, indent=4, ensure_ascii=False), encoding="utf-8")
    temp.replace(DATA_FILE)


def status(goal):
    if goal.get("progress", 0) >= 100:
        return "Completed"
    deadline = goal.get("deadline", "")
    if deadline:
        try:
            if date.fromisoformat(deadline) < date.today():
                return "Overdue"
        except ValueError:
            pass
    return "In Progress" if goal.get("progress", 0) > 0 else "Not Started"


def enrich(goal):
    item = dict(goal)
    item["status"] = status(item)
    item["milestones_completed"] = sum(1 for m in item.get("milestones", []) if m.get("done"))
    item["milestones_total"] = len(item.get("milestones", []))
    return item


def summary(goals):
    total = len(goals)
    counts = {name: sum(1 for g in goals if status(g) == name)
              for name in ("Completed", "In Progress", "Not Started", "Overdue")}
    average = round(sum(g.get("progress", 0) for g in goals) / total, 1) if total else 0
    milestone_total = sum(len(g.get("milestones", [])) for g in goals)
    milestone_done = sum(sum(1 for m in g.get("milestones", []) if m.get("done")) for g in goals)
    categories = {}
    for goal in goals:
        categories.setdefault(goal.get("category", "Other"), []).append(goal)
    category_data = [
        {"name": name, "count": len(items),
         "average": round(sum(g.get("progress", 0) for g in items) / len(items), 1)}
        for name, items in sorted(categories.items())
    ]
    return {
        "total": total, "completed": counts["Completed"],
        "in_progress": counts["In Progress"], "not_started": counts["Not Started"],
        "overdue": counts["Overdue"], "average": average,
        "milestones_done": milestone_done, "milestones_total": milestone_total,
        "categories": category_data
    }


class GoalHandler(BaseHTTPRequestHandler):
    def send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, content_type=None):
        if not path.is_file():
            self.send_error(404, "File not found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("Request is too large.")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            return self.send_file(BASE_DIR / "index.html", "text/html; charset=utf-8")
        if parsed.path.startswith("/static/"):
            relative = unquote(parsed.path[len("/static/"):])
            path = (STATIC_DIR / relative).resolve()
            if STATIC_DIR.resolve() not in path.parents:
                return self.send_error(403)
            return self.send_file(path)

        goals = load_goals()
        if parsed.path == "/api/goals":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0].lower().strip()
            category = params.get("category", [""])[0].lower().strip()
            wanted_status = params.get("status", [""])[0].lower().strip()
            results = []
            for goal in goals:
                searchable = " ".join([
                    goal.get("title", ""), goal.get("category", ""),
                    goal.get("description", ""), goal.get("reflection", ""),
                    " ".join(m.get("name", "") for m in goal.get("milestones", []))
                ]).lower()
                if query and query not in searchable:
                    continue
                if category and category not in goal.get("category", "").lower():
                    continue
                if wanted_status and wanted_status != status(goal).lower():
                    continue
                results.append(enrich(goal))
            return self.send_json(200, {"goals": results})
        if parsed.path == "/api/summary":
            return self.send_json(200, summary(goals))
        if parsed.path == "/api/export/csv":
            output = io.StringIO()
            fields = ["id", "title", "category", "description", "deadline", "progress",
                      "status", "milestones_completed", "milestones_total", "reflection", "created", "updated"]
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for goal in goals:
                writer.writerow(enrich(goal))
            body = output.getvalue().encode("utf-8-sig")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="goal_report.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if parsed.path == "/api/export/markdown":
            stats = summary(goals)
            lines = ["# Personal Goal Review Report", "", f"Generated: {date.today().isoformat()}",
                     "", "## Summary", f"- Total goals: {stats['total']}",
                     f"- Completed goals: {stats['completed']}",
                     f"- Average progress: {stats['average']}%", "", "## Goal Details",
                     "| ID | Goal | Category | Progress | Status | Deadline |",
                     "|---:|---|---|---:|---|---|"]
            for g in goals:
                lines.append(f"| {g['id']} | {g['title'].replace('|', '/')} | {g['category'].replace('|', '/')} | {g['progress']}% | {status(g)} | {g.get('deadline') or '-'} |")
            body = "\n".join(lines).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="goal_summary.md"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        return self.send_json(404, {"error": "Endpoint not found."})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_body()
            goals = load_goals()
            if parsed.path != "/api/goals":
                return self.send_json(404, {"error": "Endpoint not found."})
            title = str(data.get("title", "")).strip()
            category = str(data.get("category", "")).strip()
            if not title or len(title) > 80:
                return self.send_json(400, {"error": "Enter a goal title (up to 80 characters)."})
            if not category or len(category) > 40:
                return self.send_json(400, {"error": "Enter a category (up to 40 characters)."})
            deadline = str(data.get("deadline", "")).strip()
            if deadline:
                date.fromisoformat(deadline)
            milestones = []
            for name in data.get("milestones", []):
                name = str(name).strip()
                if name:
                    if len(name) > 100:
                        raise ValueError("Milestone names must be 100 characters or fewer.")
                    milestones.append({"name": name, "done": False})
            new_id = max([g.get("id", 0) for g in goals] + [0]) + 1
            today = date.today().isoformat()
            goal = {"id": new_id, "title": title, "category": category,
                    "description": str(data.get("description", "")).strip()[:500],
                    "deadline": deadline, "progress": 0, "milestones": milestones,
                    "reflection": str(data.get("reflection", "")).strip()[:1000],
                    "created": today, "updated": today}
            goals.append(goal)
            save_goals(goals)
            return self.send_json(201, {"goal": enrich(goal)})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            return self.send_json(400, {"error": str(error) or "Invalid request."})

    def do_PUT(self):
        parsed = urlparse(self.path)
        try:
            goal_id = int(parsed.path.rsplit("/", 1)[-1])
            data = self.read_body()
            goals = load_goals()
            goal = next((g for g in goals if g.get("id") == goal_id), None)
            if goal is None:
                return self.send_json(404, {"error": "Goal not found."})
            title = str(data.get("title", goal["title"])).strip()
            category = str(data.get("category", goal["category"])).strip()
            if not title or len(title) > 80 or not category or len(category) > 40:
                return self.send_json(400, {"error": "Check the goal title and category."})
            progress = int(data.get("progress", goal["progress"]))
            if not 0 <= progress <= 100:
                return self.send_json(400, {"error": "Progress must be between 0 and 100."})
            deadline = str(data.get("deadline", goal.get("deadline", ""))).strip()
            if deadline:
                date.fromisoformat(deadline)
            old_milestones = {m["name"]: m.get("done", False) for m in goal.get("milestones", [])}
            milestones = []
            for entry in data.get("milestones", [m["name"] for m in goal.get("milestones", [])]):
                if isinstance(entry, dict):
                    name = str(entry.get("name", "")).strip()
                    done = bool(entry.get("done", False))
                else:
                    name = str(entry).strip()
                    done = old_milestones.get(name, False)
                if name:
                    milestones.append({"name": name, "done": done})
            goal.update({"title": title, "category": category,
                         "description": str(data.get("description", goal.get("description", ""))).strip()[:500],
                         "deadline": deadline, "progress": progress,
                         "milestones": milestones,
                         "reflection": str(data.get("reflection", goal.get("reflection", ""))).strip()[:1000],
                         "updated": date.today().isoformat()})
            save_goals(goals)
            return self.send_json(200, {"goal": enrich(goal)})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            return self.send_json(400, {"error": str(error) or "Invalid request."})

    def do_DELETE(self):
        try:
            goal_id = int(urlparse(self.path).path.rsplit("/", 1)[-1])
            goals = load_goals()
            remaining = [g for g in goals if g.get("id") != goal_id]
            if len(remaining) == len(goals):
                return self.send_json(404, {"error": "Goal not found."})
            save_goals(remaining)
            return self.send_json(200, {"message": "Goal deleted."})
        except ValueError:
            return self.send_json(400, {"error": "Invalid goal ID."})


def run_server(host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), GoalHandler)
    print(f"Personal Goal Review is running at http://{host}:{port}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
