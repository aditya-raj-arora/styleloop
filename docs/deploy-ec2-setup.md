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

Don't reuse your personal SSH key. `ssh-keygen` ships with Windows 10+'s
built-in OpenSSH client, so this works the same in PowerShell as anywhere
else:

```powershell
ssh-keygen -t ed25519 -C "github-actions-deploy" -f .\styleloop-deploy-key -N '""'
```

(The `-N '""'` — empty passphrase, quoted so PowerShell doesn't eat it — is
required: the workflow can't be prompted for one.)

Add the **public** half to the EC2 box's `~/.ssh/authorized_keys` for the
user the workflow will log in as (the same user you've been deploying as
manually). `ssh-copy-id` isn't available on Windows, so append it over SSH
directly:

```powershell
Get-Content .\styleloop-deploy-key.pub | ssh ubuntu@<your-ec2-ip-or-domain> "cat >> ~/.ssh/authorized_keys"
```

(POSIX equivalent, if you're doing this from Mac/Linux/WSL instead:
`ssh-copy-id -i ./styleloop-deploy-key.pub ubuntu@<your-ec2-ip-or-domain>`.)

## 2. Add the repository secrets

Via the GitHub UI: **Settings → Secrets and variables → Actions → New
repository secret**, or via `gh`. Note `gh secret set`'s stdin form needs
`Get-Content | gh secret set NAME` in PowerShell — plain `<` redirection
isn't supported there (that's a POSIX shell thing):

```powershell
gh secret set EC2_HOST --body "15.252.168.183"        # or your EC2 domain
gh secret set EC2_USER --body "ubuntu"                 # the deploy user
Get-Content .\styleloop-deploy-key -Raw | gh secret set EC2_SSH_KEY   # the PRIVATE key
```

(POSIX equivalent: `gh secret set EC2_SSH_KEY < ./styleloop-deploy-key`.)

Then delete the local key files (`styleloop-deploy-key` /
`styleloop-deploy-key.pub`) — they're not needed again once the secret is
set:

```powershell
Remove-Item .\styleloop-deploy-key, .\styleloop-deploy-key.pub
```

## 3. Paths (already verified, nothing to do)

`DEPLOY_PATH`/`VENV_PATH` in the workflow are confirmed against
`/etc/systemd/system/styleloop-api.service`'s `WorkingDirectory`/
`ExecStart` on the real box (`/home/ubuntu/styleloop` /
`/home/ubuntu/styleloop/backend/.venv`) — not a guess. If you ever move the
repo or venv on the box, update these two `env:` values to match.

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
