"""Tests for fixture_d_account.py."""

import pytest

from fixture_d_account import Account, AccountRepo, AccountService, Mailer


class FakeAccountRepo(AccountRepo):
    def __init__(self, account: Account) -> None:
        self.account = account
        self.set_status_calls = []

    def get(self, user_id: str) -> Account:
        assert user_id == self.account.user_id
        return self.account

    def set_status(self, user_id: str, status: str) -> None:
        self.set_status_calls.append((user_id, status))
        self.account.status = status


class FakeMailer(Mailer):
    def __init__(self) -> None:
        self.sent_to = []

    def send_goodbye(self, email: str) -> None:
        self.sent_to.append(email)


@pytest.fixture
def active_account() -> Account:
    return Account(user_id="u1", email="u1@example.com", status="active")


@pytest.fixture
def inactive_account() -> Account:
    return Account(user_id="u2", email="u2@example.com", status="inactive")


def test_deactivate_active_account_sets_status_and_sends_email(active_account):
    repo = FakeAccountRepo(active_account)
    mailer = FakeMailer()
    service = AccountService(repo, mailer)

    service.deactivate("u1")

    assert repo.set_status_calls == [("u1", "inactive")]
    assert mailer.sent_to == ["u1@example.com"]
    assert active_account.status == "inactive"


def test_deactivate_already_inactive_account_is_noop(inactive_account):
    repo = FakeAccountRepo(inactive_account)
    mailer = FakeMailer()
    service = AccountService(repo, mailer)

    service.deactivate("u2")

    assert repo.set_status_calls == []
    assert mailer.sent_to == []


def test_deactivate_looks_up_correct_user_id(active_account):
    repo = FakeAccountRepo(active_account)
    mailer = FakeMailer()
    service = AccountService(repo, mailer)

    with pytest.raises(AssertionError):
        service.deactivate("someone-else")


def test_account_is_dataclass_with_expected_fields():
    account = Account(user_id="u3", email="u3@example.com", status="active")

    assert account.user_id == "u3"
    assert account.email == "u3@example.com"
    assert account.status == "active"


def test_account_repo_base_methods_raise_not_implemented():
    repo = AccountRepo()

    with pytest.raises(NotImplementedError):
        repo.get("u1")

    with pytest.raises(NotImplementedError):
        repo.set_status("u1", "inactive")


def test_mailer_base_method_raises_not_implemented():
    mailer = Mailer()

    with pytest.raises(NotImplementedError):
        mailer.send_goodbye("u1@example.com")
