# JavaScript and TypeScript (node:test, Vitest, Jest)

This file maps the skill's rules onto the tools of the JavaScript and TypeScript ecosystem.

## Runner

- `node:test` is built into Node. Run one file with `node --test path/to/file.test.js`.
- Vitest runs one file once, without watch mode, with `npx vitest run path/to/file.test.ts`.
- Jest runs one file with `npx jest path/to/file.test.js`. Use `npx jest --runTestsByPath path/to/file.test.js` when the path must match exactly.

Source: https://nodejs.org/api/test.html, https://vitest.dev/guide/cli, https://jestjs.io/docs/cli

## Writing a fake

In TypeScript, declare the adapter as an `interface` and write a small class that implements it with in-memory state. In plain JavaScript, duck typing is enough: an object with the same methods will do. Pass the fake in through the constructor or a parameter. Don't reach for module mocking.

```ts
interface UserStore { save(u: User): Promise<void>; findByEmail(e: string): Promise<User | undefined> }
class InMemoryUserStore implements UserStore {
  readonly users = new Map<string, User>();
  async save(u: User) { this.users.set(u.email, u); }
  async findByEmail(e: string) { return this.users.get(e); }
}
class FixedClock { constructor(private readonly at: Date) {} now() { return this.at; } }
```

Assert on `store.users` or on what the unit returns. Fake timers (`vi.useFakeTimers`, `vi.setSystemTime`, `mock.timers` in `node:test`) are for code that calls `setTimeout` or `Date` directly. An injected `FixedClock` is still the first choice.

Source: https://www.typescriptlang.org/docs/handbook/2/objects.html, https://vitest.dev/guide/mocking

## Mocking library (last resort)

- Vitest: `vi.fn`, `vi.spyOn`, `vi.mock`.
- Jest: `jest.fn`, `jest.spyOn`, `jest.mock`.
- `node:test`: `mock.fn`, `mock.method`.

The skill allows a mock only to verify an outgoing side effect that can't be avoided, at a boundary you don't own. These are the interaction assertions to look for in review: `toHaveBeenCalled`, `toHaveBeenCalledWith`, `toHaveBeenCalledTimes` and `toHaveBeenNthCalledWith` in Vitest and Jest; `mock.calls`, `mock.lastCall`, and in `node:test` `fn.mock.calls` and `fn.mock.callCount()`. If one of these is a test's main assertion, the test is checking the mock and not the behaviour. A `vi.mock` or `jest.mock` of a module you own replaces a tier 2 collaborator, and that is a finding.

Source: https://vitest.dev/guide/mocking, https://jestjs.io/docs/mock-function-api, https://nodejs.org/api/test.html#mocking

## Property-based testing

fast-check is maintained and works with any runner: `fc.assert(fc.property(fc.string(), (s) => decode(encode(s)) === s))`. It also has adapter packages, `@fast-check/vitest` and `@fast-check/jest`.

Source: https://github.com/dubzzz/fast-check

## Mutation testing

StrykerJS is maintained. Set it up with `npm init stryker@latest` and run it with `npx stryker run`. It has dedicated runners for Jest, Vitest, Mocha, Jasmine, Karma, Cucumber and Tap. There is no dedicated runner for `node:test`. Use the `command` runner instead (`commandRunner: { command: 'node --test' }`): it works, but it reruns every test for every mutant, so it is slow.

Source: https://stryker-mutator.io/docs/stryker-js/getting-started/, https://stryker-mutator.io/docs/stryker-js/configuration/

## Red flags in a diff

Any of these inside a fix is suspect:

- Skip markers: `test.skip`, `it.skip`, `describe.skip`, `xit`, `xtest`, `xdescribe`, `test.todo`, Vitest's `test.skipIf` and `test.runIf`, a `node:test` option `{ skip: true }` or `{ todo: true }`, or a `t.skip()` call.
- Inverted tests: `test.fails` in Vitest and `test.failing` in Jest. These pass when the body throws.
- Focus markers: `.only`, `fit`, `fdescribe`, and `{ only: true }` together with `--test-only` in `node:test`. Also Vitest `--allowOnly`, which turns off the CI guard against `.only`.
- Snapshot rewrites: `jest -u` or `--updateSnapshot`, `vitest -u` or `--update`, `node --test --test-update-snapshots`. So is any `.snap` or `.snapshot` file that changes in the same commit as the code.
- Filters that hide tests: `--passWithNoTests`, `--testPathIgnorePatterns`, `--test-skip-pattern`, `--test-name-pattern`.
- Runner config: `jest.config.*`, the `"jest"` key or the `"test"` script in `package.json`, `vitest.config.*`, the `test` block in `vite.config.*`, `vitest.workspace.*` (deprecated since Vitest 3.2 in favour of `projects`), setup files, and `stryker.config.*`.

Source: https://jestjs.io/docs/api, https://vitest.dev/api/, https://vitest.dev/guide/projects, https://nodejs.org/api/test.html
