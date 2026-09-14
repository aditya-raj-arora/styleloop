# EC2 backend deploy automation — one-time setup

`.github/workflows/deploy.yml` SSHes into the EC2 box and runs the same
steps that were previously done by hand after every backend-touching PR:
`git pull` → `pip install` → `alembic upgrade head` →
`systemctl restart styleloop-api styleloop-worker`. It fires automatically
once `CI` finishes successfully on `main` (see the workflow's `workflow_run`
trigger) — nothing to run manually once this is set up.

It needs three repository secrets it doesn't have yet. This is a one-time
setup; skip it and the workflow just fails clearly (SSH auth error) without
touching the EC2 box.

## 1. Create a dedicated deploy key

Don't reuse your personal SSH key. On your own machine:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ./styleloop-deploy-key -N ""
```

Add the **public** half to the EC2 box's `~/.ssh/authorized_keys` for the
user the workflow will log in as (the same user you've been deploying as
manually):

```bash
ssh-copy-id -i ./styleloop-deploy-key.pub ubuntu@<your-ec2-ip-or-domain>
# or, if ssh-copy-id isn't available: paste the .pub file's contents onto
# a new line in ~/.ssh/authorized_keys on the box yourself.
```

## 2. Add the repository secrets

Via the GitHub UI: **Settings → Secrets and variables → Actions → New
repository secret**, or via `gh`:

```bash
gh secret set EC2_HOST --body "15.252.168.183"        # or your EC2 domain
gh secret set EC2_USER --body "ubuntu"                 # the deploy user
gh secret set EC2_SSH_KEY < ./styleloop-deploy-key      # the PRIVATE key
```

Then delete the local key files (`styleloop-deploy-key` /
`styleloop-deploy-key.pub`) — they're not needed again once the secret is
set.

## 3. Verify the paths in `deploy.yml`

`DEPLOY_PATH` and `VENV_PATH` in the workflow reflect the manual runbook
used for every deploy up to this point, but weren't checked against the
box's actual filesystem when this automation was written. If the first run
fails on `cd`/`source`, adjust those two `env:` values to match reality and
push again.

## 4. First run

Merge a PR to `main` (or re-run the `CI` workflow from the Actions tab) and
watch the **Deploy backend (EC2)** run in the Actions tab. It restarts the
API + worker and then polls `/health` for up to 50s before failing loudly if
the service didn't come back.

## Rolling back a bad deploy

The workflow doesn't do this automatically. Manually, on the box:

```bash
cd ~/styleloop && git log --oneline -5   # find the last-good commit
git checkout <that-sha>
sudo systemctl restart styleloop-api styleloop-worker
```
