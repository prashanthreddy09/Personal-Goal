const $ = (id) => document.getElementById(id);
let editingId = null;
let goalsCache = [];

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {"Content-Type": "application/json"},
    ...options
  });
  const data = response.headers.get("content-type")?.includes("application/json")
    ? await response.json() : null;
  if (!response.ok) throw new Error(data?.error || "Something went wrong.");
  return data;
}
function toast(message) {
  $("toast").textContent = message;
  $("toast").classList.add("show");
  setTimeout(() => $("toast").classList.remove("show"), 2400);
}
function safe(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}
async function refresh() {
  try {
    const params = new URLSearchParams({
      q: $("search").value,
      category: $("category-filter").value,
      status: $("status-filter").value
    });
    const [goalData, stats] = await Promise.all([
      request("/api/goals?" + params.toString()), request("/api/summary")
    ]);
    goalsCache = goalData.goals;
    renderGoals(goalsCache);
    renderStats(stats);
    renderAnalytics(stats);
  } catch (error) {
    $("goal-list").innerHTML = `<div class="empty-state">${safe(error.message)}</div>`;
  }
}
function renderStats(s) {
  $("total").textContent = s.total;
  $("completed").textContent = s.completed;
  $("in-progress").textContent = s.in_progress;
  $("average").textContent = s.average + "%";
}
function renderAnalytics(s) {
  if (!s.categories.length) {
    $("analytics").innerHTML = '<p class="muted">Add goals to see your category breakdown.</p>';
    return;
  }
  $("analytics").innerHTML = s.categories.map(c => `
    <div class="category-item"><strong>${safe(c.name)}</strong>
      <p>${c.count} goal(s) · ${c.average}% average progress</p>
      <div class="category-bar"><span style="width:${c.average}%"></span></div>
    </div>`).join("");
}
function renderGoals(goals) {
  if (!goals.length) {
    $("goal-list").innerHTML = '<div class="empty-state">No goals found. Add your first goal to get started.</div>';
    return;
  }
  $("goal-list").innerHTML = goals.map(g => `
    <article class="goal-card">
      <div class="goal-top">
        <div><h3 class="goal-title">${safe(g.title)}</h3>
          <div class="goal-meta">${safe(g.category)} · Deadline: ${safe(g.deadline || "Not set")} · ${g.milestones_completed}/${g.milestones_total} milestones</div>
        </div>
        <span class="status ${g.status.replaceAll(" ","-")}">${safe(g.status)}</span>
      </div>
      <div class="progress-line"><span style="width:${g.progress}%"></span></div>
      <div class="goal-bottom"><span>${g.progress}% complete</span>
        <div class="goal-actions">
          <button class="text-btn" onclick="editGoal(${g.id})">Edit</button>
          <button class="text-btn delete" onclick="deleteGoal(${g.id})">Delete</button>
        </div>
      </div>
      ${g.milestones.length ? `<div class="milestones">${g.milestones.map((m,i)=>`
        <label><input type="checkbox" ${m.done ? "checked" : ""} onchange="toggleMilestone(${g.id},${i},this.checked)">
        <span>${safe(m.name)}</span></label>`).join("")}</div>` : ""}
      ${g.description ? `<p class="reflection">${safe(g.description)}</p>` : ""}
      ${g.reflection ? `<p class="reflection"><b>Reflection:</b> ${safe(g.reflection)}</p>` : ""}
    </article>`).join("");
}
function openModal(goal = null) {
  editingId = goal ? goal.id : null;
  $("goal-form").reset();
  $("form-error").textContent = "";
  $("form-title").textContent = goal ? "Edit goal" : "Add a new goal";
  $("progress-label").style.display = goal ? "flex" : "none";
  if (goal) {
    const f = $("goal-form");
    f.elements.title.value = goal.title;
    f.elements.category.value = goal.category;
    f.elements.deadline.value = goal.deadline || "";
    f.elements.description.value = goal.description || "";
    f.elements.milestones.value = goal.milestones.map(m => m.name).join("\n");
    f.elements.reflection.value = goal.reflection || "";
    f.elements.progress.value = goal.progress;
    $("progress-value").textContent = goal.progress + "%";
  } else {
    $("goal-form").elements.progress.value = 0;
  }
  $("modal").classList.add("show");
}
function closeModal() { $("modal").classList.remove("show"); }
async function editGoal(id) {
  const goal = goalsCache.find(g => g.id === id);
  if (goal) openModal(goal);
}
async function deleteGoal(id) {
  if (!confirm("Delete this goal? This cannot be undone.")) return;
  try { await request("/api/goals/" + id, {method:"DELETE"}); toast("Goal deleted."); refresh(); }
  catch (e) { toast(e.message); }
}
async function toggleMilestone(id, index, done) {
  const goal = goalsCache.find(g => g.id === id);
  if (!goal) return;
  const milestones = goal.milestones.map((m,i) => ({...m, done: i === index ? done : m.done}));
  try {
    await request("/api/goals/" + id, {method:"PUT", body:JSON.stringify({
      ...goal, milestones:milestones
    })});
    refresh();
  } catch (e) { toast(e.message); }
}
$("open-add").addEventListener("click", () => openModal());
$("close-modal").addEventListener("click", closeModal);
$("cancel-form").addEventListener("click", closeModal);
$("modal").addEventListener("click", e => { if (e.target === $("modal")) closeModal(); });
$("goal-form").elements.progress.addEventListener("input", e => $("progress-value").textContent = e.target.value + "%");
$("goal-form").addEventListener("submit", async e => {
  e.preventDefault();
  const f = e.currentTarget;
  const data = {
    title:f.elements.title.value.trim(), category:f.elements.category.value.trim(),
    deadline:f.elements.deadline.value, description:f.elements.description.value.trim(),
    milestones:f.elements.milestones.value.split("\n").map(s=>s.trim()).filter(Boolean),
    reflection:f.elements.reflection.value.trim(), progress:Number(f.elements.progress.value)
  };
  try {
    await request(editingId ? "/api/goals/" + editingId : "/api/goals", {
      method:editingId ? "PUT" : "POST", body:JSON.stringify(data)
    });
    closeModal(); toast(editingId ? "Goal updated." : "Goal added."); refresh();
  } catch (error) { $("form-error").textContent = error.message; }
});
["search","category-filter","status-filter"].forEach(id => $(id).addEventListener("input", refresh));
refresh();
