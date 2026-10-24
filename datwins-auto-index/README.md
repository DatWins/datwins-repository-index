# DatWins automatic repository index

This project builds a searchable `index.html` from the current public repositories in the `DatWins` GitHub account. If a Netlify personal access token is configured, it also reads the Netlify sites visible to that token and maps them to their connected repositories.

## What updates automatically?

- GitHub repository additions, deletions, names, archive status, homepage metadata, and GitHub Pages enabled status are re-read from GitHub each run.
- Netlify sites and repository connections are re-read when `NETLIFY_AUTH_TOKEN` is configured.
- The workflow runs daily and can also be started manually.
- The generated index is committed to this repository only when its contents change.

The index is a snapshot between runs. A repository you delete should disappear at the next successful run; the scheduled run is daily. It will not update instantly at the exact moment you delete a repository.

## Setup (one time)

1. Create a new repository on GitHub named **`datwins-repository-index`**. Make it **Public** if you want to publish the index using GitHub Pages. Do not initialize it with a README or other files.
2. Download and unzip this starter package.
3. Upload the contents of the `datwins-auto-index` folder to the root of the new repository. Ensure the `.github/workflows/update-index.yml` file is included. GitHub's upload page sometimes hides dot-folders; if that happens, use GitHub Desktop or Git to upload the folder.
4. In the repository, open **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**, then save.
5. (Recommended for Netlify links) In Netlify, create a personal access token. In GitHub, open the new repository's **Settings → Secrets and variables → Actions → New repository secret**. Name it exactly `NETLIFY_AUTH_TOKEN` and paste the token as the secret value. Never put the token in `index.html`, in this README, or in a public commit. The token should have only the access needed to read your sites; if Netlify offers token scopes, choose the least-privileged read access that works.
6. Open the repository's **Actions** tab. If prompted, enable workflows. Select **Refresh repository index** and click **Run workflow**.
7. When the workflow finishes successfully, `index.html` will be refreshed and committed.
8. To publish the index as a website, open **Settings → Pages**. Choose **Deploy from a branch**, select branch **`main`** and folder **`/(root)`**, then save. GitHub will show the public website URL when deployment is ready. For a repository named `datwins-repository-index`, the URL is usually `https://datwins.github.io/datwins-repository-index/`.

## Manual refresh

Open **Actions → Refresh repository index → Run workflow**. You can do this after a cleanup instead of waiting for the daily run.

## Netlify token is optional

Without `NETLIFY_AUTH_TOKEN`, the workflow still updates public GitHub repository and GitHub Pages metadata, but it cannot reliably refresh Netlify site connections. With the token, it includes the Netlify sites accessible to that token; if your account/team has more than one site scope, confirm the token can see the intended sites.

## Notes

- The workflow lists **public** GitHub repositories for `DatWins`. It does not enumerate private repositories.
- The GitHub Pages URL is marked as likely when Pages is enabled but GitHub doesn't provide a homepage URL; verify it before relying on it.
- “Neither hosting method identified” does not prove a repository has no live website.
- The generated page uses only public website and repository metadata. The Netlify token is used in the workflow environment and is not written into the generated HTML.
