# Go (testing package)

This file maps the skill's rules onto the Go toolchain: `go test`, the `testing` package and the common third-party test libraries.

## Runner

`go test` compiles each package together with its `*_test.go` files and runs every `TestXxx(t *testing.T)` function. Go runs tests per package, not per file. To run one test, pass `-run` a regular expression: `go test ./internal/users -run '^TestSave$' -count=1`. The `-count=1` flag skips the result cache. You can also pass a list of `.go` files from one directory (`go test store.go store_test.go`), and Go builds them as a single package, but you have to name every file the test needs.
Source: https://pkg.go.dev/cmd/go/internal/test

## Writing a fake

Go interfaces are satisfied implicitly. Define a small interface at the point of use, then write a struct in the test package that implements it with a map or a fixed value. A compile-time assertion keeps the fake in step with the interface.

```go
type InMemoryUserStore struct{ users map[string]User }

var _ UserStore = (*InMemoryUserStore)(nil)

func (s *InMemoryUserStore) Save(u User) error { s.users[u.ID] = u; return nil }

func (s *InMemoryUserStore) Get(id string) (User, bool) {
	u, ok := s.users[id]
	return u, ok
}
```

Assert on what ends up in `users`, or on what `Get` returns. Don't count the calls to `Save`. For time, inject a `Clock` interface and pass in `FixedClock{T: time.Date(...)}` instead of calling `time.Now()`.
Source: https://go.dev/ref/spec#Interface_types

## Mocking library (last resort)

The two common libraries are `go.uber.org/mock` (gomock with `mockgen`) and the `mock` package in `github.com/stretchr/testify`. The original `golang/mock` is no longer maintained by Google, and Uber's fork took its place. Use either one only to verify an outgoing side effect you can't avoid and can't observe through a fake. When you review, look for these interaction assertions: in gomock, `EXPECT()`, `.Times(n)`, `.MinTimes(n)`, `.AnyTimes()`, `gomock.InOrder(...)` and `.After(...)`; in testify, `.On(...).Return(...)`, `AssertCalled`, `AssertNotCalled`, `AssertNumberOfCalls`, `AssertExpectations`, `.Once()` and `.Times(n)`. If one of these is a test's main assertion, the test checks calls, not behaviour.
Source: https://github.com/uber-go/mock
Source: https://pkg.go.dev/github.com/stretchr/testify/mock

## Property-based testing

`pgregory.net/rapid` is the maintained library (`rapid.Check(t, func(t *rapid.T) {...})`, generators through `.Draw`, automatic shrinking, state-machine tests). The standard `testing/quick` package is frozen and takes no new features. `leanovate/gopter` has had no release since 2020. For inputs that should never crash the code, the built-in fuzzing works too (`func FuzzXxx(f *testing.F)`, run with `go test -fuzz`).
Source: https://github.com/flyingmutant/rapid
Source: https://pkg.go.dev/testing/quick

## Mutation testing

Gremlins is maintained and still at 0.x, so its flags can change between minor releases. Run `gremlins unleash` in a module directory. The `avito-tech/go-mutesting` fork is also maintained: `go-mutesting ./...`.
Source: https://github.com/go-gremlins/gremlins
Source: https://github.com/avito-tech/go-mutesting

## Red flags in a diff

- Skips: new `t.Skip(...)`, `t.Skipf(...)` or `t.SkipNow()`; `if testing.Short() { t.Skip() }` added to a test that used to run; a build constraint (`//go:build ignore`, or a custom tag) added at the top of a `_test.go` file; `TestXxx` renamed to `testXxx` or `XTestXxx`, which stops `go test` from picking it up; a `_test.go` file renamed so it drops the suffix.
- Focus: Go has no `.only`. The same effect comes from a `-run` or `-skip` pattern added to a Makefile, CI workflow or test script, which narrows the suite quietly.
- Snapshot and golden updates: `UPDATE_SNAPS=true` (or `always`, `clean`) for go-snaps; a custom `-update` flag for golden files (a common convention, not a toolchain flag) passed in a script or defaulted to true; regenerated files under `testdata/` or `__snapshots__/` in the same change as a fix.
- Runner config: Go has no runner config file, so watch `TestMain(m *testing.M)`. A `TestMain` that returns without calling `m.Run()`, or calls `os.Exit(0)` instead of passing on `m.Run()`'s exit code, turns every failure into a pass. Also watch changes to Makefile test targets, CI test steps, `-failfast` and `-count`, and generated mocks (`mockgen` output) edited by hand.
Source: https://pkg.go.dev/testing
Source: https://github.com/gkampitakis/go-snaps
