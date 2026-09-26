"""Account lifecycle service."""

from dataclasses import dataclass


@dataclass
class Account:
    user_id: str
    email: str
    status: str  # "active" | "inactive"


class AccountRepo:
    def get(self, user_id: str) -> Account:
        raise NotImplementedError("real DB access")

    def set_status(self, user_id: str, status: str) -> None:
        raise NotImplementedError("real DB access")


class Mailer:
    def send_goodbye(self, email: str) -> None:
        raise NotImplementedError("real email send")


class AccountService:
    def __init__(self, repo: AccountRepo, mailer: Mailer) -> None:
        self._repo = repo
        self._mailer = mailer

    def deactivate(self, user_id: str) -> None:
        account = self._repo.get(user_id)
        if account.status == "inactive":
            return
        self._repo.set_status(user_id, "inactive")
        self._mailer.send_goodbye(account.email)
