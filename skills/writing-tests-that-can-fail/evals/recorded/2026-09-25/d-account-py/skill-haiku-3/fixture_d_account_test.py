"""Tests for AccountService deactivation logic."""

import pytest

from fixture_d_account import Account, AccountRepo, AccountService, Mailer


class FakeAccountRepo(AccountRepo):
    """In-memory implementation of AccountRepo for testing."""

    def __init__(self):
        self._accounts = {}

    def add_account(self, account: Account) -> None:
        """Add an account to the fake repo."""
        self._accounts[account.user_id] = account

    def get(self, user_id: str) -> Account:
        """Get an account by user_id."""
        if user_id not in self._accounts:
            raise ValueError(f"Account not found: {user_id}")
        return self._accounts[user_id]

    def set_status(self, user_id: str, status: str) -> None:
        """Set account status."""
        if user_id in self._accounts:
            self._accounts[user_id].status = status
        else:
            raise ValueError(f"Account not found: {user_id}")


class FakeMailer(Mailer):
    """In-memory implementation of Mailer for testing."""

    def __init__(self):
        self.sent_emails = []

    def send_goodbye(self, email: str) -> None:
        """Record that a goodbye email was sent."""
        self.sent_emails.append(email)


class TestAccountServiceDeactivate:
    """Test cases for AccountService.deactivate()."""

    def test_deactivate_active_account_sets_status(self):
        """Deactivating an active account should set its status to inactive."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user123", email="test@example.com", status="active")
        repo.add_account(account)

        service.deactivate("user123")

        assert account.status == "inactive"

    def test_deactivate_active_account_sends_goodbye_email(self):
        """Deactivating an active account should send a goodbye email."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user123", email="test@example.com", status="active")
        repo.add_account(account)

        service.deactivate("user123")

        assert "test@example.com" in mailer.sent_emails

    def test_deactivate_active_account_emails_correct_address(self):
        """The goodbye email should use the account's email address."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user456", email="alice@example.com", status="active")
        repo.add_account(account)

        service.deactivate("user456")

        assert mailer.sent_emails == ["alice@example.com"]

    def test_deactivate_already_inactive_does_not_change_status(self):
        """Deactivating an inactive account should not change its status."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user789", email="inactive@example.com", status="inactive")
        repo.add_account(account)

        service.deactivate("user789")

        assert account.status == "inactive"

    def test_deactivate_already_inactive_sends_no_email(self):
        """Deactivating an inactive account should not send a goodbye email."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user789", email="inactive@example.com", status="inactive")
        repo.add_account(account)

        service.deactivate("user789")

        assert len(mailer.sent_emails) == 0


    def test_deactivate_multiple_accounts_independently(self):
        """Deactivating multiple accounts should work independently."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account1 = Account(user_id="user1", email="alice@example.com", status="active")
        account2 = Account(user_id="user2", email="bob@example.com", status="active")
        repo.add_account(account1)
        repo.add_account(account2)

        service.deactivate("user1")
        service.deactivate("user2")

        assert account1.status == "inactive"
        assert account2.status == "inactive"
        assert set(mailer.sent_emails) == {"alice@example.com", "bob@example.com"}

    def test_deactivate_with_unicode_email(self):
        """Deactivating an account with unicode characters in email should work."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user_unicode", email="tëst@example.com", status="active")
        repo.add_account(account)

        service.deactivate("user_unicode")

        assert "tëst@example.com" in mailer.sent_emails
        assert account.status == "inactive"

    def test_deactivate_with_special_user_id(self):
        """Deactivating accounts with special characters in user_id should work."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user-123-xyz", email="test@example.com", status="active")
        repo.add_account(account)

        service.deactivate("user-123-xyz")

        assert account.status == "inactive"
        assert "test@example.com" in mailer.sent_emails

    def test_deactivate_with_empty_string_email(self):
        """Deactivating an account with empty email should still send goodbye."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user_no_email", email="", status="active")
        repo.add_account(account)

        service.deactivate("user_no_email")

        assert "" in mailer.sent_emails
        assert account.status == "inactive"

    def test_deactivate_preserves_other_account_fields(self):
        """Deactivating should only change status, not other account fields."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user123", email="test@example.com", status="active")
        repo.add_account(account)

        service.deactivate("user123")

        assert account.user_id == "user123"
        assert account.email == "test@example.com"
        assert account.status == "inactive"

    def test_deactivate_does_not_email_when_already_inactive_one(self):
        """Idempotency: deactivating twice sends email only once."""
        repo = FakeAccountRepo()
        mailer = FakeMailer()
        service = AccountService(repo, mailer)

        account = Account(user_id="user123", email="test@example.com", status="active")
        repo.add_account(account)

        service.deactivate("user123")
        first_call_emails = len(mailer.sent_emails)

        service.deactivate("user123")
        second_call_emails = len(mailer.sent_emails)

        assert first_call_emails == 1
        assert second_call_emails == 1

