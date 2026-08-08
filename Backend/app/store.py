
from threading import Lock


class Store:


    def __init__(self):
        self.lock = Lock()
        self.clear()

    def clear(self):

        self.users = {}            # user_id -> user dict
        self.sessions = {}         # token   -> user_id
        self.services = {}         # service_id -> service dict
        self.queues = {}           # service_id -> list of queue entries
        self.notifications = []    # list of notification dicts
        self.history = []          # list of history dicts

        self._user_id = 0
        self._service_id = 0
        self._entry_id = 0
        self._notification_id = 0
        self._history_id = 0
        self._sequence = 0         # global arrival counter for FIFO ordering

    def reset(self):
      
        self.clear()
        self.seed()

    # ------------------------------------------------------------------
    # ID generators
    # ------------------------------------------------------------------

    def next_user_id(self):
        self._user_id += 1
        return self._user_id

    def next_service_id(self):
        self._service_id += 1
        return self._service_id

    def next_entry_id(self):
        self._entry_id += 1
        return self._entry_id

    def next_notification_id(self):
        self._notification_id += 1
        return self._notification_id

    def next_history_id(self):
        self._history_id += 1
        return self._history_id

    def next_sequence(self):
        """Monotonic counter used as the arrival-order tiebreaker."""
        self._sequence += 1
        return self._sequence

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def find_user_by_email(self, email):
        email = (email or "").strip().lower()
        for user in self.users.values():
            if user["email"] == email:
                return user
        return None

    def get_queue(self, service_id):
        return self.queues.setdefault(service_id, [])

    def seed(self):
       
        from app.modules import auth_module, service_module

        auth_module.register_user({
            "first_name": "Demo",
            "last_name": "User",
            "email": "user@queuesmart.com",
            "password": "password123",
            "confirm_password": "password123",
        })

        auth_module.register_user({
            "first_name": "Demo",
            "last_name": "Admin",
            "email": "admin@queuesmart.com",
            "password": "password123",
            "confirm_password": "password123",
            "role": "admin",
            "admin_key": "QUEUE-ADMIN-2026",
        })

        service_module.create_service({
            "name": "Service 1",
            "description": "General assistance and inquiries.",
            "expected_duration": 15,
            "priority": "medium",
        })
        service_module.create_service({
            "name": "Service 2",
            "description": "Document processing and verification.",
            "expected_duration": 10,
            "priority": "low",
        })
        service_module.create_service({
            "name": "Service 3",
            "description": "Specialist consultation.",
            "expected_duration": 30,
            "priority": "high",
        })


# Single shared instance imported by every module. It starts empty; demo data
# is loaded by store.reset(), which the app factory calls at start-up and the
# test suite calls before each test. Seeding here at import time would create a
# circular import, because seed() needs the modules that import this object.
store = Store()
