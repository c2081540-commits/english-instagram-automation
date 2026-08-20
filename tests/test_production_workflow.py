import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ProductionWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (REPO_ROOT / ".github" / "workflows" / "post-due.yml").read_text()
        cls.gas = (REPO_ROOT / "examples" / "gas" / "dispatch_due_posts.gs").read_text()

    def test_dispatch_and_manual_entry_points_call_one_existing_runner(self):
        self.assertIn("repository_dispatch:", self.workflow)
        self.assertIn("types: [due-post-check]", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertEqual(self.workflow.count("scripts/run_due_post.py --live"), 1)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_workflow_contains_no_schedule_or_content(self):
        for forbidden in ("ENG-", "07:00", "09:30", "12:00", "15:00", "18:00", "20:30", "22:30"):
            self.assertNotIn(forbidden, self.workflow)

    def test_state_is_committed_only_when_changed_without_force_push(self):
        self.assertIn("git diff --quiet -- data/queue data/receipts", self.workflow)
        self.assertIn("git add -- data/queue data/receipts", self.workflow)
        self.assertIn("git pull --rebase origin main", self.workflow)
        self.assertIn("git push origin HEAD:main", self.workflow)
        self.assertNotIn("git add .", self.workflow)
        self.assertNotIn("--force", self.workflow)

    def test_gas_is_dispatch_only_and_five_minute(self):
        self.assertIn("everyMinutes(5)", self.gas)
        self.assertIn("event_type: 'due-post-check'", self.gas)
        for required in ("GITHUB_DISPATCH_TOKEN", "GITHUB_OWNER", "INSTAGRAM_REPOSITORY", "THREADS_REPOSITORY"):
            self.assertIn(required, self.gas)
        for forbidden in ("graph.instagram.com", "graph.threads.net", "ENG-", "publish_at"):
            self.assertNotIn(forbidden, self.gas)


if __name__ == "__main__":
    unittest.main()
