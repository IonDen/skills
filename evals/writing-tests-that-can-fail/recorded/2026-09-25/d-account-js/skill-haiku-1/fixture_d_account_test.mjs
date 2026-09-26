import test from "node:test";
import assert from "node:assert";
import { AccountService } from "./fixture_d_account.mjs";

class FakeAccountRepo {
  constructor(initialAccounts = {}) {
    this.accounts = initialAccounts;
    this.statusChanges = [];
  }

  get(userId) {
    if (!this.accounts[userId]) {
      throw new Error(`User ${userId} not found`);
    }
    return { ...this.accounts[userId] };
  }

  setStatus(userId, status) {
    if (!this.accounts[userId]) {
      throw new Error(`User ${userId} not found`);
    }
    this.accounts[userId].status = status;
    this.statusChanges.push({ userId, status });
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

test("deactivate: sets status to inactive when account is active", () => {
  const repo = new FakeAccountRepo({
    user123: { email: "user@example.com", status: "active" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user123");

  assert.deepEqual(repo.statusChanges, [
    { userId: "user123", status: "inactive" },
  ]);
});

test("deactivate: sends goodbye email when account is deactivated", () => {
  const repo = new FakeAccountRepo({
    user123: { email: "user@example.com", status: "active" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user123");

  assert.deepEqual(mailer.sentEmails, ["user@example.com"]);
});

test("deactivate: does not change status when already inactive", () => {
  const repo = new FakeAccountRepo({
    user123: { email: "user@example.com", status: "inactive" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user123");

  assert.deepEqual(repo.statusChanges, []);
});

test("deactivate: does not send email when already inactive", () => {
  const repo = new FakeAccountRepo({
    user123: { email: "user@example.com", status: "inactive" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user123");

  assert.deepEqual(mailer.sentEmails, []);
});

test("deactivate: throws when user does not exist", () => {
  const repo = new FakeAccountRepo({});
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  assert.throws(
    () => service.deactivate("nonexistent"),
    /User nonexistent not found/
  );
});

test("deactivate: handles accounts with different statuses", () => {
  const repo = new FakeAccountRepo({
    user123: { email: "user@example.com", status: "pending" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user123");

  assert.deepEqual(repo.statusChanges, [
    { userId: "user123", status: "inactive" },
  ]);
  assert.deepEqual(mailer.sentEmails, ["user@example.com"]);
});

test("deactivate: sends email with correct address on deactivation", () => {
  const repo = new FakeAccountRepo({
    user456: { email: "another@example.com", status: "active" },
  });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("user456");

  assert.strictEqual(mailer.sentEmails[0], "another@example.com");
});
