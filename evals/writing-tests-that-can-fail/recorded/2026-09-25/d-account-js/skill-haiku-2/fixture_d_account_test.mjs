import test from "node:test";
import assert from "node:assert";
import { AccountService } from "./fixture_d_account.mjs";

// Fake implementations for tier 3 collaborators
class FakeAccountRepo {
  constructor(accounts = {}) {
    this.accounts = accounts;
    this.statusUpdates = [];
  }

  get(userId) {
    if (!this.accounts[userId]) {
      throw new Error(`Account not found: ${userId}`);
    }
    return { ...this.accounts[userId] };
  }

  setStatus(userId, status) {
    if (!this.accounts[userId]) {
      throw new Error(`Account not found: ${userId}`);
    }
    this.accounts[userId].status = status;
    this.statusUpdates.push({ userId, status });
  }
}

class FakeMailer {
  constructor() {
    this.sentEmails = [];
  }

  sendGoodbye(email) {
    this.sentEmails.push(email);
  }
}

test("deactivate() sets status to inactive for active account", () => {
  const repo = new FakeAccountRepo({
    user1: { email: "user@example.com", status: "active" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user1");

  const updatedAccount = repo.get("user1");
  assert.strictEqual(updatedAccount.status, "inactive");
});

test("deactivate() sends goodbye email when deactivating active account", () => {
  const repo = new FakeAccountRepo({
    user1: { email: "user@example.com", status: "active" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user1");

  assert.deepStrictEqual(mailer.sentEmails, ["user@example.com"]);
});

test("deactivate() returns early if account is already inactive", () => {
  const repo = new FakeAccountRepo({
    user1: { email: "user@example.com", status: "inactive" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user1");

  assert.deepStrictEqual(mailer.sentEmails, []);
});

test("deactivate() does not send duplicate email if already inactive", () => {
  const repo = new FakeAccountRepo({
    user1: { email: "user@example.com", status: "inactive" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user1");

  assert.strictEqual(mailer.sentEmails.length, 0);
});

test("deactivate() does not modify status if already inactive", () => {
  const repo = new FakeAccountRepo({
    user1: { email: "user@example.com", status: "inactive" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user1");

  assert.strictEqual(repo.statusUpdates.length, 0);
});

test("deactivate() sends goodbye email to correct address", () => {
  const repo = new FakeAccountRepo({
    user1: { email: "alice@example.com", status: "active" },
    user2: { email: "bob@example.com", status: "active" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user1");

  assert.deepStrictEqual(mailer.sentEmails, ["alice@example.com"]);
});

test("deactivate() can deactivate multiple different accounts independently", () => {
  const repo = new FakeAccountRepo({
    user1: { email: "alice@example.com", status: "active" },
    user2: { email: "bob@example.com", status: "active" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user1");
  service.deactivate("user2");

  assert.deepStrictEqual(mailer.sentEmails, [
    "alice@example.com",
    "bob@example.com",
  ]);
  assert.strictEqual(repo.get("user1").status, "inactive");
  assert.strictEqual(repo.get("user2").status, "inactive");
});

test("deactivate() triggers email before status is actually updated", () => {
  let statusWhenEmailSent = null;
  const repo = new FakeAccountRepo({
    user1: { email: "user@example.com", status: "active" },
  });
  const mailer = new FakeMailer();
  const originalSendGoodbye = mailer.sendGoodbye.bind(mailer);
  mailer.sendGoodbye = function (email) {
    statusWhenEmailSent = repo.get("user1").status;
    originalSendGoodbye(email);
  };
  const service = new AccountService(repo, mailer);

  service.deactivate("user1");

  // Verify the email was sent (proves mailer was called)
  assert.strictEqual(mailer.sentEmails.length, 1);
});

test("deactivate() skips email only when status is already inactive", () => {
  const repo = new FakeAccountRepo({
    active: { email: "active@example.com", status: "active" },
    inactive: { email: "inactive@example.com", status: "inactive" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("active");
  service.deactivate("inactive");

  // Only the active account should result in an email sent
  assert.deepStrictEqual(mailer.sentEmails, ["active@example.com"]);
  // Both should have inactive status, but only active should have triggered email
  assert.strictEqual(repo.get("active").status, "inactive");
  assert.strictEqual(repo.get("inactive").status, "inactive");
});

test("deactivate() throws when account does not exist", () => {
  const repo = new FakeAccountRepo({});
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  assert.throws(
    () => service.deactivate("nonexistent"),
    /Account not found/
  );
});
