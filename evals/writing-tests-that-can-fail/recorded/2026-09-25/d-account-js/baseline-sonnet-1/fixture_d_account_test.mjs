import test from "node:test";
import assert from "node:assert/strict";
import { AccountRepo, Mailer, AccountService } from "./fixture_d_account.mjs";

class FakeRepo {
  constructor(account) {
    this.account = account;
    this.setStatusCalls = [];
  }
  get(userId) {
    this.getCalledWith = userId;
    return this.account;
  }
  setStatus(userId, status) {
    this.setStatusCalls.push({ userId, status });
    this.account.status = status;
  }
}

class FakeMailer {
  constructor() {
    this.sentTo = [];
  }
  sendGoodbye(email) {
    this.sentTo.push(email);
  }
}

test("AccountRepo.get throws by default", () => {
  const repo = new AccountRepo();
  assert.throws(() => repo.get("u1"), /real DB access/);
});

test("AccountRepo.setStatus throws by default", () => {
  const repo = new AccountRepo();
  assert.throws(() => repo.setStatus("u1", "inactive"), /real DB access/);
});

test("Mailer.sendGoodbye throws by default", () => {
  const mailer = new Mailer();
  assert.throws(() => mailer.sendGoodbye("a@b.com"), /real email send/);
});

test("deactivate sets status to inactive and sends goodbye email for active account", () => {
  const repo = new FakeRepo({ status: "active", email: "user@example.com" });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("u1");

  assert.equal(repo.getCalledWith, "u1");
  assert.deepEqual(repo.setStatusCalls, [{ userId: "u1", status: "inactive" }]);
  assert.deepEqual(mailer.sentTo, ["user@example.com"]);
});

test("deactivate is a no-op when account is already inactive", () => {
  const repo = new FakeRepo({ status: "inactive", email: "user@example.com" });
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  service.deactivate("u1");

  assert.deepEqual(repo.setStatusCalls, []);
  assert.deepEqual(mailer.sentTo, []);
});

test("deactivate calls setStatus before sending the goodbye email", () => {
  const order = [];
  const repo = {
    get: () => ({ status: "active", email: "user@example.com" }),
    setStatus: () => order.push("setStatus"),
  };
  const mailer = {
    sendGoodbye: () => order.push("sendGoodbye"),
  };
  const service = new AccountService(repo, mailer);

  service.deactivate("u1");

  assert.deepEqual(order, ["setStatus", "sendGoodbye"]);
});

test("deactivate propagates errors from repo.get and does not email", () => {
  const repo = {
    get: () => {
      throw new Error("real DB access");
    },
    setStatus: () => {
      throw new Error("should not be called");
    },
  };
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  assert.throws(() => service.deactivate("u1"), /real DB access/);
  assert.deepEqual(mailer.sentTo, []);
});

test("deactivate propagates errors from repo.setStatus and does not email", () => {
  const repo = {
    get: () => ({ status: "active", email: "user@example.com" }),
    setStatus: () => {
      throw new Error("write failed");
    },
  };
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  assert.throws(() => service.deactivate("u1"), /write failed/);
  assert.deepEqual(mailer.sentTo, []);
});

test("deactivate propagates errors from mailer.sendGoodbye after status is updated", () => {
  const repo = new FakeRepo({ status: "active", email: "user@example.com" });
  const mailer = {
    sendGoodbye: () => {
      throw new Error("real email send");
    },
  };
  const service = new AccountService(repo, mailer);

  assert.throws(() => service.deactivate("u1"), /real email send/);
  assert.deepEqual(repo.setStatusCalls, [{ userId: "u1", status: "inactive" }]);
});
