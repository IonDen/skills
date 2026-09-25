# C# (.NET: xUnit, NUnit, MSTest)

This file shows how the skill's rules map onto the .NET test runners, fakes, mock libraries, property and mutation tools, and the diff markers a reviewer should question.

## Runner

All three frameworks run through `dotnet test`. .NET selects tests by name, not by file, so to run one test class (usually one file), filter on its fully qualified name: `dotnet test --filter "FullyQualifiedName~MyNamespace.PriceRulesTests"`. For one method, use `FullyQualifiedName=MyNamespace.PriceRulesTests.Rejects_negative_quantity`. MSTest also accepts `ClassName=`, and NUnit accepts `Name~`.
Source: https://learn.microsoft.com/en-us/dotnet/core/testing/selective-unit-tests

## Writing a fake

Put an owned interface in front of the slow resource and give the test a small in-memory class that implements it. For time, depend on `System.TimeProvider`, which is built into .NET 8 and later. In tests, pass `FakeTimeProvider` from the `Microsoft.Extensions.TimeProvider.Testing` package, or a subclass that overrides `GetUtcNow()`.

```csharp
public interface IUserStore { User? Find(string id); void Save(User user); }

public sealed class InMemoryUserStore : IUserStore
{
    public Dictionary<string, User> Saved { get; } = new();
    public User? Find(string id) => Saved.GetValueOrDefault(id);
    public void Save(User user) => Saved[user.Id] = user;
}
```

Assert on `store.Saved`, the state a caller can observe, and not on whether `Save` was called.
Source: https://learn.microsoft.com/en-us/dotnet/standard/datetime/timeprovider-overview

## Mocking library (last resort)

Moq and NSubstitute are both maintained. Use one only to verify an unavoidable outgoing side effect at a boundary you don't own, such as a message published to an external bus. Never use one on the unit under test or on your own deterministic collaborators. These are the interaction assertions to look for in review:
- Moq: `mock.Verify(...)`, `Times.Once()`, `Times.Never()`, `VerifyAll()`, `VerifyNoOtherCalls()`.
- NSubstitute: `sub.Received()`, `sub.Received(2)`, `sub.DidNotReceive()`, `Received.InOrder(...)`.

If one of these is the main assertion in a test of in-process logic, rewrite the test to assert returned values or state held in a fake.
Source: https://github.com/devlooped/moq
Source: https://github.com/nsubstitute/NSubstitute

## Property-based testing

FsCheck is maintained and usable from C#. It has runner integrations in `FsCheck.Xunit`, `FsCheck.Xunit.v3` and `FsCheck.NUnit`, and a `[Property]` attribute. CsCheck is a maintained C#-first alternative whose `Gen.*.Sample(...)` shrinks failures and prints a seed for reproducing them.
Source: https://github.com/fscheck/FsCheck
Source: https://github.com/AnthonyLloyd/CsCheck

## Mutation testing

Stryker.NET is maintained. Install it with `dotnet tool install -g dotnet-stryker`, or locally with `dotnet new tool-manifest` and then `dotnet tool install dotnet-stryker`. Run `dotnet stryker` from the test project directory. It reads its settings from `stryker-config.json`, so treat a lowered threshold there like any other runner-config change.
Source: https://stryker-mutator.io/docs/stryker-net/getting-started/

## Red flags in a diff

Skip and disable markers:
- xUnit: `[Fact(Skip = "...")]`, `[Theory(Skip = ...)]`, `SkipWhen`/`SkipUnless` properties, `Assert.Skip`, `Assert.SkipWhen`, `Assert.SkipUnless`.
- NUnit: `[Ignore("...")]` (including `Until = ...`), `[Explicit]`, `Assert.Ignore`, `Assert.Inconclusive`, `Assume.That`.
- MSTest: `[Ignore]`, `[OSCondition]`, `[CICondition]`, `Assert.Inconclusive`. Inconclusive results show as skipped unless `MapInconclusiveToFailed` is true.

Focus-only markers: there is no `.only` in .NET. The same effect comes from a filter that narrows the run:
- `--filter` added to a CI script;
- `<TestCaseFilter>` in a `.runsettings` file;
- xUnit v3 `Explicit = true` on a test that used to run.

Snapshot updates (Verify library):
- a `.received.` file renamed or copied over a `.verified.` file;
- `AutoVerify()` added to a test, a settings object or `VerifierSettings`;
- bulk acceptance through the Verify.Terminal dotnet tool.

Runner config:
- `*.runsettings`, including `TestCaseFilter`, `TreatNoTestsAsError`, the `MSTest` adapter section and `-- Key=Value` overrides on the command line;
- `RunSettingsFilePath` in a project file or `Directory.Build.props`;
- `xunit.runner.json`;
- `stryker-config.json`.

Any of these changing inside a fix is suspect.
Source: https://xunit.net/docs/getting-started/v3/whats-new
Source: https://docs.nunit.org/articles/nunit/writing-tests/attributes/ignore.html
Source: https://learn.microsoft.com/en-us/dotnet/core/testing/unit-testing-mstest-writing-tests
Source: https://learn.microsoft.com/en-us/visualstudio/test/configure-unit-tests-by-using-a-dot-runsettings-file
Source: https://github.com/VerifyTests/Verify/blob/main/docs/autoverify.md
