"""
PERSONAL GOAL REVIEW
A beginner-friendly goal tracker using only the Python standard library.
Run: python main.py
"""

import csv
import json
import os
from datetime import date, datetime

DATA_DIR = "data"
REPORT_DIR = "reports"
DATA_FILE = os.path.join(DATA_DIR, "goals.json")
DATE_FORMAT = "%Y-%m-%d"


# ---------- Terminal display ----------

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def line():
    print("-" * 76)


def heading(title):
    print()
    line()
    print(title.center(76))
    line()


def pause():
    input("\nPress Enter to continue...")


def print_banner():
    clear_screen()
    print("=" * 76)
    print("                    PERSONAL GOAL REVIEW")
    print("                 Plan  |  Track  |  Reflect")
    print("=" * 76)
    print("A simple offline tool to manage goals and measure your progress.")


# ---------- Data validation ----------

def clean_text(prompt, allow_blank=False, max_length=200):
    while True:
        value = input(prompt).strip()
        if not value and not allow_blank:
            print("Input cannot be empty. Please try again.")
        elif len(value) > max_length:
            print("Please keep the input within", max_length, "characters.")
        else:
            return value


def read_percentage(prompt, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(prompt + suffix + ": ").strip()
        if raw == "" and default is not None:
            return default
        try:
            value = int(raw)
            if 0 <= value <= 100:
                return value
            print("Enter a whole number from 0 to 100.")
        except ValueError:
            print("Please enter a valid whole number.")


def read_date(prompt, allow_blank=False):
    while True:
        raw = input(prompt + " (YYYY-MM-DD): ").strip()
        if raw == "" and allow_blank:
            return ""
        try:
            parsed = datetime.strptime(raw, DATE_FORMAT).date()
            return parsed.isoformat()
        except ValueError:
            print("Invalid date. Example: 2026-12-31")


def read_choice(prompt, choices):
    valid = [str(item) for item in choices]
    while True:
        value = input(prompt).strip()
        if value in valid:
            return value
        print("Choose one of:", ", ".join(valid))


# ---------- Storage ----------

def ensure_folders():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)


def save_goals(goals):
    ensure_folders()
    temporary_file = DATA_FILE + ".tmp"
    try:
        with open(temporary_file, "w", encoding="utf-8") as file:
            json.dump(goals, file, indent=4, ensure_ascii=False)
        os.replace(temporary_file, DATA_FILE)
        return True
    except (OSError, TypeError) as error:
        print("Could not save data:", error)
        if os.path.exists(temporary_file):
            os.remove(temporary_file)
        return False


def load_goals():
    ensure_folders()
    if not os.path.exists(DATA_FILE):
        save_goals([])
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError("The JSON file must contain a list of goals.")

        valid_goals = []
        for item in data:
            if isinstance(item, dict) and validate_record(item):
                valid_goals.append(item)
            else:
                print("Warning: An invalid record was skipped.")
        return valid_goals

    except (json.JSONDecodeError, OSError, ValueError) as error:
        print("Warning: Could not read saved data:", error)
        print("Starting with an empty goal list. The original file is left untouched.")
        return []


def validate_record(goal):
    required = ["id", "title", "category", "description", "deadline",
                "progress", "milestones", "reflection", "created"]
    if not all(key in goal for key in required):
        return False
    if not isinstance(goal["progress"], int) or not 0 <= goal["progress"] <= 100:
        return False
    if not isinstance(goal["milestones"], list):
        return False
    for milestone in goal["milestones"]:
        if not isinstance(milestone, dict):
            return False
        if "name" not in milestone or "done" not in milestone:
            return False
        if not isinstance(milestone["done"], bool):
            return False
    return True


# ---------- Goal calculations ----------

def goal_status(goal):
    if goal["progress"] == 100:
        return "Completed"
    if goal["deadline"]:
        try:
            due = date.fromisoformat(goal["deadline"])
            if due < date.today():
                return "Overdue"
        except ValueError:
            pass
    if goal["progress"] > 0:
        return "In Progress"
    return "Not Started"


def milestone_counts(goal):
    total = len(goal["milestones"])
    completed = sum(1 for item in goal["milestones"] if item["done"])
    return completed, total


def next_goal_id(goals):
    return max([goal.get("id", 0) for goal in goals] + [0]) + 1


# ---------- Main actions ----------

def add_goal(goals):
    heading("ADD A NEW GOAL")
    title = clean_text("Goal title: ", max_length=80)
    category = clean_text("Category (Study/Fitness/Personal/Work etc.): ", max_length=40)
    description = clean_text("Description: ", allow_blank=True, max_length=500)
    deadline = read_date("Deadline", allow_blank=True)

    milestones = []
    print("\nAdd milestones (leave the name blank when finished).")
    while True:
        name = input("Milestone name: ").strip()
        if not name:
            break
        if len(name) > 100:
            print("Milestone name must be 100 characters or fewer.")
            continue
        milestones.append({"name": name, "done": False})

    reflection = clean_text("Initial reflection (optional): ",
                            allow_blank=True, max_length=1000)

    goal = {
        "id": next_goal_id(goals),
        "title": title,
        "category": category,
        "description": description,
        "deadline": deadline,
        "progress": 0,
        "milestones": milestones,
        "reflection": reflection,
        "created": date.today().isoformat(),
        "updated": date.today().isoformat()
    }
    goals.append(goal)
    if save_goals(goals):
        print("\nGoal added and saved successfully. Goal ID:", goal["id"])


def display_goal(goal):
    done, total = milestone_counts(goal)
    print(f'ID: {goal["id"]} | {goal["title"]}')
    print(f'Category: {goal["category"]} | Progress: {goal["progress"]}%')
    print(f'Status: {goal_status(goal)} | Deadline: {goal["deadline"] or "Not set"}')
    print(f'Milestones: {done}/{total} completed')
    if goal["description"]:
        print("Description:", goal["description"])
    if goal["milestones"]:
        for item in goal["milestones"]:
            mark = "✓" if item["done"] else " "
            print(f'  [{mark}] {item["name"]}')
    if goal["reflection"]:
        print("Reflection:", goal["reflection"])
    line()


def list_goals(goals):
    heading("YOUR GOALS")
    if not goals:
        print("No goals saved yet. Choose option 1 to add your first goal.")
        return
    for goal in goals:
        display_goal(goal)


def find_goal(goals):
    if not goals:
        print("There are no goals to update.")
        return None
    goal_id = read_positive_id("Enter goal ID: ")
    for goal in goals:
        if goal["id"] == goal_id:
            return goal
    print("No goal found with that ID.")
    return None


def read_positive_id(prompt):
    while True:
        try:
            value = int(input(prompt).strip())
            if value > 0:
                return value
            print("ID must be greater than zero.")
        except ValueError:
            print("Enter a valid numeric ID.")


def update_goal(goals):
    heading("UPDATE GOAL")
    goal = find_goal(goals)
    if goal is None:
        return

    while True:
        print("\n1. Update completion percentage")
        print("2. Mark a milestone complete/incomplete")
        print("3. Add a reflection note")
        print("4. Change deadline")
        print("5. Back")
        choice = read_choice("Select: ", range(1, 6))

        if choice == "1":
            goal["progress"] = read_percentage("New completion percentage",
                                               goal["progress"])
        elif choice == "2":
            if not goal["milestones"]:
                print("This goal has no milestones.")
                continue
            for index, item in enumerate(goal["milestones"], start=1):
                mark = "Done" if item["done"] else "Pending"
                print(f'{index}. {item["name"]} - {mark}')
            number = read_choice("Milestone number: ",
                                 range(1, len(goal["milestones"]) + 1))
            item = goal["milestones"][int(number) - 1]
            item["done"] = not item["done"]
            print("Milestone status changed.")
        elif choice == "3":
            note = clean_text("Reflection note: ", max_length=1000)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            old = goal.get("reflection", "")
            goal["reflection"] = (old + "\n" if old else "") + f"[{stamp}] {note}"
        elif choice == "4":
            goal["deadline"] = read_date("New deadline", allow_blank=True)
        else:
            break

        goal["updated"] = date.today().isoformat()
        save_goals(goals)
        print("Changes saved.")


def search_goals(goals):
    heading("SEARCH AND FILTER")
    if not goals:
        print("No saved goals to search.")
        return
    keyword = input("Keyword (leave blank to skip): ").strip().lower()
    category = input("Category (leave blank for all): ").strip().lower()
    status = input("Status (Completed/In Progress/Overdue/Not Started, blank for all): ").strip().lower()

    matches = []
    for goal in goals:
        searchable = " ".join([
            goal["title"], goal["category"], goal["description"],
            goal["reflection"],
            " ".join(item["name"] for item in goal["milestones"])
        ]).lower()
        if keyword and keyword not in searchable:
            continue
        if category and category not in goal["category"].lower():
            continue
        if status and status != goal_status(goal).lower():
            continue
        matches.append(goal)

    print(f"\nFound {len(matches)} matching goal(s).")
    for goal in matches:
        display_goal(goal)


# ---------- Analytics and reports ----------

def show_summary(goals):
    heading("EXECUTIVE SUMMARY")
    total = len(goals)
    completed = sum(1 for goal in goals if goal_status(goal) == "Completed")
    overdue = sum(1 for goal in goals if goal_status(goal) == "Overdue")
    active = sum(1 for goal in goals if goal_status(goal) == "In Progress")
    not_started = sum(1 for goal in goals if goal_status(goal) == "Not Started")
    average = sum(goal["progress"] for goal in goals) / total if total else 0
    milestone_total = sum(len(goal["milestones"]) for goal in goals)
    milestone_done = sum(milestone_counts(goal)[0] for goal in goals)

    print(f"Total goals              : {total}")
    print(f"Completed                : {completed}")
    print(f"In progress              : {active}")
    print(f"Not started              : {not_started}")
    print(f"Overdue                  : {overdue}")
    print(f"Average completion       : {average:.1f}%")
    print(f"Milestones completed     : {milestone_done}/{milestone_total}")
    line()

    if goals:
        print("CATEGORY BREAKDOWN")
        categories = {}
        for goal in goals:
            categories.setdefault(goal["category"], []).append(goal)
        for name, items in sorted(categories.items()):
            avg = sum(item["progress"] for item in items) / len(items)
            print(f"{name:<24} {len(items):>3} goal(s)   average progress: {avg:5.1f}%")

        print("\nPROGRESS INSIGHT")
        best = max(goals, key=lambda item: item["progress"])
        lowest = min(goals, key=lambda item: item["progress"])
        print(f"Highest progress: {best['title']} ({best['progress']}%)")
        print(f"Needs attention : {lowest['title']} ({lowest['progress']}%)")
        if overdue:
            print("Warning: You have overdue goals. Review their deadlines.")
    else:
        print("Add goals to see your performance metrics.")


def export_csv(goals):
    ensure_folders()
    path = os.path.join(REPORT_DIR, "goal_report.csv")
    fields = ["id", "title", "category", "description", "deadline",
              "progress", "status", "milestones_completed",
              "milestones_total", "reflection", "created", "updated"]
    try:
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for goal in goals:
                done, total = milestone_counts(goal)
                row = {key: goal.get(key, "") for key in fields}
                row["status"] = goal_status(goal)
                row["milestones_completed"] = done
                row["milestones_total"] = total
                writer.writerow(row)
        print("CSV report exported to:", path)
    except OSError as error:
        print("Could not export CSV:", error)


def export_markdown(goals):
    ensure_folders()
    path = os.path.join(REPORT_DIR, "goal_summary.md")
    total = len(goals)
    average = sum(g["progress"] for g in goals) / total if total else 0
    lines = [
        "# Personal Goal Review Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Summary",
        f"- Total goals: {total}",
        f"- Completed goals: {sum(1 for g in goals if goal_status(g) == 'Completed')}",
        f"- Average progress: {average:.1f}%",
        "",
        "## Goal Details",
        "| ID | Goal | Category | Progress | Status | Deadline |",
        "|---:|---|---|---:|---|---|"
    ]
    for goal in goals:
        title = goal["title"].replace("|", "/")
        category = goal["category"].replace("|", "/")
        lines.append(
            f'| {goal["id"]} | {title} | {category} | '
            f'{goal["progress"]}% | {goal_status(goal)} | {goal["deadline"] or "-"} |'
        )
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write("\n".join(lines))
        print("Markdown report exported to:", path)
    except OSError as error:
        print("Could not export report:", error)


def delete_goal(goals):
    heading("DELETE GOAL")
    goal = find_goal(goals)
    if goal is None:
        return
    confirm = read_choice(f'Delete "{goal["title"]}"? (y/n): ', ["y", "n"])
    if confirm == "y":
        goals.remove(goal)
        save_goals(goals)
        print("Goal deleted.")
    else:
        print("Deletion cancelled.")


# ---------- Application menu ----------

def main():
    goals = load_goals()
    while True:
        print_banner()
        print("\nMAIN MENU")
        print("1. Add a new goal")
        print("2. View all goals")
        print("3. Update goal / milestones / reflection")
        print("4. Search and filter goals")
        print("5. Executive summary and analytics")
        print("6. Export CSV report")
        print("7. Export Markdown report")
        print("8. Delete a goal")
        print("9. Save and exit")
        choice = read_choice("\nEnter your choice (1-9): ", range(1, 10))

        if choice == "1":
            add_goal(goals)
            pause()
        elif choice == "2":
            list_goals(goals)
            pause()
        elif choice == "3":
            update_goal(goals)
            pause()
        elif choice == "4":
            search_goals(goals)
            pause()
        elif choice == "5":
            show_summary(goals)
            pause()
        elif choice == "6":
            export_csv(goals)
            pause()
        elif choice == "7":
            export_markdown(goals)
            pause()
        elif choice == "8":
            delete_goal(goals)
            pause()
        elif choice == "9":
            save_goals(goals)
            print("\nYour goals are saved. Thank you for using Personal Goal Review!")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted. Your last saved data remains safe.")
