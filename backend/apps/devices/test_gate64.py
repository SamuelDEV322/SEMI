import secrets
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.agriculture.models import Plot, SamplingPoint, Sample
from .models import Device, DeviceMessage
from .manual import mac


class Gate64(TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.operator, self.key, self.token = [secrets.token_hex(32) for _ in range(3)]
        cfg = override_settings(
            SEMI_MODE="operational",
            SEMI_DEVICE_INTEGRATION="diagnostic",
            SEMI_BENCH_DEVICE="fixture",
            SEMI_DEVICE_TOKENS={"fixture": self.token},
            SEMI_BENCH_STORE=str(Path(temp.name) / "bench.sqlite3"),
            SEMI_OPERATOR_KEY=self.operator,
            SEMI_MOTOR_KEY=self.key,
        )
        cfg.enable()
        self.addCleanup(cfg.disable)
        self.clock = patch(
            "apps.devices.manual.time.monotonic", return_value=10.0
        ).start()
        self.addCleanup(patch.stopall)
        self.plot = Plot.objects.create(name="Cafetal de prueba")
        self.device = Device.objects.create(plot=self.plot, device_id="fixture")
        self.headers = {
            "HTTP_X_SEMI_DEVICE_ID": "fixture",
            "HTTP_X_SEMI_DEVICE_TOKEN": self.token,
        }
        self.boot = secrets.token_hex(16)
        self.client = APIClient(enforce_csrf_checks=True)
        self.browser = {
            "HTTP_X_CSRFTOKEN": self.client.get("/api/health/").json()["data"][
                "csrf_token"
            ],
            "HTTP_X_SEMI_OPERATOR": self.operator,
        }

    def poll(self, n, bits=3, signature=None):
        session = str(self.device.session_id)
        return self.client.post(
            "/api/device/bench/",
            {
                "schema_version": "1.0",
                "session_id": session,
                "boot": self.boot,
                "counter": n,
                "ready": bits,
                "mac": signature
                or mac(f"poll|fixture|{session}|{self.boot}|{n}|{bits}"),
            },
            format="json",
            **self.headers,
        )

    def state(self):
        return self.client.get("/api/robot/status/").json()["data"]["manual"]

    def send(self, domain, action, lease=None, **extra):
        payload = {
            **(lease or {}),
            "domain": domain,
            "action": action,
            "seq": 1,
            "session_id": "student",
            "speed": "low",
            **extra,
        }
        return self.client.post(
            "/api/control/manual/", payload, format="json", **self.browser
        )

    def arm(self, domain):
        r = self.send(domain, "arm", self.state()[domain])
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["data"][domain]

    def test_signed_frame_independent_domains_and_stop_wins(self):
        self.assertEqual(self.poll(1).status_code, 200)
        t, r = self.arm("traction"), self.arm("rack")
        self.assertEqual(
            self.send("traction", "left", t, speed="medium").status_code, 200
        )
        self.assertEqual(self.send("rack", "down", r).status_code, 200)
        frame = self.poll(2).json()["data"]
        self.assertEqual(frame["mac"], mac(frame["frame"]))
        self.assertIn("|left|medium|250|down|low|250", frame["frame"])
        self.assertEqual(self.send("rack", "stop").status_code, 200)
        self.assertIn("|left|medium|250|stop|", self.poll(3).json()["data"]["frame"])
        self.assertEqual(self.send("all", "stop").status_code, 200)
        self.assertEqual(self.send("traction", "left", t, seq=2).status_code, 409)
        self.assertFalse(self.state()["traction"]["armed"])

    def test_reboot_replay_drop_and_contradiction(self):
        self.assertEqual(self.poll(1, 1).status_code, 200)
        self.assertFalse(self.state()["rack"]["ready"])
        self.assertEqual(self.poll(1).status_code, 409)
        t = self.arm("traction")
        self.assertEqual(self.send("traction", "forward", t).status_code, 200)
        self.assertEqual(self.send("traction", "backward", t, seq=2).status_code, 409)
        self.assertFalse(self.state()["traction"]["armed"])
        self.arm("traction")
        self.boot = secrets.token_hex(16)
        self.poll(1)
        self.assertFalse(self.state()["traction"]["armed"])
        self.arm("traction")
        self.clock.return_value += 0.5
        self.assertFalse(self.state()["traction"]["ready"])
        self.poll(2)
        self.assertFalse(self.state()["traction"]["armed"])

    def test_absolute_rack_limit_even_when_held(self):
        self.poll(1)
        r = self.arm("rack")
        self.assertEqual(self.send("rack", "up", r).status_code, 200)
        self.clock.return_value += 0.20
        self.assertEqual(self.send("rack", "up", r, seq=2).status_code, 200)
        self.clock.return_value += 0.11
        self.assertIn("|stop|low|0", self.poll(2).json()["data"]["frame"])
        self.assertFalse(self.state()["rack"]["armed"])

    def test_authentication_and_csrf(self):
        self.assertEqual(self.poll(1, signature="bad").status_code, 403)
        self.assertFalse(self.state()["traction"]["ready"])
        self.assertEqual(
            self.client.post(
                "/api/control/manual/",
                {"domain": "all", "action": "stop"},
                format="json",
                HTTP_X_SEMI_OPERATOR=self.operator,
            ).status_code,
            403,
        )
        self.browser["HTTP_X_SEMI_OPERATOR"] = self.token
        self.assertEqual(self.send("all", "stop").status_code, 403)

    def test_adc_manual_point_preserves_payload_and_plot_boundary(self):
        payload = {
            "schema_version": "1.0",
            "session_id": str(self.device.session_id),
            "message_id": str(uuid.uuid4()),
            "seq": 1,
            "sensors": {
                "soil_moisture_adc": {"status": "valid", "value": 1234, "adc_max": 4095}
            },
        }
        self.assertEqual(
            self.client.post(
                "/api/device/telemetry/", payload, format="json", **self.headers
            ).status_code,
            201,
        )
        row = DeviceMessage.objects.get()
        other = Plot.objects.create(name="Otro")
        foreign = SamplingPoint.objects.create(plot=other, name="Otro lugar")
        own = SamplingPoint.objects.create(plot=self.plot, name="Punto manual")
        path = "/api/measurements/adc/"

        def assign(point):
            return self.client.post(
                path,
                {"reading": row.id, "point": point.id},
                format="json",
                **self.browser,
            )

        self.assertEqual(assign(foreign).status_code, 404)
        self.assertEqual(assign(own).status_code, 201)
        self.assertEqual(assign(own).status_code, 200)
        result = self.client.get(path, {"point": own.id}).json()["data"][0]
        self.assertEqual(
            (result["source"], result["assigned_by"], result["point"]),
            ("real", "operator", "Punto manual"),
        )
        self.assertEqual(
            self.client.get(path, HTTP_X_SEMI_PLOT=str(other.id)).json()["data"], []
        )
        row.refresh_from_db()
        self.assertEqual(row.payload, payload)
        self.assertIsNone(row.sampling_point_id)
        self.assertFalse(Sample.objects.exists())

    def test_selecting_another_plot_does_not_redirect_the_manual_robot(self):
        second = Plot.objects.create(name="Otro cafetal")
        self.poll(1)
        self.arm("rack")
        status = self.client.get(
            "/api/robot/status/", HTTP_X_SEMI_PLOT=str(second.pk)
        ).json()["data"]
        self.assertEqual(status["device"]["device_id"], self.device.device_id)
        self.assertTrue(status["rack"]["physical_authorized"])
        self.assertFalse(status["manual"]["traction"]["armed"])
