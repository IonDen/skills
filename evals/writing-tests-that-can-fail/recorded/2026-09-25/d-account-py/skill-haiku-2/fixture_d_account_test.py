"""Tests for AccountService.deactivate logic."""

import pytest
from fixture_d_account import Account, AccountRepo, Mailer, AccountService


class FakeAccountRepo(AccountRepo):
    """Fake repo that stores accounts in memory."""

    def __init__(self):
        self.accounts = {}

    def get(self, user_id: str) -> Account:
        if user_id not in self.accounts:
            raise KeyError(f"User {user_id} not found")
        return self.accounts[user_id]

    def set_status(self, user_id: str, status: str) -> None:
        if user_id not in self.accounts:
            raise KeyError(f"User {user_id} not found")
        self.accounts[user_id].status = status


class FakeMailer(Mailer):
    """Fake mailer that collects sent emails."""

    def __init__(self):
        self.sent_emails = []

    def send_goodbye(self, email: str) -> None:
        self.sent_emails.append(email)


class TestAccountServiceDeactivate:
    """Test deactivate behavior."""

    def test_deactivate_active_account_changes_status(self):
        """Flips status from active to inactive."""
        repo = FakeAccountRepo()
        repo.accounts["user1"] = Account("user1", "alice@example.com", "active")
        mailer = FakeMailer()
        svc = AccountService(repo, mailer)

        svc.deactivate("user1")

        assert repo.get("user1").status == "inactive"

    def test_deactivate_active_account_sends_goodbye_email(self):
        """Sends email when deactivating an active account."""
        repo = FakeAccountRepo()
        repo.accounts["user1"] = Account("user1", "alice@example.com", "active")
        mailer = FakeMailer()
        svc = AccountService(repo, mailer)

        svc.deactivate("user1")

        assert mailer.sent_emails == ["alice@example.com"]

    def test_deactivate_inactive_account_does_not_change_status(self):
        """Already inactive account stays inactive, no side effects.

        Catches bugs where the status check is inverted or missing.
        """
        repo = FakeAccountRepo()
        repo.accounts["user2"] = Account("user2", "bob@example.com", "inactive")
        mailer = FakeMailer()
        svc = AccountService(repo, mailer)

        svc.deactivate("user2")

        assert repo.get("user2").status == "inactive"

    def test_deactivate_inactive_account_sends_no_goodbye_email(self):
        """Already inactive account gets no goodbye email.

        Catches bugs where the early return is missing or the status check is wrong.
        """
        repo = FakeAccountRepo()
        repo.accounts["user2"] = Account("user2", "bob@example.com", "inactive")
        mailer = FakeMailer()
        svc = AccountService(repo, mailer)

        svc.deactivate("user2")

        assert mailer.sent_emails == []

    def test_deactivate_nonexistent_user_raises_key_error(self):
        """Repo.get() for missing user raises KeyError."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        svc = AccountService(repo, mailer)

        with pytest.raises(KeyError):
            svc.deactivate("user_not_found")

    def test_deactivate_twice_sends_email_only_once(self):
        """Second deactivation of same user sends no email.

        Catches bugs where the status check is inverted or the early return is wrong.
        """
        repo = FakeAccountRepo()
        repo.accounts["user1"] = Account("user1", "alice@example.com", "active")
        mailer = FakeMailer()
        svc = AccountService(repo, mailer)

        svc.deactivate("user1")
        svc.deactivate("user1")

        assert len(mailer.sent_emails) == 1

    def test_deactivate_twice_status_remains_inactive(self):
        """Idempotent: deactivating twice leaves status as inactive."""
        repo = FakeAccountRepo()
        repo.accounts["user1"] = Account("user1", "alice@example.com", "active")
        mailer = FakeMailer()
        svc = AccountService(repo, mailer)

        svc.deactivate("user1")
        svc.deactivate("user1")

        assert repo.get("user1").status == "inactive"

    def test_deactivate_preserves_email_address(self):
        """Deactivation doesn't change the email field."""
        repo = FakeAccountRepo()
        repo.accounts["user1"] = Account("user1", "alice@example.com", "active")
        mailer = FakeMailer()
        svc = AccountService(repo, mailer)

        svc.deactivate("user1")

        assert repo.get("user1").email == "alice@example.com"
