// Account lifecycle service.

export class AccountRepo {
  get(userId) {
    throw new Error("real DB access");
  }

  setStatus(userId, status) {
    throw new Error("real DB access");
  }
}

export class Mailer {
  sendGoodbye(email) {
    throw new Error("real email send");
  }
}

export class AccountService {
  constructor(repo, mailer) {
    this.repo = repo;
    this.mailer = mailer;
  }

  deactivate(userId) {
    const account = this.repo.get(userId);
    if (account.status === "inactive") return;
    this.repo.setStatus(userId, "inactive");
    this.mailer.sendGoodbye(account.email);
  }
}
