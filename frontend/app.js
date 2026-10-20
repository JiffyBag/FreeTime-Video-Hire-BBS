const API = "http://localhost:8000/api/v1";
let token = localStorage.getItem("ft_token");
let userId = localStorage.getItem("ft_uid");
let username = localStorage.getItem("ft_uname");
let isAdmin = localStorage.getItem("ft_admin") === "true";

function show(id) { const el = document.getElementById(id); if (el) el.classList.remove("hidden"); }
function hide(id) { const el = document.getElementById(id); if (el) el.classList.add("hidden"); }

function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}

async function authFetch(url, opts = {}) {
  opts.headers = Object.assign({}, opts.headers, { Authorization: `Bearer ${token}` });
  return fetch(url, opts);
}

// ---------------- index.html ----------------

async function doLogin() {
  const u = document.getElementById("username").value;
  const p = document.getElementById("password").value;
  try {
    const res = await fetch(`${API}/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p }),
    });
    if (!res.ok) throw new Error("bad creds");
    const data = await res.json();
    token = data.access_token; userId = data.user_id; username = u; isAdmin = data.is_admin;
    localStorage.setItem("ft_token", token);
    localStorage.setItem("ft_uid", userId);
    localStorage.setItem("ft_uname", username);
    localStorage.setItem("ft_admin", isAdmin);
    enterBBS();
  } catch (e) {
    document.getElementById("login-msg").textContent = "LOGIN FAILED - check credentials";
  }
}

async function enterBBS() {
  hide("login-screen"); show("main-screen");
  document.getElementById("whoami").textContent = `USER: ${username} (id ${userId})${isAdmin ? " [ADMIN]" : ""}`;
  loadMovies(); loadSnacks(); loadRentals();
}

async function loadMovies() {
  const el = document.getElementById("movies");
  if (!el) return;
  const res = await fetch(`${API}/movies`);
  const movies = await res.json();
  el.innerHTML = movies.map(m => `
    <div class="card"><b>${m.title}</b> (${m.year})<br>${m.genre} - $${m.rental_price.toFixed(2)} - stock: ${m.stock}
    <button onclick="rentMovie(${m.id})">RENT</button></div>`).join("");
}

async function rentMovie(movieId) {
  const res = await authFetch(`${API}/rentals`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ movie_id: movieId, qty: 1 }),
  });
  const data = await res.json();
  document.getElementById("action-msg").textContent = res.ok
    ? `Rented! Total: $${data.total_price}` : `Error: ${data.detail}`;
  loadRentals(); loadMovies();
}

async function loadSnacks() {
  const el = document.getElementById("snacks");
  if (!el) return;
  const res = await fetch(`${API}/snacks`);
  const snacks = await res.json();
  el.innerHTML = snacks.map(s => `
    <div class="card"><b>${s.name}</b><br>$${s.price.toFixed(2)} - stock: ${s.stock}
    <button onclick="orderSnack(${s.id})">ORDER</button></div>`).join("");
}

async function orderSnack(snackId) {
  const res = await authFetch(`${API}/snacks/purchase`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snack_id: snackId, qty: 1 }),
  });
  const data = await res.json();
  document.getElementById("action-msg").textContent = res.ok
    ? `Ordered ${data.snack}! Total: $${data.total_price}` : `Error: ${data.detail}`;
  loadSnacks();
}

async function loadRentals() {
  const el = document.getElementById("rentals");
  if (!el) return;
  const res = await authFetch(`${API}/rentals`);
  const rentals = await res.json();
  el.innerHTML = rentals.length
    ? rentals.map(r => `<div class="card">Movie #${r.movie_id} x${r.qty}</div>`).join("")
    : "<p>No rentals yet.</p>";
}

// ---------------- register.html ----------------

async function doRegister() {
  const u = document.getElementById("reg-username").value;
  const email = document.getElementById("reg-email").value;
  const p = document.getElementById("reg-password").value;
  const c = document.getElementById("reg-confirm").value;
  const msg = document.getElementById("reg-msg");
  if (p !== c) { msg.textContent = "Passwords do not match"; return; }
  try {
    const res = await fetch(`${API}/auth/register`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, email: email, password: p }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "registration failed");
    msg.classList.add("ok");
    msg.textContent = `Welcome, ${data.username}! You can now log in.`;
  } catch (e) {
    msg.classList.remove("ok");
    msg.textContent = e.message;
  }
}

// ---------------- forgot.html ----------------

async function doForgot() {
  const email = document.getElementById("forgot-email").value;
  const msg = document.getElementById("forgot-msg");
  try {
    const res = await fetch(`${API}/auth/forgot-password`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email }),
    });
    const data = await res.json();
    msg.classList.add("ok");
    msg.textContent = data.message;
  } catch (e) {
    msg.classList.remove("ok");
    msg.textContent = "Something went wrong.";
  }
}

// ---------------- reset.html ----------------

async function doReset() {
  const params = new URLSearchParams(window.location.search);
  const resetToken = params.get("token");
  const p = document.getElementById("reset-password").value;
  const c = document.getElementById("reset-confirm").value;
  const msg = document.getElementById("reset-msg");
  if (!resetToken) { msg.textContent = "Missing reset token in URL."; return; }
  if (p !== c) { msg.textContent = "Passwords do not match"; return; }
  try {
    const res = await fetch(`${API}/auth/reset-password`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: resetToken, new_password: p }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "reset failed");
    msg.classList.add("ok");
    msg.textContent = "Password reset! You can now log in.";
  } catch (e) {
    msg.classList.remove("ok");
    msg.textContent = e.message;
  }
}

// ---------------- admin.html ----------------

async function initAdmin() {
  if (!token) { window.location.href = "index.html"; return; }
  if (!isAdmin) { show("admin-denied"); return; }
  show("admin-screen");
  loadAdminUsers(); loadAdminMovies(); loadAdminSnacks();
}

async function loadAdminUsers() {
  const res = await authFetch(`${API}/admin/users`);
  const users = await res.json();
  const tbody = document.querySelector("#users-table tbody");
  tbody.innerHTML = users.map(u => `
    <tr><td>${u.id}</td><td>${u.username}</td><td>${u.email}</td><td>$${u.balance.toFixed(2)}</td>
    <td>${u.is_admin ? "yes" : "no"}</td>
    <td><button onclick="adminDeleteUser(${u.id})">DELETE</button></td></tr>`).join("");
}

async function adminAddUser() {
  const body = {
    username: document.getElementById("nu-username").value,
    email: document.getElementById("nu-email").value,
    password: document.getElementById("nu-password").value,
    balance: parseFloat(document.getElementById("nu-balance").value) || 5,
    is_admin: document.getElementById("nu-admin").checked,
  };
  const res = await authFetch(`${API}/admin/users`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await res.json();
  document.getElementById("admin-msg").textContent = res.ok ? `Added user ${data.username}` : `Error: ${data.detail}`;
  loadAdminUsers();
}

async function adminDeleteUser(id) {
  const res = await authFetch(`${API}/admin/users/${id}`, { method: "DELETE" });
  const data = await res.json();
  document.getElementById("admin-msg").textContent = res.ok ? `Deleted user ${id}` : `Error: ${data.detail}`;
  loadAdminUsers();
}

async function loadAdminMovies() {
  const res = await fetch(`${API}/movies?limit=100`);
  const movies = await res.json();
  const tbody = document.querySelector("#movies-table tbody");
  tbody.innerHTML = movies.map(m => `
    <tr><td>${m.id}</td><td>${m.title}</td><td>${m.stock}</td>
    <td><input type="number" id="restock-${m.id}" value="5" style="width:70px">
    <button onclick="adminRestockMovie(${m.id})">RESTOCK</button></td></tr>`).join("");
}

async function adminAddMovie() {
  const body = {
    title: document.getElementById("nm-title").value,
    year: parseInt(document.getElementById("nm-year").value) || 1985,
    genre: document.getElementById("nm-genre").value,
    rental_price: parseFloat(document.getElementById("nm-price").value) || 2.0,
  };
  const res = await authFetch(`${API}/admin/movies`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await res.json();
  document.getElementById("admin-msg").textContent = res.ok ? `Added movie ${data.title}` : `Error: ${data.detail}`;
  loadAdminMovies();
}

async function adminRestockMovie(id) {
  const qty = parseInt(document.getElementById(`restock-${id}`).value) || 0;
  const res = await authFetch(`${API}/admin/movies/${id}/restock`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ qty }),
  });
  const data = await res.json();
  document.getElementById("admin-msg").textContent = res.ok ? `${data.title} stock now ${data.stock}` : `Error: ${data.detail}`;
  loadAdminMovies();
}

async function loadAdminSnacks() {
  const res = await fetch(`${API}/snacks`);
  const snacks = await res.json();
  const tbody = document.querySelector("#snacks-table tbody");
  tbody.innerHTML = snacks.map(s => `
    <tr><td>${s.id}</td><td>${s.name}</td><td>${s.stock}</td>
    <td><input type="number" id="srestock-${s.id}" value="20" style="width:70px">
    <button onclick="adminRestockSnack(${s.id})">RESTOCK</button></td></tr>`).join("");
}

async function adminRestockSnack(id) {
  const qty = parseInt(document.getElementById(`srestock-${id}`).value) || 0;
  const res = await authFetch(`${API}/admin/snacks/restock`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ snack_id: id, qty }),
  });
  const data = await res.json();
  document.getElementById("admin-msg").textContent = res.ok ? `${data.name} stock now ${data.stock}` : `Error: ${data.detail}`;
  loadAdminSnacks();
}

// ---------------- page bootstrap ----------------

const page = window.location.pathname.split("/").pop();
if (page === "index.html" || page === "") {
  if (token) enterBBS();
} else if (page === "admin.html") {
  initAdmin();
}
