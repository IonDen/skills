# Test smell catalog

Named smells, why each one hurts, and a before/after fix in pseudo-code. Load this when reviewing a suite or when a test feels wrong but you can't say why.

## Testing the mock
The assertion checks what the mock was told to do, so it passes whatever the code does.
```
BEFORE  store = MOCK(returns = user)
        expect store.load(1) == user          # asserts the mock's canned answer
AFTER   store = InMemoryUserStore([user])
        expect Profiles(store).display_name(1) == "Ada L."
```

## Incomplete mock
The double implements only the methods today's code path calls, and returns shapes the real thing never returns. The test passes until the code touches one more field.
```
BEFORE  api = MOCK(get_user = {"id": 1})      # real response also has "email", "status"
AFTER   a fake built from a recorded real response, or the real adapter's own
        in-memory implementation, with the full shape
```

## Test-only method in production code
A method added to a production class so a test can reach inside (`reset_for_tests`, `_set_state`). It ships, and callers start using it.
```
BEFORE  cache.clear_for_tests()
AFTER   build a fresh Cache per test, or give the test its own instance through
        the constructor
```

## Mocking without understanding the dependency
The mock replaces a collaborator whose side effects the test needs (a write the next step reads, an ordering guarantee), so the test passes against behaviour that can't happen.
```
BEFORE  mock the queue, then assert the consumer processed the message
AFTER   use an in-memory queue with the same ordering and delivery rules
```

## Tautological test
The test recomputes the answer the way the code does, so it can never disagree with it.
```
BEFORE  expect total(items) == sum(item.price for item in items)
AFTER   expect total([2, 3]) == 5
        expect total([]) == 0
```

## Oracle from the implementation's constants
The expected value is built from the code's own constants or helpers, so a wrong constant moves the test with it.
```
BEFORE  expect price(member_item) == MEMBER_PRICE
AFTER   expect price(member_item) == 8.50       # the value the spec states
```

## Assertion-free test
It runs code and asserts nothing. Coverage goes up; no bug is caught.
```
BEFORE  parse_config("a=1")
AFTER   expect parse_config("a=1") == {"a": "1"}
```

## Mocked unit under test
The thing being tested is itself a double, so nothing real runs.
```
BEFORE  svc = MOCK(BookingService); svc.book.returns("ok")
        expect svc.book(b) == "ok"
AFTER   expect BookingService(InMemoryBookings()).book(b).status == "booked"
```

## Assert-on-calls
The test checks that a collaborator was called instead of checking the result.
```
BEFORE  repo = MOCK(); BookingService(repo).book(b)
        expect repo.save.called_once()
AFTER   repo = InMemoryBookings(); BookingService(repo).book(b)
        expect repo.get(b.id).status == "booked"
```

## Mystery guest
The test depends on a file or service it doesn't show, so it isn't self-contained and breaks on another machine.
```
BEFORE  expect load("/home/me/data/sample.json").n == 3
AFTER   path = temp_dir / "s.json"; write(path, '{"n": 3}')
        expect load(path).n == 3
```

## Eager test
One test registers, logs in, updates and deletes. When it fails, you don't know which behaviour broke.
```
AFTER   one behaviour per test, named for what breaks: register_rejects_duplicate_email, ...
```

## Wrong oracle
A quality bound asserted where the inputs make it meaningless, for example a similarity threshold checked on a configuration it was never calibrated for.
```
BEFORE  expect similarity(fast_path, exact_path) >= 0.85   # at a setting where 0.85 can't hold
AFTER   expect mechanical correctness here (finite output, the fast path taken);
        assert the quality bound at the setting it was calibrated for
```

## Tolerance that can't fail, or can't pass
A numeric bound so wide nothing fails it, or so tight that legitimate noise fails it. Pick the smallest bound that passes on the correct code, measured, and say where it came from.

## A heavy test standing in for missing cheap ones
The logic has no unit tests because a slow, gated test "covers it", and that test doesn't run on every change. Extract the logic, test it cheaply, and gate only the part that really needs the resource.
