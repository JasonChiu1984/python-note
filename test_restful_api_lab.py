from concurrent.futures import ThreadPoolExecutor
import unittest

from fastapi.testclient import TestClient

from python_restful_api_lab import create_app


class Contract(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.root = "/v1/devices"
        self.body = {"id": "ahu-01", "name": "AHU primary", "enabled": True}
        self.path = self.root + "/ahu-01"

    def make(self):
        r = self.client.post(self.root, json=self.body)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers["location"], self.path)
        self.assertEqual(r.json()["revision"], 1)

    def assert_problem(self, response, code):
        self.assertEqual(response.status_code, code)
        self.assertEqual(response.headers["content-type"], "application/problem+json")
        self.assertEqual(response.json()["status"], code)
        self.assertEqual(response.json()["type"], "about:blank")

    def test_create_read_and_duplicate(self):
        self.assert_problem(self.client.get(self.path), 404)
        self.make()
        self.assertEqual(self.client.get(self.path).headers["etag"], '"1"')
        self.assert_problem(self.client.post(self.root, json=self.body), 409)
        self.assertEqual(self.client.get(self.path).json()["name"], self.body["name"])

    def test_pagination(self):
        for key in ("ahu-03", "ahu-01", "ahu-02"):
            self.assertEqual(self.client.post(self.root, json={**self.body, "id": key}).status_code, 201)
        first = self.client.get(self.root, params={"limit": 2}).json()
        self.assertEqual([x["id"] for x in first["items"]], ["ahu-01", "ahu-02"])
        final = self.client.get(self.root, params={"limit": 2, "after": first["next_after"]}).json()
        self.assertEqual([x["id"] for x in final["items"]], ["ahu-03"])
        self.assertIsNone(final["next_after"])
        self.assert_problem(self.client.get(self.root, params={"limit": 51}), 422)

    def test_validation(self):
        for change in ({"id": "A"}, {"enabled": "true"}, {"name": " "}, {"plc_write": True}):
            self.assert_problem(self.client.post(self.root, json={**self.body, **change}), 422)

    def test_optimistic_update(self):
        self.make()
        patch = {"name": "AHU standby", "enabled": False}
        self.assert_problem(self.client.put(self.path, json=patch), 428)
        for tag in ('W/"1"', '*', '"1", "2"'):
            self.assert_problem(self.client.put(self.path, json=patch, headers={"If-Match": tag}), 400)
        r = self.client.put(self.path, json=patch, headers={"If-Match": '"1"'})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("etag", r.headers)
        self.assert_problem(self.client.put(self.path, json=patch, headers={"If-Match": '"1"'}), 412)
        self.assertEqual(self.client.get(self.path).headers["etag"], '"2"')
        same = self.client.put(self.path, json=patch, headers={"If-Match": '"2"'})
        self.assertEqual(same.json()["revision"], 2)

    def test_two_concurrent_writers_have_one_winner(self):
        self.make()
        def write(name):
            with TestClient(self.app) as client:
                return client.put(self.path, json={"name": name, "enabled": False},
                                  headers={"If-Match": '"1"'}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(write, ["Writer A", "Writer B"])), [200, 412])
        self.assertEqual(self.client.get(self.path).json()["revision"], 2)

    def test_openapi_problem_matches_wire(self):
        s = self.client.get("/openapi.json").json()
        read = s["paths"]["/v1/devices/{device_id}"]["get"]["responses"]
        write = s["paths"]["/v1/devices/{device_id}"]["put"]["responses"]
        self.assertIn("ETag", read["200"]["headers"])
        self.assertIn("application/problem+json", write["412"]["content"])
        self.assertNotIn("application/json", write["422"]["content"])


if __name__ == "__main__":
    unittest.main()
