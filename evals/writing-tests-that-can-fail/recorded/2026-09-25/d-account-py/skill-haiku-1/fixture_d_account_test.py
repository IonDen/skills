"""Tests for AccountService deactivate logic."""

import pytest
from fixture_d_account import Account, AccountRepo, Mailer, AccountService


class FakeAccountRepo(AccountRepo):
    def __init__(self):
        self.accounts = {}
        self.status_updates = []

    def get(self, user_id: str) -> Account:
        if user_id not in self.accounts:
            raise ValueError(f"Account not found: {user_id}")
        return self.accounts[user_id]

    def set_status(self, user_id: str, status: str) -> None:
        self.status_updates.append((user_id, status))
        if user_id in self.accounts:
            self.accounts[user_id].status = status


class FakeMailer(Mailer):
    def __init__(self):
        self.messages = []

    def send_goodbye(self, email: str) -> None:
        self.messages.append(email)


@pytest.fixture
def repo():
    return FakeAccountRepo()


@pytest.fixture
def mailer():
    return FakeMailer()


@pytest.fixture
def service(repo, mailer):
    return AccountService(repo, mailer)


class TestAccountServiceDeactivate:
    def test_deactivate_active_account_sets_status_to_inactive(self, repo, service):
        repo.accounts["user123"] = Account(user_id="user123", email="test@example.com", status="active")

        service.deactivate("user123")

        assert repo.accounts["user123"].status == "inactive"

    def test_deactivate_active_account_sends_goodbye_email(self, repo, mailer, service):
        repo.accounts["user123"] = Account(user_id="user123", email="alice@example.com", status="active")

        service.deactivate("user123")

        assert "alice@example.com" in mailer.messages

    def test_deactivate_active_account_calls_repo_set_status(self, repo, service):
        repo.accounts["user123"] = Account(user_id="user123", email="test@example.com", status="active")

        service.deactivate("user123")

        assert ("user123", "inactive") in repo.status_updates

    def test_deactivate_inactive_account_is_noop(self, repo, mailer, service):
        repo.accounts["user123"] = Account(user_id="user123", email="test@example.com", status="inactive")

        service.deactivate("user123")

        assert repo.status_updates == []
        assert mailer.messages == []

    def test_deactivate_sends_email_to_correct_recipient(self, repo, mailer, service):
        repo.accounts["user456"] = Account(user_id="user456", email="bob@company.org", status="active")

        service.deactivate("user456")

        assert mailer.messages == ["bob@company.org"]

    def test_deactivate_multiple_accounts_independently(self, repo, mailer, service):
        repo.accounts["user1"] = Account(user_id="user1", email="alice@example.com", status="active")
        repo.accounts["user2"] = Account(user_id="user2", email="bob@example.com", status="active")

        service.deactivate("user1")
        service.deactivate("user2")

        assert repo.accounts["user1"].status == "inactive"
        assert repo.accounts["user2"].status == "inactive"
        assert mailer.messages == ["alice@example.com", "bob@example.com"]

    def test_deactivate_already_inactive_twice_stays_noop(self, repo, mailer, service):
        repo.accounts["user123"] = Account(user_id="user123", email="test@example.com", status="inactive")

        service.deactivate("user123")
        service.deactivate("user123")

        assert repo.status_updates == []
        assert mailer.messages == []

    def test_deactivate_active_then_deactivate_again_no_second_email(self, repo, mailer, service):
        repo.accounts["user123"] = Account(user_id="user123", email="test@example.com", status="active")

        service.deactivate("user123")
        service.deactivate("user123")

        assert mailer.messages == ["test@example.com"]
        assert len(repo.status_updates) == 1
