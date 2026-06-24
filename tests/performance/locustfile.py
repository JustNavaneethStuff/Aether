"""Performance test scaffold — run with: locust -f tests/performance/locustfile.py"""

from locust import HttpUser, between, task


class AetherUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        response = self.client.post("/v1/conversations", json={})
        self.conversation_id = response.json()["id"]

    @task
    def send_message(self) -> None:
        self.client.post(
            f"/v1/conversations/{self.conversation_id}/messages",
            json={"content": "What are the benefits of event-driven architecture?"},
            stream=True,
        )
