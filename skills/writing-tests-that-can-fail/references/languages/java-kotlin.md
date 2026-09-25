# Java and Kotlin (JUnit 5, Kotest)

This file maps the skill's rules onto the test tools for Java and Kotlin on the JVM.

## Runner

JUnit Jupiter is the standard runner for Java. The current platform release is JUnit 6, which keeps the Jupiter API that JUnit 5 introduced. Kotest runs on the same JUnit Platform through `kotest-runner-junit5`, with `useJUnitPlatform()` set on the Gradle test task. To run one test class, use `./gradlew test --tests com.example.PriceRulesTest` with Gradle, or `mvn -Dtest=PriceRulesTest test` with Maven.

Source: https://docs.junit.org/current/user-guide/ https://kotest.io/docs/framework/project-setup.html https://docs.gradle.org/current/userguide/java_testing.html https://maven.apache.org/surefire/maven-surefire-plugin/examples/single-test.html

## Writing a fake

Make the code depend on an interface you own, and give the test a small class that keeps its state in a map. Kotlin does the same with an `interface` and a `class`, and neither language needs a library for it. For time, inject `java.time.Clock` and pass `Clock.fixed(...)`. The JDK documents the fixed clock for exactly this use.

```java
interface UserStore { void save(User u); Optional<User> byId(String id); }

final class InMemoryUserStore implements UserStore {
    final Map<String, User> rows = new HashMap<>();
    public void save(User u) { rows.put(u.id(), u); }
    public Optional<User> byId(String id) { return Optional.ofNullable(rows.get(id)); }
}
// Clock clock = Clock.fixed(Instant.parse("2026-03-29T01:30:00Z"), ZoneOffset.UTC);
```

Assert on what `byId` returns or on what is in `rows`, not on which methods were called.

Source: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html

## Mocking library (last resort)

The usual choices are Mockito (5.x) for Java and MockK for Kotlin. Use one only to confirm an outgoing side effect that no fake can observe, such as a call to a third-party service you cannot run. In review, these calls mark interaction assertions. For Mockito: `verify(...)`, `times`, `never`, `atLeast`, `inOrder`, `verifyNoMoreInteractions` and `verifyNoInteractions`. For MockK: `verify`, `coVerify`, `verifyAll`, `verifyOrder`, `verifySequence`, `confirmVerified` and `wasNot Called`. A test whose main assertion is one of these, or one that calls `mock()` on the class under test, fails the keep-or-kill checklist.

Source: https://www.javadoc.io/static/org.mockito/mockito-core/5.24.0/org.mockito/org/mockito/Mockito.html https://mockk.io/

## Property-based testing

Kotest property (`io.kotest:kotest-property`) is maintained and works without the Kotest runner. Use `checkAll` for a block of assertions and `forAll` for a function that returns a boolean. The main Java option is jqwik, but its repository says it is in pure maintenance mode with no new features. From 1.10 on, its user guide also says it is not meant to be used by AI coding agents, so an agent should not add it. For Java, write the property as a loop over hand-picked spec cases, or use Kotest property from a Kotlin test source set.

Source: https://kotest.io/docs/proptest/property-test-functions.html https://github.com/jqwik-team/jqwik

## Mutation testing

PIT (pitest) is maintained. With Maven, run `mvn test-compile org.pitest:pitest-maven:mutationCoverage`, which writes an HTML report under `target/pit-reports/`. With Gradle, apply the plugin `info.solidsoft.pitest`, set `junit5PluginVersion` in the `pitest { }` block so it runs JUnit Platform tests, then run `./gradlew pitest`.

Source: https://pitest.org/quickstart/maven/ https://github.com/hcoles/pitest https://github.com/szpak/gradle-pitest-plugin

## Red flags in a diff

- JUnit skips: `@Disabled`, `@DisabledIf`/`@EnabledIf`, the OS, JRE, native-image, system-property and environment-variable conditions (`@DisabledOnOs`, `@EnabledOnJre`, `@EnabledIfSystemProperty` and their siblings), and a new `Assumptions.assumeTrue` or `assumingThat` inside a test. A failed assumption aborts the test instead of failing it.
- Kotest skips: `x` variants (`xtest`, `xit`, `xdescribe`, `xcontext`, `xshould`, `xgiven`), a `!` prefix on a test name, `config(enabled = false)`, `enabledIf` and `enabledOrReasonIf`.
- Focus: the Kotest `f:` prefix on a top-level test name runs only that test. JUnit has no focus marker, so look instead for a new `filter { }` or `--tests` pattern that narrows the suite.
- Snapshot updates with Selfie: `selfie=overwrite` or `SELFIE=overwrite`, the `//selfieonce` or `//SELFIEWRITE` comments, a `_TODO` suffix on a snapshot call, and any committed snapshot change in the same diff as a fix.
- Runner config: `junit-platform.properties`; a Kotest `ProjectConfig` subclass of `AbstractProjectConfig`, or the `kotest.bang.disable` property; the Gradle `test { }` block (`ignoreFailures`, filters); and Surefire settings in `pom.xml` or on the command line (`skipTests`, `maven.test.skip`, `testFailureIgnore` or `maven.test.failure.ignore`, `excludes`, `skipAfterFailureCount`).

Source: https://docs.junit.org/current/writing-tests/conditional-test-execution.html https://docs.junit.org/current/writing-tests/assumptions.html https://kotest.io/docs/framework/conditional/conditional-tests-with-focus-and-bang.html https://kotest.io/docs/framework/conditional/conditional-tests-with-x-methods.html https://kotest.io/docs/framework/conditional/enabled-config-flag.html https://selfie.dev/jvm/get-started https://maven.apache.org/surefire/maven-surefire-plugin/test-mojo.html https://docs.junit.org/current/running-tests/configuration-parameters.html https://kotest.io/docs/framework/project-config.html
