// Package infrared configures the baseplate-celery repository.
//
// Run `make generate` from the repository root to regenerate files defined by this config.
package infrared

import (
	"github.snooguts.net/reddit-go/infrared-domain-aitools/codereview"
	"github.snooguts.net/reddit-go/infrared-domain-droneci/droneci"
	"github.snooguts.net/reddit-go/infrared-domain-droneci/droneci/legacydrone"
	"github.snooguts.net/reddit-go/infrared-domain-github/github"
	"github.snooguts.net/reddit-go/infrared-domain-github/github/codelifecycle"
	"github.snooguts.net/reddit-go/infrared-domain-python/python"
	"github.snooguts.net/reddit-go/infrared-domain-renovate/renovate"
	"github.snooguts.net/reddit-go/infrared-generator/domains/infrared/infraredci"
	"github.snooguts.net/reddit-go/infrared-generator/infragen"
)

// teamOwner owns the repository.
const teamOwner = "@reddit/ads-campaign-management"

// Generate is a special function that will be called automatically by infrared-generator.
func Generate(gen *infragen.Generator) {
	github.NewRepo(gen,
		github.WithTeam("team/111/campaign-management"), // https://service-catalog.snooguts.net/team/111/campaign-management
	)
	github.RedditOwnersFor(gen).AddOwners(github.RootOwners(teamOwner))
	codelifecycle.For(gen)

	renovate.NewConfig(gen,
		// Published library: widen dependency ranges instead of raising consumers' minimums.
		python.RenovateLibraryConfig(),
		renovate.WithIgnorePaths(
			// The minimum supported Python version, by design.
			".python-version",
		),
	)

	// Server-side PyStyle reviewer persona, posting inline review comments.
	codereview.For(gen).
		SetReviewMode(codereview.ModeAutoCreate).
		SetOutputMode(codereview.OutputModeInline).
		SetPersonaEnabled("PyStyle", true)

	github.GitIgnoreForRoot(gen).IgnorePatterns(
		".DS_Store",
		".idea/",
		".vscode/",
		// uv virtual environments; CI steps use .venv-<step>/.
		".venv/",
		".venv-*/",
		// direnv state: input fingerprint that lets .envrc skip `make scaffold`.
		".direnv/",
		// Build output; CI steps use dist-py<version>/.
		"build/",
		"dist/",
		"dist-py*/",
		"*.egg-info/",
		// Python and tool caches.
		"__pycache__/",
		"*.py[cod]",
		".pytest_cache/",
		".ruff_cache/",
		// Coverage reports.
		".coverage",
		".coverage.*",
		"coverage.lcov",
		"htmlcov/",
	)

	generateMakefile(gen) // See makefile.go.

	// Test, lint, and publish pipelines live in legacydrone.yaml.
	legacydrone.Import(gen, "infrared/legacydrone.yaml")
	droneci.For(gen).SetDefaultBranch("main")
	droneci.For(gen).Add(
		infraredci.NewCodegenCheckPipeline("Infrared v2"),
	)
}
