/* =========================================================
   QueueSmart - page logic
   All data comes from the backend API (see api.js).
   Nothing is stored in localStorage except the session token.
   ========================================================= */

const formBox = document.getElementById("formBox");
const tabs = document.querySelectorAll(".tab");

/* ---------- shared helpers ---------- */

function setActiveTab(index) {
    tabs.forEach(tab => tab.classList.remove("active"));

    if (tabs[index]) {
        tabs[index].classList.add("active");
    }
}

function validEmail(email) {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(email);
}

function showMessage(text, type = "error") {
    const message = document.getElementById("formMessage");

    if (!message) return;

    message.textContent = text;
    message.className = type === "success" ? "message success" : "message error";
}

function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function setText(id, text) {
    const element = document.getElementById(id);
    if (element) element.textContent = text;
}

function currentPage() {
    return document.body.dataset.page || "";
}

/* =========================================================
   AUTHENTICATION PAGES
   ========================================================= */

function showLogin() {
    setActiveTab(0);

    formBox.innerHTML = `
        <label>EMAIL:</label>
        <input type="email" id="email" value="user@queuesmart.com">

        <label>PASSWORD:</label>
        <input type="password" id="password">

        <a href="forgotPassword.html" class="forgot">Forgot Password?</a>

        <p id="formMessage" class="message"></p>

        <button class="login-button" onclick="login()">LOGIN</button>
    `;
}

function showRegister() {
    setActiveTab(1);

    formBox.innerHTML = `
        <label>First Name:</label>
        <input type="text" id="firstName">

        <label>Last Name:</label>
        <input type="text" id="lastName">

        <label>Email:</label>
        <input type="email" id="email">

        <label>Password:</label>
        <input type="password" id="password">

        <label>Confirm Password:</label>
        <input type="password" id="confirmPassword">

        <p id="formMessage" class="message"></p>

        <button class="login-button" onclick="register()">REGISTER</button>
    `;
}

function showAdminLogin() {
    setActiveTab(0);

    formBox.innerHTML = `
        <label>EMAIL:</label>
        <input type="email" id="email" value="admin@queuesmart.com">

        <label>PASSWORD:</label>
        <input type="password" id="password">

        <label>ADMIN KEY:</label>
        <input type="text" id="adminKey">

        <a href="forgotPassword.html" class="forgot">Forgot Password?</a>

        <p id="formMessage" class="message"></p>

        <button class="login-button" onclick="adminLogin()">LOGIN</button>
    `;
}

function showAdminRegister() {
    setActiveTab(1);

    formBox.innerHTML = `
        <label>First Name:</label>
        <input type="text" id="firstName">

        <label>Last Name:</label>
        <input type="text" id="lastName">

        <label>Email:</label>
        <input type="email" id="email">

        <label>Password:</label>
        <input type="password" id="password">

        <label>Confirm Password:</label>
        <input type="password" id="confirmPassword">

        <label>Admin Key:</label>
        <input type="text" id="adminKey">

        <p id="formMessage" class="message"></p>

        <button class="login-button" onclick="adminRegister()">REGISTER</button>
    `;
}

/*
   The client-side checks below are a convenience only. The backend runs the
   same rules again and is the authority - see app/validators.py.
*/

async function login() {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!validEmail(email)) {
        showMessage("Please enter a valid email address.");
        return;
    }

    if (password.length < 8) {
        showMessage("Password must be at least 8 characters.");
        return;
    }

    showMessage("Signing in...", "success");

    try {
        const result = await QueueSmartAPI.login({ email: email, password: password });

        saveSession(result.user, result.token);
        showMessage("Login successful!", "success");

        setTimeout(function () {
            window.location.href = "dashboard.html";
        }, 700);
    } catch (error) {
        showMessage(error.message);
    }
}

async function register() {
    const payload = {
        first_name: document.getElementById("firstName").value.trim(),
        last_name: document.getElementById("lastName").value.trim(),
        email: document.getElementById("email").value.trim(),
        password: document.getElementById("password").value,
        confirm_password: document.getElementById("confirmPassword").value
    };

    if (payload.password !== payload.confirm_password) {
        showMessage("Passwords do not match.");
        return;
    }

    try {
        const result = await QueueSmartAPI.register(payload);

        saveSession(result.user, result.token);
        showMessage("Registration successful!", "success");

        setTimeout(function () {
            window.location.href = "dashboard.html";
        }, 900);
    } catch (error) {
        showMessage(error.message);
    }
}

async function adminLogin() {
    const payload = {
        email: document.getElementById("email").value.trim(),
        password: document.getElementById("password").value,
        admin_key: document.getElementById("adminKey").value.trim(),
        role: "admin"
    };

    try {
        const result = await QueueSmartAPI.login(payload);

        saveSession(result.user, result.token);
        showMessage("Admin login successful!", "success");

        setTimeout(function () {
            window.location.href = "adminDashboard.html";
        }, 700);
    } catch (error) {
        showMessage(error.message);
    }
}

async function adminRegister() {
    const payload = {
        first_name: document.getElementById("firstName").value.trim(),
        last_name: document.getElementById("lastName").value.trim(),
        email: document.getElementById("email").value.trim(),
        password: document.getElementById("password").value,
        confirm_password: document.getElementById("confirmPassword").value,
        admin_key: document.getElementById("adminKey").value.trim(),
        role: "admin"
    };

    if (payload.password !== payload.confirm_password) {
        showMessage("Passwords do not match.");
        return;
    }

    try {
        const result = await QueueSmartAPI.register(payload);

        saveSession(result.user, result.token);
        showMessage("Admin registration successful!", "success");

        setTimeout(function () {
            window.location.href = "adminDashboard.html";
        }, 900);
    } catch (error) {
        showMessage(error.message);
    }
}

function sendReset() {
    const email = document.getElementById("resetEmail").value.trim();
    const message = document.getElementById("message");

    if (!validEmail(email)) {
        message.textContent = "Please enter a valid email address.";
        message.className = "message error";
        return;
    }

    message.textContent = "A password reset link has been sent to " + email + ".";
    message.className = "message success";
}

/* =========================================================
   USER DASHBOARD
   ========================================================= */

async function renderDashboard() {
    const user = requireLogin();
    if (!user) return;

    setText("headerName", user.first_name);

    try {
        const status = await QueueSmartAPI.myQueueStatus();
        const statusBox = document.getElementById("currentQueueStatus");

        if (!status.in_queue) {
            statusBox.innerHTML = "<p>You are currently not in a queue.</p>";
        } else {
            statusBox.innerHTML = status.queues.map(function (q) {
                return `
                    <p>
                        <strong>${escapeHtml(q.service_name)}</strong> &mdash;
                        position <strong>${q.position}</strong>,
                        ${escapeHtml(q.wait_label.toLowerCase())}
                    </p>
                `;
            }).join("");
        }
    } catch (error) {
        document.getElementById("currentQueueStatus").innerHTML =
            "<p class='error'>" + escapeHtml(error.message) + "</p>";
    }

    try {
        const data = await QueueSmartAPI.listServices(true);
        const list = document.getElementById("activeServiceList");

        list.innerHTML = data.services.length === 0
            ? "<li>No services are open right now.</li>"
            : data.services.map(function (s) {
                return `<li>${escapeHtml(s.name)} (${s.queue_length} waiting)</li>`;
            }).join("");
    } catch (error) {
        document.getElementById("activeServiceList").innerHTML =
            "<li>" + escapeHtml(error.message) + "</li>";
    }

    renderDashboardNotifications();
}

async function renderDashboardNotifications() {
    const element = document.getElementById("notificationList");

    if (!element) return;

    try {
        const data = await QueueSmartAPI.notifications();

        if (data.notifications.length === 0) {
            element.innerHTML = "<p>No new notifications</p>";
            return;
        }

        element.innerHTML = "<ul>" + data.notifications.map(function (n) {
            return "<li>" + escapeHtml(n.message) + "</li>";
        }).join("") + "</ul>";
    } catch (error) {
        element.innerHTML = "<p>" + escapeHtml(error.message) + "</p>";
    }
}

/* =========================================================
   JOIN QUEUE
   ========================================================= */

async function renderJoinQueue() {
    if (!requireLogin()) return;

    const container = document.getElementById("serviceCards");

    try {
        const data = await QueueSmartAPI.listServices(true);

        if (data.services.length === 0) {
            container.innerHTML = "<p class='empty-message'>No services are open right now.</p>";
            return;
        }

        // Ask the backend for a wait estimate for each open service.
        const estimates = await Promise.all(
            data.services.map(function (s) { return QueueSmartAPI.waitTime(s.id); })
        );

        container.innerHTML = data.services.map(function (s, index) {
            const estimate = estimates[index];

            return `
                <div class="service-card">
                    <h3>${escapeHtml(s.name)}</h3>
                    <p>${escapeHtml(s.description)}</p>
                    <p>
                        ${estimate.queue_length} in line &nbsp;|&nbsp;
                        Priority: ${escapeHtml(s.priority)} &nbsp;|&nbsp;
                        Estimated wait: <strong>${estimate.estimated_wait_minutes} min</strong>
                    </p>
                    <button class="join-button" onclick="joinQueue(${s.id})">JOIN QUEUE</button>
                </div>
            `;
        }).join("");
    } catch (error) {
        container.innerHTML = "<p class='empty-message'>" + escapeHtml(error.message) + "</p>";
    }
}

async function joinQueue(serviceId) {
    try {
        const result = await QueueSmartAPI.joinQueue(serviceId);

        alert(
            "You joined " + result.entry.service_name +
            ". You are number " + result.entry.position +
            " in line. " + result.entry.wait_label + "."
        );

        window.location.href = "queueStatus.html?serviceId=" + serviceId;
    } catch (error) {
        alert(error.message);
    }
}

/* =========================================================
   QUEUE STATUS
   ========================================================= */

async function loadQueueStatus() {
    if (!requireLogin()) return;

    const card = document.getElementById("statusCard");

    try {
        const status = await QueueSmartAPI.myQueueStatus();

        if (!status.in_queue) {
            card.innerHTML = `
                <h3>You are not in a queue</h3>
                <p>Join a service to see your live position here.</p>
            `;
            return;
        }

        const params = new URLSearchParams(window.location.search);
        const requested = Number(params.get("serviceId"));
        const entry = status.queues.find(function (q) {
            return q.service_id === requested;
        }) || status.queues[0];

        card.innerHTML = `
            <h3 id="statusService">Service: ${escapeHtml(entry.service_name)}</h3>
            <p>Your position in line</p>
            <div class="big-number" id="queuePosition">${entry.position}</div>
            <p>Estimated wait</p>
            <div class="big-number" id="statusWait">${entry.estimated_wait_minutes} min</div>
            <p>${escapeHtml(entry.wait_label)}</p>
            <span class="status-badge" id="queueStatus">
                ${entry.position === 1 ? "You are next" : "Waiting"}
            </span>
            <button class="join-button" style="margin-top:30px"
                    onclick="leaveQueueStatus(${entry.service_id})">
                LEAVE QUEUE
            </button>
        `;
    } catch (error) {
        card.innerHTML = "<p>" + escapeHtml(error.message) + "</p>";
    }
}

async function leaveQueueStatus(serviceId) {
    if (!confirm("Are you sure you want to leave this queue?")) return;

    try {
        const result = await QueueSmartAPI.leaveQueue(serviceId);

        alert(result.message);
        window.location.href = "dashboard.html";
    } catch (error) {
        alert(error.message);
    }
}

/* =========================================================
   QUEUE HISTORY
   ========================================================= */

async function renderHistory() {
    if (!requireLogin()) return;

    const body = document.getElementById("historyTableBody");

    try {
        const data = await QueueSmartAPI.history();

        setText(
            "historySummary",
            data.summary.total_visits + " visits | " +
            data.summary.served + " served | " +
            "average wait " + data.summary.average_wait_minutes + " min"
        );

        if (data.history.length === 0) {
            body.innerHTML = "<tr><td colspan='4' class='empty-message'>No queue history yet.</td></tr>";
            return;
        }

        body.innerHTML = data.history.map(function (record) {
            const joined = new Date(record.joined_at).toLocaleString();
            const wait = record.actual_wait_minutes === null
                ? "-"
                : record.actual_wait_minutes + " min";

            return `
                <tr>
                    <td>${escapeHtml(record.service_name)}</td>
                    <td>${escapeHtml(joined)}</td>
                    <td>${escapeHtml(wait)}</td>
                    <td>${escapeHtml(record.status)}</td>
                </tr>
            `;
        }).join("");
    } catch (error) {
        body.innerHTML = "<tr><td colspan='4' class='empty-message'>" +
            escapeHtml(error.message) + "</td></tr>";
    }
}

/* =========================================================
   ADMIN DASHBOARD
   ========================================================= */

async function renderAdminDashboard() {
    if (!requireLogin("admin")) return;

    const container = document.getElementById("adminServiceList");

    try {
        const data = await QueueSmartAPI.listServices();

        if (data.services.length === 0) {
            container.innerHTML = "<p class='empty-message'>No services yet. Add one to get started.</p>";
            return;
        }

        container.innerHTML = data.services.map(function (s) {
            return `
                <div class="admin-service-row">
                    <div class="admin-service-info">
                        <h3>${escapeHtml(s.name)}</h3>
                        <p>
                            Queue length: <strong>${s.queue_length}</strong> &nbsp;|&nbsp;
                            Priority: <strong>${escapeHtml(s.priority)}</strong> &nbsp;|&nbsp;
                            Duration: <strong>${s.expected_duration} min</strong>
                        </p>
                        <span class="status-pill ${s.is_open ? "pill-open" : "pill-closed"}">
                            ${s.is_open ? "OPEN" : "CLOSED"}
                        </span>
                    </div>
                    <div class="admin-service-actions">
                        <button class="small-button" onclick="toggleQueueOpen(${s.id}, ${!s.is_open})">
                            ${s.is_open ? "Close Queue" : "Open Queue"}
                        </button>
                        <button class="small-button" onclick="window.location.href='queueManagement.html?serviceId=${s.id}'">Manage Queue</button>
                        <button class="small-button" onclick="window.location.href='serviceManagement.html?editId=${s.id}'">Edit</button>
                    </div>
                </div>
            `;
        }).join("");
    } catch (error) {
        container.innerHTML = "<p class='empty-message'>" + escapeHtml(error.message) + "</p>";
    }
}

async function toggleQueueOpen(serviceId, isOpen) {
    try {
        await QueueSmartAPI.setServiceStatus(serviceId, isOpen);
        renderAdminDashboard();
    } catch (error) {
        alert(error.message);
    }
}

/* =========================================================
   SERVICE MANAGEMENT
   ========================================================= */

async function loadServiceFormFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const editId = params.get("editId");

    if (!editId) return;

    try {
        const data = await QueueSmartAPI.getService(editId);
        const service = data.service;

        document.getElementById("serviceId").value = service.id;
        document.getElementById("serviceName").value = service.name;
        document.getElementById("serviceDescription").value = service.description;
        document.getElementById("serviceDuration").value = service.expected_duration;
        document.getElementById("servicePriority").value = service.priority;
        setText("formTitle", "Edit Service");
    } catch (error) {
        showMessage(error.message);
    }
}

async function renderServiceTable() {
    const body = document.getElementById("serviceTableBody");

    if (!body) return;

    try {
        const data = await QueueSmartAPI.listServices();

        if (data.services.length === 0) {
            body.innerHTML = "<tr><td colspan='5' class='empty-message'>No services created yet.</td></tr>";
            return;
        }

        body.innerHTML = data.services.map(function (s) {
            return `
                <tr>
                    <td>${escapeHtml(s.name)}</td>
                    <td>${s.expected_duration} min</td>
                    <td>${escapeHtml(s.priority)}</td>
                    <td>${s.is_open ? "Open" : "Closed"}</td>
                    <td>
                        <button class="small-button" onclick="window.location.href='serviceManagement.html?editId=${s.id}'">Edit</button>
                        <button class="small-button danger-button" onclick="deleteService(${s.id})">Delete</button>
                    </td>
                </tr>
            `;
        }).join("");
    } catch (error) {
        body.innerHTML = "<tr><td colspan='5' class='empty-message'>" +
            escapeHtml(error.message) + "</td></tr>";
    }
}

async function saveService() {
    const idField = document.getElementById("serviceId").value;

    const payload = {
        name: document.getElementById("serviceName").value.trim(),
        description: document.getElementById("serviceDescription").value.trim(),
        expected_duration: document.getElementById("serviceDuration").value,
        priority: document.getElementById("servicePriority").value
    };

    try {
        if (idField) {
            await QueueSmartAPI.updateService(idField, payload);
        } else {
            await QueueSmartAPI.createService(payload);
        }

        showMessage("Service saved successfully.", "success");

        setTimeout(function () {
            window.location.href = "adminDashboard.html";
        }, 800);
    } catch (error) {
        // The backend tells us which field failed, so highlight it for the user.
        showMessage(error.message);
    }
}

async function deleteService(serviceId) {
    if (!confirm("Delete this service and its queue?")) return;

    try {
        await QueueSmartAPI.deleteService(serviceId);
        renderServiceTable();
    } catch (error) {
        alert(error.message);
    }
}

/* =========================================================
   QUEUE MANAGEMENT (ADMIN)
   ========================================================= */

let activeServiceId = null;

async function renderQueueManagement() {
    if (!requireLogin("admin")) return;

    const select = document.getElementById("serviceSelect");

    if (!select) return;

    try {
        const data = await QueueSmartAPI.listServices();

        if (data.services.length === 0) {
            document.getElementById("queueList").innerHTML =
                "<p class='empty-message'>No services exist yet.</p>";
            return;
        }

        const params = new URLSearchParams(window.location.search);
        activeServiceId = Number(params.get("serviceId")) || data.services[0].id;

        select.innerHTML = data.services.map(function (s) {
            return `<option value="${s.id}" ${s.id === activeServiceId ? "selected" : ""}>
                        ${escapeHtml(s.name)}
                    </option>`;
        }).join("");

        select.onchange = function () {
            activeServiceId = Number(select.value);
            renderQueueList();
        };

        renderQueueList();
    } catch (error) {
        document.getElementById("queueList").innerHTML =
            "<p class='empty-message'>" + escapeHtml(error.message) + "</p>";
    }
}

async function renderQueueList() {
    const list = document.getElementById("queueList");

    if (!list || activeServiceId === null) return;

    try {
        const data = await QueueSmartAPI.viewQueue(activeServiceId);

        setText(
            "queueSummary",
            data.queue_length + " waiting | about " +
            data.estimated_drain_minutes + " min to clear the queue"
        );

        if (data.entries.length === 0) {
            list.innerHTML = "<p class='empty-message'>No one is currently in this queue.</p>";
            return;
        }

        list.innerHTML = data.entries.map(function (entry, index) {
            return `
                <div class="queue-row">
                    <span class="queue-position-label">${entry.position}.</span>
                    <span class="queue-name">
                        ${escapeHtml(entry.user_name)}
                        <span class="status-pill pill-open">${escapeHtml(entry.priority)}</span>
                        <small>${entry.estimated_wait_minutes} min</small>
                    </span>
                    <div class="queue-row-actions">
                        <button class="small-button" onclick="moveInQueue(${entry.entry_id}, 'up')"
                            ${index === 0 ? "disabled" : ""}>Up</button>
                        <button class="small-button" onclick="moveInQueue(${entry.entry_id}, 'down')"
                            ${index === data.entries.length - 1 ? "disabled" : ""}>Down</button>
                        <button class="small-button danger-button" onclick="removeFromQueue(${entry.entry_id})">Remove</button>
                    </div>
                </div>
            `;
        }).join("");
    } catch (error) {
        list.innerHTML = "<p class='empty-message'>" + escapeHtml(error.message) + "</p>";
    }
}

async function moveInQueue(entryId, direction) {
    try {
        await QueueSmartAPI.moveInQueue(activeServiceId, entryId, direction);
        renderQueueList();
    } catch (error) {
        alert(error.message);
    }
}

async function removeFromQueue(entryId) {
    try {
        const result = await QueueSmartAPI.removeFromQueue(activeServiceId, entryId);

        alert(result.message);
        renderQueueList();
    } catch (error) {
        alert(error.message);
    }
}

async function serveNext() {
    try {
        const result = await QueueSmartAPI.serveNext(activeServiceId);

        alert(
            result.served.user_name + " has been served. " +
            result.remaining + " still waiting."
        );

        renderQueueList();
    } catch (error) {
        alert(error.message);
    }
}

/* =========================================================
   PAGE ROUTER
   ========================================================= */

const routes = {
    login: function () {
        if (formBox) showLogin();
    },
    adminLogin: function () {
        if (formBox) showAdminLogin();
    },
    dashboard: renderDashboard,
    joinQueue: renderJoinQueue,
    queueStatus: loadQueueStatus,
    history: renderHistory,
    adminDashboard: renderAdminDashboard,
    serviceManagement: function () {
        if (!requireLogin("admin")) return;
        renderServiceTable();
        loadServiceFormFromQuery();
    },
    queueManagement: renderQueueManagement
};

const route = routes[currentPage()];

if (route) {
    route();
}
