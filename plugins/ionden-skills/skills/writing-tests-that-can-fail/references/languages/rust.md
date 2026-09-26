# Rust (cargo test)

This file maps the skill's rules onto the tools that Rust projects use with `cargo test`.

## Runner

- `cargo test` runs the libtest harness over unit tests (`#[cfg(test)] mod tests`), integration tests in `tests/` and doctests.
- To run one integration test file, use `cargo test --test <file_stem>`. To narrow to a single test in it, use `cargo test --test <file_stem> -- <module::test_name>`. Unit tests are filtered by name with `cargo test <name_filter>`.
- cargo-nextest is a common alternative runner. Its command is `cargo nextest run`, and it reads `.config/nextest.toml` at the workspace root.

Source: https://doc.rust-lang.org/cargo/commands/cargo-test.html

## Writing a fake

Put a trait at the adapter boundary and inject it through a generic parameter or `&dyn Trait`. The fake is a plain struct that implements the same trait, and the test asserts on the state the fake holds or the value the unit returns.

```rust
pub trait Clock { fn now(&self) -> u64; }
pub struct FixedClock(pub u64);
impl Clock for FixedClock { fn now(&self) -> u64 { self.0 } }

#[derive(Default)]
pub struct InMemoryUserStore { pub users: std::cell::RefCell<Vec<String>> }
impl UserStore for InMemoryUserStore {
    fn save(&self, name: &str) { self.users.borrow_mut().push(name.to_owned()); }
}
```

Source: https://doc.rust-lang.org/book/ch10-02-traits.html

## Mocking library (last resort)

mockall generates `Mock<Trait>` types from `#[automock]` or `mock!`. The skill allows it only to verify an outgoing side effect that can't be avoided and that no fake can observe. In review, these calls on a mock are interaction assertions: `expect_<method>()`, `.times(n)`, `.with(predicate)`, `.in_sequence(&mut seq)` and `.checkpoint()`. If one of them carries the main check of a test, the test fails keep-or-kill item 4. `.returning()` and `.return_const()` alone only make the mock act as a stub.

Source: https://docs.rs/mockall/latest/mockall/

## Property-based testing

proptest provides the `proptest!` macro with `prop_assert!` and `prop_assert_eq!`. It is maintained, though the repository describes it as close to feature-complete and in passive maintenance.

Source: https://github.com/proptest-rs/proptest

## Mutation testing

cargo-mutants is maintained. Install it with `cargo install --locked cargo-mutants` and run `cargo mutants` in the crate. `--file <path>` limits the run to one file and `--in-diff <patch>` to the changed code. In a diff, a new `#[mutants::skip]` or a new exclusion in `.cargo/mutants.toml` hides surviving mutants.

Source: https://mutants.rs/

## Red flags in a diff

- Skip and disable markers: `#[ignore]` or `#[ignore = "..."]` on a test that ran before, a removed `#[test]` attribute, a test gated off with `#[cfg(any())]` or `#[cfg(not(test))]`, and an early `return;` placed before the asserts.
- A newly added `#[should_panic]`, or one whose `expected = "..."` got looser. Any panic now passes the test, including one from the bug.
- Focus-only markers: Rust has no `.only`. Watch instead for CI scripts that gain a name filter (`cargo test <filter>`, `-- --exact`, `--skip <name>`) or a nextest `-E` filterset.
- Snapshot updates: `cargo insta accept`, `cargo insta test --accept`, `INSTA_UPDATE=always`, `INSTA_FORCE_PASS=1`, bulk rewrites of `.snap` files, and `UPDATE_EXPECT=1` with expect-test.
- Runner config: `.config/nextest.toml` (look for `retries`, `default-filter` and per-test overrides), `harness = false` or `test = false` on a `[[test]]` or `[lib]` target in `Cargo.toml`, `.cargo/config.toml`, `build.rs`, and CI scripts that call the tests.

Sources: https://doc.rust-lang.org/reference/attributes/testing.html, https://insta.rs/docs/advanced/, https://docs.rs/expect-test/latest/expect_test/, https://nexte.st/docs/configuration/
