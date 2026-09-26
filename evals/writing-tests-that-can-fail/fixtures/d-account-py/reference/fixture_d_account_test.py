"""Reference suite: the real service with in-memory fakes; assertions on state."""
from fixture_d_account import Account, AccountService


class FakeRepo:
    def __init__(self, *accounts):
        self.accounts = {a.user_id: a for a in accounts}

    def get(self, user_id):
        return self.accounts[user_id]

    def set_status(self, user_id, status):
        old = self.accounts[user_id]
        self.accounts[user_id] = Account(old.user_id, old.email, status)


class FakeMailer:
    def __init__(self):
        self.goodbyes = []

    def send_goodbye(self, email):
        self.goodbyes.append(email)


def make(status):
    repo = FakeRepo(Account("u1", "u1@example.com", status))
    mailer = FakeMailer()
    return AccountService(repo, mailer), repo, mailer


def test_deactivating_an_active_account_marks_it_inactive():
    svc, repo, _ = make("active")
    svc.deactivate("u1")
    assert repo.accounts["u1"].status == "inactive"


def test_deactivating_an_active_account_sends_one_goodbye():
    svc, _, mailer = make("active")
    svc.deactivate("u1")
    assert mailer.goodbyes == ["u1@example.com"]


def test_deactivating_an_inactive_account_changes_nothing():
    svc, repo, mailer = make("inactive")
    svc.deactivate("u1")
    assert mailer.goodbyes == []
    assert repo.accounts["u1"].status == "inactive"
