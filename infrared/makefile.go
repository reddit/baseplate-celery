package infrared

import (
	"github.snooguts.net/reddit-go/infrared-domain-make/pkg/makefile"
	"github.snooguts.net/reddit-go/infrared-generator/infragen"
)

// generateMakefile generates the root Makefile.
//
// Every uv command runs with `--exact --group dev`, so the venv always matches uv.lock. CI
// re-resolves uv.lock (UV_RESOLUTION=lowest-direct, `uv lock --upgrade`) to test the declared
// dependency ranges.
func generateMakefile(gen *infragen.Generator) {
	m := makefile.For(gen)
	m.RawHeader = "UV_RUN := uv run --exact --group dev\n" +
		"TEST_CMD := $(UV_RUN) pytest -n auto -ra\n"
	m.RawHeaderSource = "infrared/makefile.go"

	m.Generate().Description = "Regenerate Infrared v2 configs"

	m.TargetWithHelp("scaffold", "Idempotently set up the venv and git hooks").AddRawCommands(
		"uv sync --exact --group dev",
		"lefthook install",
	)

	m.TargetWithHelp("ruff", "Run ruff lint checks").AddRawCommands("$(UV_RUN) ruff check")
	m.TargetWithHelp("ruff-fix", "Apply ruff lint fixes").AddRawCommands("$(UV_RUN) ruff check --fix")
	m.TargetWithHelp("ruff-fmt", "Check ruff formatting").AddRawCommands("$(UV_RUN) ruff format --check")
	m.TargetWithHelp("ruff-fmt-fix", "Apply ruff formatting").AddRawCommands("$(UV_RUN) ruff format")
	m.TargetWithHelp("ty", "Run type checks").AddRawCommands("$(UV_RUN) ty check")
	m.TargetWithHelp("lint", "Run all lint checks (no edits)").AddPrerequisites("ruff", "ruff-fmt", "ty")
	m.TargetWithHelp("fmt", "Apply formatting and lint fixes (edits files)").AddPrerequisites("ruff-fmt-fix", "ruff-fix")

	// pytest exits 5 when no tests are collected.
	m.TargetWithHelp("test", "Run tests").AddRawCommands("$(TEST_CMD) --no-cov || [ $$? -eq 5 ]")
	m.TargetWithHelp("test-cov", "Run tests with coverage").AddRawCommands(
		"$(TEST_CMD) --cov --cov-report=term --cov-report=lcov --no-cov-on-fail || [ $$? -eq 5 ]",
	)

	// uv builds the sdist, then the wheel from the sdist, which checks the sdist is complete.
	m.TargetWithHelp("build", "Build the sdist and wheel into dist/").AddRawCommands("uv build")
}
