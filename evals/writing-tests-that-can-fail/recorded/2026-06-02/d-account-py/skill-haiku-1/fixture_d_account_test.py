"""Test suite for AccountService.deactivate."""

import pytest
from fixture_d_account import Account, AccountRepo, Mailer, AccountService


class InMemoryAccountRepo(AccountRepo):
    """Fake repository: in-memory storage, no network."""

    def __init__(self):
        self._accounts = {}

    def set_account(self, account: Account) -> None:
        """Helper: initialize an account (for test setup)."""
        self._accounts[account.user_id] = account

    def get(self, user_id: str) -> Account:
        """Return the stored account or raise if not found."""
        if user_id not in self._accounts:
            raise KeyError(f"Account {user_id} not found")
        return self._accounts[user_id]

    def set_status(self, user_id: str, status: str) -> None:
        """Update the account status in memory."""
        if user_id not in self._accounts:
            raise KeyError(f"Account {user_id} not found")
        self._accounts[user_id].status = status


class RecordingMailer(Mailer):
    """Fake mailer: records all sent emails, no network."""

    def __init__(self):
        self.sent_emails = []

    def send_goodbye(self, email: str) -> None:
        """Record the email address a goodbye was sent to."""
        self.sent_emails.append(email)


class TestDeactivateHappyPath:
    """Bugs caught: missing status update, missing email."""

    def test_deactivate_sets_status_to_inactive(self):
        """Bug: forgot to call repo.set_status."""
        repo = InMemoryAccountRepo()
        repo.set_account(Account(user_id="u1", email="alice@example.com", status="active"))
        service = AccountService(repo, RecordingMailer())

        service.deactivate("u1")

        account = repo.get("u1")
        assert account.status == "inactive"

    def test_deactivate_sends_goodbye_email(self):
        """Bug: forgot to call mailer.send_goodbye."""
        repo = InMemoryAccountRepo()
        repo.set_account(Account(user_id="u1", email="alice@example.com", status="active"))
        mailer = RecordingMailer()
        service = AccountService(repo, mailer)

        service.deactivate("u1")

        assert len(mailer.sent_emails) == 1
        assert mailer.sent_emails[0] == "alice@example.com"

    def test_deactivate_uses_correct_email_from_account(self):
        """Bug: hardcoded wrong email or used user_id instead of account.email."""
        repo = InMemoryAccountRepo()
        repo.set_account(
            Account(user_id="user123", email="bob@example.org", status="active")
        )
        mailer = RecordingMailer()
        service = AccountService(repo, mailer)

        service.deactivate("user123")

        assert mailer.sent_emails[0] == "bob@example.org"


class TestDeactivateIdempotency:
    """Bug caught: missing idempotency check (calling twice sends two emails)."""

    def test_deactivate_already_inactive_is_noop(self):
        """Bug: no guard against re-deactivating an inactive account.

        If the guard is removed, calling deactivate twice sends two emails.
        """
        repo = InMemoryAccountRepo()
        repo.set_account(Account(user_id="u2", email="carol@example.com", status="inactive"))
        mailer = RecordingMailer()
        service = AccountService(repo, mailer)

        service.deactivate("u2")

        # Should be a no-op: no email sent, status unchanged.
        assert len(mailer.sent_emails) == 0
        assert repo.get("u2").status == "inactive"

    def test_deactivate_twice_sends_email_only_once(self):
        """Bug: missing idempotency means deactivate sends email on second call.

        If the idempotency guard is removed, the test goes red.
        """
        repo = InMemoryAccountRepo()
        repo.set_account(Account(user_id="u3", email="dave@example.com", status="active"))
        mailer = RecordingMailer()
        service = AccountService(repo, mailer)

        service.deactivate("u3")
        assert len(mailer.sent_emails) == 1
        assert repo.get("u3").status == "inactive"

        # Second call: should be a no-op.
        service.deactivate("u3")
        assert len(mailer.sent_emails) == 1, "Second deactivate should not send another email"
        assert repo.get("u3").status == "inactive"


class TestDeactivateOrderingAndState:
    """Bugs caught: wrong order (email before status update), partial failure."""

    def test_status_updated_before_email_sent(self):
        """Bug: email sent before status update (if mailer fails, account is still active).

        This test asserts that the state change is persistent in the repo before
        the email is sent. If order is reversed, we catch it as a behavior difference.
        """
        repo = InMemoryAccountRepo()
        repo.set_account(Account(user_id="u4", email="eve@example.com", status="active"))

        class VerifyingMailer(Mailer):
            """Mailer that checks the repo state when send_goodbye is called."""

            def __init__(self, repo):
                self.repo = repo
                self.account_status_when_called = None

            def send_goodbye(self, email: str) -> None:
                # At the time the email is sent, the account should already be inactive.
                self.account_status_when_called = self.repo.get("u4").status

        mailer = VerifyingMailer(repo)
        service = AccountService(repo, mailer)

        service.deactivate("u4")

        # The status should have been "inactive" at the time send_goodbye was called.
        assert mailer.account_status_when_called == "inactive"


class TestDeactivateErrorCases:
    """Bugs caught: missing error handling, silent failures."""

    def test_deactivate_nonexistent_account_raises(self):
        """Bug: silently ignore missing account instead of raising."""
        repo = InMemoryAccountRepo()
        mailer = RecordingMailer()
        service = AccountService(repo, mailer)

        with pytest.raises(KeyError):
            service.deactivate("nonexistent")

        # No email sent on error.
        assert len(mailer.sent_emails) == 0

    def test_deactivate_with_invalid_account_data_propagates_error(self):
        """Bug: not handling malformed account objects."""
        repo = InMemoryAccountRepo()

        # Simulate a corrupted account (missing email field by setting None).
        class BrokenAccount:
            def __init__(self):
                self.user_id = "u_broken"
                self.email = None  # This will cause mailer to fail if called.
                self.status = "active"

        class BrokenRepo(AccountRepo):
            def get(self, user_id: str):
                return BrokenAccount()

            def set_status(self, user_id: str, status: str):
                pass

        class StrictMailer(Mailer):
            def send_goodbye(self, email: str) -> None:
                if email is None:
                    raise ValueError("Email cannot be None")

        repo = BrokenRepo()
        mailer = StrictMailer()
        service = AccountService(repo, mailer)

        # The error from the mailer should propagate.
        with pytest.raises(ValueError):
            service.deactivate("u_broken")


class TestDeactivateMultipleUsers:
    """Bugs caught: cross-talk between users, wrong user deactivated."""

    def test_deactivate_one_user_does_not_affect_others(self):
        """Bug: deactivating one user affects another's status or emails."""
        repo = InMemoryAccountRepo()
        repo.set_account(Account(user_id="u_alice", email="alice@example.com", status="active"))
        repo.set_account(Account(user_id="u_bob", email="bob@example.com", status="active"))

        mailer = RecordingMailer()
        service = AccountService(repo, mailer)

        service.deactivate("u_alice")

        # Bob should still be active.
        assert repo.get("u_bob").status == "active"
        # Only Alice's email should have been sent.
        assert mailer.sent_emails == ["alice@example.com"]
        assert repo.get("u_alice").status == "inactive"

    def test_deactivate_correct_user_when_multiple_exist(self):
        """Bug: deactivating wrong user ID due to index mix-up or typo."""
        repo = InMemoryAccountRepo()
        repo.set_account(Account(user_id="user_001", email="first@example.com", status="active"))
        repo.set_account(Account(user_id="user_002", email="second@example.com", status="active"))
        repo.set_account(Account(user_id="user_003", email="third@example.com", status="active"))

        mailer = RecordingMailer()
        service = AccountService(repo, mailer)

        service.deactivate("user_002")

        assert repo.get("user_001").status == "active"
        assert repo.get("user_002").status == "inactive"
        assert repo.get("user_003").status == "active"
        assert mailer.sent_emails == ["second@example.com"]
