/* =========================================================
   QueueSmart - API client
   Every page loads this file before script.js. It is the only
   place in the front end that knows about HTTP.
   ========================================================= */

const API_BASE =
    window.location.protocol === "file:"
        ? "http://127.0.0.1:5000/api"
        : "/api";

const TOKEN_KEY = "qs_token";
const USER_KEY = "qs_user";

/* ---------- session helpers ---------- */

function saveSession(user, token) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

function authToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function currentUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
}

/* ---------- core request wrapper ---------- */

async function apiRequest(path, method = "GET", body = null) {
    const options = {
        method: method,
        headers: { "Content-Type": "application/json" }
    };

    const token = authToken();

    if (token) {
        options.headers["Authorization"] = "Bearer " + token;
    }

    if (body !== null) {
        options.body = JSON.stringify(body);
    }

    let response;

    try {
        response = await fetch(API_BASE + path, options);
    } catch (networkError) {
        throw new Error("Cannot reach the QueueSmart server. Is the backend running?");
    }

    let data = {};

    try {
        data = await response.json();
    } catch (parseError) {
        data = {};
    }

    if (!response.ok) {
        const error = new Error(data.message || "Something went wrong.");
        error.status = response.status;
        error.field = data.field || null;

        // The token expired or the server restarted - send the user back to login.
        if (response.status === 401 && token) {
            clearSession();
        }

        throw error;
    }

    return data;
}

const api = {
    get: (path) => apiRequest(path, "GET"),
    post: (path, body) => apiRequest(path, "POST", body),
    put: (path, body) => apiRequest(path, "PUT", body),
    patch: (path, body) => apiRequest(path, "PATCH", body),
    del: (path) => apiRequest(path, "DELETE")
};

/* ---------- endpoint shortcuts ---------- */

const QueueSmartAPI = {
    register: (payload) => api.post("/auth/register", payload),
    login: (payload) => api.post("/auth/login", payload),
    logout: () => api.post("/auth/logout", {}),
    me: () => api.get("/auth/me"),

    listServices: (onlyOpen) => api.get("/services" + (onlyOpen ? "?open=true" : "")),
    getService: (id) => api.get("/services/" + id),
    createService: (payload) => api.post("/services", payload),
    updateService: (id, payload) => api.put("/services/" + id, payload),
    setServiceStatus: (id, isOpen) => api.patch("/services/" + id + "/status", { is_open: isOpen }),
    deleteService: (id) => api.del("/services/" + id),

    waitTime: (id) => api.get("/services/" + id + "/wait-time"),

    joinQueue: (id, priority) => api.post("/services/" + id + "/queue/join", priority ? { priority: priority } : {}),
    leaveQueue: (id) => api.del("/services/" + id + "/queue/leave"),
    myQueueStatus: () => api.get("/queue/status"),

    viewQueue: (id) => api.get("/services/" + id + "/queue"),
    serveNext: (id) => api.post("/services/" + id + "/queue/serve-next", {}),
    removeFromQueue: (serviceId, entryId) => api.del("/services/" + serviceId + "/queue/" + entryId),
    moveInQueue: (serviceId, entryId, direction) =>
        api.patch("/services/" + serviceId + "/queue/" + entryId + "/move", { direction: direction }),

    notifications: () => api.get("/notifications"),
    markNotificationsRead: () => api.post("/notifications/read", {}),

    history: () => api.get("/history")
};

/* ---------- page guards ---------- */

function requireLogin(role) {
    const user = currentUser();

    if (!user || !authToken()) {
        window.location.href = role === "admin" ? "adminLogin.html" : "index.html";
        return null;
    }

    if (role && user.role !== role) {
        window.location.href = user.role === "admin" ? "adminDashboard.html" : "dashboard.html";
        return null;
    }

    return user;
}

async function doLogout() {
    try {
        await QueueSmartAPI.logout();
    } catch (error) {
        /* the token may already be gone - log out locally either way */
    }

    clearSession();
    window.location.href = "index.html";
}
