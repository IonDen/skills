# Swift (XCTest, Swift Testing)

This file maps the skill's rules onto the Swift toolchain: SwiftPM, Xcode, XCTest and Swift Testing.

## Runner

- Swift Testing (`@Test`, `#expect`) and XCTest (`XCTestCase`, `XCTAssert*`) both run under `swift test` in a package and under `xcodebuild test` in an Xcode project.
- Neither runner selects tests by file, so filter by the suite the file declares: `swift test --filter MyTests.UserStoreTests` (a regex over `<target>.<suite>` or `<target>.<suite>/<test>`), or `xcodebuild test -scheme App -only-testing MyTests/UserStoreTests`.

Source: https://docs.swift.org/latest/documentation/packagemanagerdocs/swifttest/ and https://developer.apple.com/documentation/xcode/running-tests-and-interpreting-results

## Writing a fake

Swift has no runtime mocking. The seam is a protocol that production code receives through its initializer. The fake conforms to that protocol and keeps its state in memory, and the test asserts on that state or on what the unit returns. Value types and pure functions stay real.

```swift
protocol UserStore {
    func save(_ user: User) throws
    func find(id: String) -> User?
}

final class InMemoryUserStore: UserStore {
    private(set) var users: [String: User] = [:]
    func save(_ user: User) throws { users[user.id] = user }
    func find(id: String) -> User? { users[id] }
}
```

Source: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/protocols/

## Mocking library (last resort)

- Swift mocks are generated code. Mockolo generates a mock for each protocol annotated `/// @mockable`, and tests check interactions through `fooCallCount` and `fooArgValues` properties. Cuckoo generates `Mock*` classes that tests check with `verify(mock).method(...)` and `verify(mock, times(n))`.
- Use one only to verify an unavoidable outgoing side effect at a boundary you don't own. When `verify(`, `*CallCount` or `*ArgValues` is the main assertion, the test is an interaction test. Assert the state or output instead.
- Mockingbird has had no commits since March 2024, so treat it as unmaintained.

Source: https://github.com/uber/mockolo and https://github.com/Brightify/Cuckoo

## Property-based testing

- PropertyBased (`swift-property-based`) runs inside Swift Testing: `await propertyCheck(input: Gen.int(in: 0...100)) { n in #expect(...) }`. It shrinks failing inputs and can pin a fixed seed to replay a failure. It needs Swift 6.2; Swift 6.1 has limited support.
- SwiftCheck has had no commits since April 2022. Don't start new tests with it.

Source: https://github.com/x-sheep/swift-property-based

## Mutation testing

- Muter: `muter init` writes `muter.conf.yml` with the test command it will run, then `muter` starts the run. `muter --files-to-mutate Sources/Foo.swift` limits a run to the files you changed.
- The last tagged release is v16 (September 2023). Fixes still land on the main branch: detection of Swift Testing failures arrived in July 2026 and is newer than any tag.

Source: https://github.com/muter-mutation-testing/muter

## Red flags in a diff

- Skips: `throw XCTSkip(...)`, `try XCTSkipIf(...)`, `try XCTSkipUnless(...)`. Swift Testing traits `.disabled()`, `.disabled(if:)`, `.enabled(if:)`. A removed `@Test` attribute. An XCTest method renamed so its name no longer begins with `test`, which makes it stop running without any message.
- Expected failures that keep the suite green: `withKnownIssue { ... }` and `XCTExpectFailure(...)`.
- Focus: neither framework has an `.only`. Focus comes from the command line or from config: `--filter`, `--skip`, `-only-testing`, `-skip-testing`, and tests excluded from a test plan.
- Snapshots (swift-snapshot-testing): `record: .all` or `record: .failed` on `assertSnapshot`, `withSnapshotTesting(record:)`, the `.snapshots(record:)` suite trait, `SNAPSHOT_TESTING_RECORD` in the environment, the deprecated `isRecording = true`, and any rewritten file under `__Snapshots__`.
- Runner config: `Package.swift` (test targets, `exclude:`, `swiftSettings`), `*.xctestplan`, `*.xcscheme`, `muter.conf.yml`, and CI scripts that call `swift test` or `xcodebuild`.

Source: https://developer.apple.com/documentation/testing/enablinganddisabling, https://developer.apple.com/documentation/testing/known-issues, https://developer.apple.com/documentation/xctest/methods-for-skipping-tests, https://developer.apple.com/documentation/xctest/defining-test-cases-and-test-methods, https://developer.apple.com/documentation/xcode/organizing-tests-to-improve-feedback, https://github.com/pointfreeco/swift-snapshot-testing
