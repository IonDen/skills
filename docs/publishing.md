# Publish the plugin

Use this guide to build a release ZIP and publish it in OpenAI's shared ChatGPT/Codex directory. Publication needs a verified developer identity and OpenAI approval. A GitHub push does not update the skills in that directory.

## Build the ZIP

From the repository root, with Python 3.10 or later, PyYAML and pytest installed:

```bash
python3 scripts/validate_skills.py
python3 -m pytest tests -q
python3 scripts/build_plugin_zip.py --output /tmp/ionden-skills-0.8.4.zip
```

Choose a new output path for each build. The builder will not overwrite a file or write inside the plugin. It prints a SHA-256 checksum, which identifies the archive's exact contents.

The ZIP contains one folder, `ionden-skills/`, with the skills and their supporting files. It leaves out tests, evals, repository docs and local caches. It rejects links to other files, unexpected plugin entries and hidden supporting files before creating the archive.[^archive]

Inspect the ZIP before uploading. A local validation pass does not replace OpenAI's scans.

## Upload, review and publish

1. Open the [OpenAI Plugins portal](<https://platform.openai.com/plugins>). Select the organization and project that will own the plugin. You must be the organization owner or have Apps Management Write permission. Complete individual or business verification, then select that developer identity.
2. Select **Upload new or existing plugin** and upload the ZIP. The package includes the listing text, three starter prompts and both required icons.[^manifest]
3. Wait for the metadata and skill checks. Fix any required findings in the source files, rebuild the ZIP with a new output path, and upload it again.
4. Submit the draft for review and complete the policy attestations.
5. After approval, select **Publish plugin**. It can then appear in the shared directory.

See [OpenAI's submission guide](<https://developers.openai.com/plugins/deploy/submission>).

This plugin contains skills only. It has no MCP server, which is a connection to an external service. It does not need MCP review cases, a demo recording or domain verification. Website, support, privacy and terms URLs are optional for this submission type.[^requirements]

Keep credentials out of the ZIP. Enter any private reviewer access in the portal. Anthropic directory approval does not transfer to OpenAI.

## Check the installed plugin

Use a fresh conversation on each target surface. Try the three starter prompts with sample agent files, a sample `SKILL.md` and a sample test suite. Check follow-up requests and unrelated requests too. See [Connect and test](<https://developers.openai.com/plugins/deploy/connect-chatgpt>).

The two optimizer skills need file access and a shell with Python. A surface without those tools cannot complete their scripted workflows. An upload, local install or safety scan alone does not prove that they work in ChatGPT.

## Release checklist

- Run the validator and full test suite.
- Update both plugin versions, the changelog and any listing text affected by the change.
- Build the ZIP from the release contents and record its checksum.
- Extract it and check that all three skills and their scripts and assets are present.
- Check Codex and Claude installs with fresh settings folders, separate from your normal configuration.
- Upload the complete new ZIP to the **existing** OpenAI plugin. Resolve findings, submit and publish the approved version.
- Check the published install in both ChatGPT and Codex before announcing availability.

## Using the API

The [Agents API](<https://developers.openai.com/api/docs/guides/agents-api/tools/plugins>) can load plugin folders or ZIPs into an agent session. That makes the plugin available in that session. Publishing a directory listing uses the portal above.

[^archive]: Entry order, timestamps and permission bits are normalized. The same source contents and executable flags produce identical bytes with the same Python/zlib toolchain. Executable files remain executable. Supporting-folder bytecode and caches are excluded; symlinks are rejected. The builder archives only `plugins/ionden-skills/`, so the repository's marketplace catalog stays outside the ZIP.

[^manifest]: Listing text is the root `interface` in `.codex-plugin/plugin.json`. This supported compatibility format lets the existing Claude layout stay in place; both manifests carry the same plugin version. Logo and composer icon use the existing 128x128 SVG. See [Plugin packaging](<https://developers.openai.com/plugins/build/plugins>).

[^requirements]: Skills-only uploads still need passing skill scans and complete listing metadata. The package provides project, support and privacy links. See the [submission requirements](<https://developers.openai.com/plugins/deploy/submission-errors>) and [Claude plugin submissions](<https://developers.openai.com/plugins/guides/submit-claude-plugin>).
