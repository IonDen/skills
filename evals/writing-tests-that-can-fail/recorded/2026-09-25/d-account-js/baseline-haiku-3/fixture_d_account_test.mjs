import test from 'node:test';
import assert from 'node:assert';
import { AccountRepo, Mailer, AccountService } from './fixture_d_account.mjs';

test('AccountService.deactivate', async (suite) => {
  const mockRepo = () => {
    const repo = Object.create(AccountRepo.prototype);
    repo.getCalls = [];
    repo.setStatusCalls = [];
    repo.get = function(userId) {
      this.getCalls.push(userId);
      return { status: 'active', email: 'user@example.com' };
    };
    repo.setStatus = function(userId, status) {
      this.setStatusCalls.push({ userId, status });
    };
    return repo;
  };

  const mockMailer = () => {
    const mailer = Object.create(Mailer.prototype);
    mailer.sendGoodbyeCalls = [];
    mailer.sendGoodbye = function(email) {
      this.sendGoodbyeCalls.push(email);
    };
    return mailer;
  };

  await suite.test('deactivates an active account', () => {
    const repo = mockRepo();
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    service.deactivate('user123');

    assert.deepEqual(repo.getCalls, ['user123']);
    assert.deepEqual(repo.setStatusCalls, [{ userId: 'user123', status: 'inactive' }]);
    assert.deepEqual(mailer.sendGoodbyeCalls, ['user@example.com']);
  });

  await suite.test('skips operations when account is already inactive', () => {
    const repo = mockRepo();
    repo.get = function(userId) {
      this.getCalls.push(userId);
      return { status: 'inactive', email: 'user@example.com' };
    };
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    service.deactivate('user123');

    assert.deepEqual(repo.getCalls, ['user123']);
    assert.deepEqual(repo.setStatusCalls, []);
    assert.deepEqual(mailer.sendGoodbyeCalls, []);
  });

  await suite.test('retrieves account by correct userId', () => {
    const repo = mockRepo();
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    service.deactivate('specific-user-id');

    assert.strictEqual(repo.getCalls[0], 'specific-user-id');
  });

  await suite.test('sends goodbye email to correct email address', () => {
    const repo = mockRepo();
    repo.get = function(userId) {
      this.getCalls.push(userId);
      return { status: 'active', email: 'john@example.com' };
    };
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    service.deactivate('user123');

    assert.strictEqual(mailer.sendGoodbyeCalls[0], 'john@example.com');
  });

  await suite.test('sets status to inactive on repo', () => {
    const repo = mockRepo();
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    service.deactivate('user456');

    assert.strictEqual(repo.setStatusCalls[0].status, 'inactive');
  });

  await suite.test('passes correct userId to setStatus', () => {
    const repo = mockRepo();
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    service.deactivate('target-user');

    assert.strictEqual(repo.setStatusCalls[0].userId, 'target-user');
  });

  await suite.test('returns undefined', () => {
    const repo = mockRepo();
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    const result = service.deactivate('user123');

    assert.strictEqual(result, undefined);
  });

  await suite.test('handles multiple deactivation calls', () => {
    const repo = mockRepo();
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    service.deactivate('user1');
    service.deactivate('user2');

    assert.deepEqual(repo.getCalls, ['user1', 'user2']);
    assert.strictEqual(repo.setStatusCalls.length, 2);
    assert.strictEqual(mailer.sendGoodbyeCalls.length, 2);
  });

  await suite.test('handles account with different statuses', () => {
    const repo = mockRepo();
    repo.get = function(userId) {
      this.getCalls.push(userId);
      return { status: 'suspended', email: 'user@example.com' };
    };
    const mailer = mockMailer();
    const service = new AccountService(repo, mailer);

    service.deactivate('user123');

    assert.deepEqual(repo.setStatusCalls, [{ userId: 'user123', status: 'inactive' }]);
    assert.deepEqual(mailer.sendGoodbyeCalls, ['user@example.com']);
  });
});
