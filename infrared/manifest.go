// Package infrared configures the baseplate-celery repository.
//
// Run `make generate` from the repository root to regenerate files defined by this config.
package infrared

import (
	"github.snooguts.net/reddit-go/infrared-domain-aitools/codereview"
	"github.snooguts.net/reddit-go/infrared-domain-github/github"
	"github.snooguts.net/reddit-go/infrared-domain-github/github/codelifecycle"
	"github.snooguts.net/reddit-go/infrared-domain-python/python"
	"github.snooguts.net/reddit-go/infrared-domain-renovate/renovate"
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
		// Added with the Drone pipelines.
		renovate.WithValidationPipeline(false),
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
		// uv virtual environments.
		".venv/",
		// Build output.
		"build/",
		"dist/",
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
}
