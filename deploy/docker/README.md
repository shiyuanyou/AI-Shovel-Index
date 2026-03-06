# Docker Deployment Kit

This directory packages the project for the optimized VPS path:
Ubuntu VPS + Docker Compose + systemd timer.

## Why This Variant

- app runtime is isolated inside an image
- upgrades become `pull/build -> switch tag -> restart timer`
- rollbacks become `switch tag back -> rerun`
- host persistence stays simple through bind-mounted `data/` and `output/`

## Files

- `compose.yml`: batch and smoke services
- `.env.example`: host paths and image tag settings
- `refresh_image.sh`: helper for `build` or `pull` image refresh plus smoke test
- `../../Dockerfile`: image build definition
- `../systemd/ai-shovel-index-docker.service`: systemd service template
- `../systemd/ai-shovel-index-docker.timer`: systemd timer template
- `../vps/bootstrap_ubuntu_docker_host.sh`: Ubuntu Docker host bootstrap

## Recommended Host Layout

- app dir: `/opt/ai-shovel-index`
- runtime data: `/opt/ai-shovel-index/runtime/data`
- runtime output: `/opt/ai-shovel-index/runtime/output`
- compose env file: `/opt/ai-shovel-index/deploy/docker/.env`

## 1. Bootstrap The Docker Host

Run this on the VPS as a sudo-capable user:

```bash
cd /path/to/repo/deploy/vps
chmod +x bootstrap_ubuntu_docker_host.sh
REPO_URL=git@github.com:YOUR_NAME/AI-Shovel-Index.git ./bootstrap_ubuntu_docker_host.sh
```

This script will:
- install Docker Engine and Compose plugin if missing
- create the `ai-shovel` system user
- clone or update the repo under `/opt/ai-shovel-index`
- create runtime bind-mount directories
- create `deploy/docker/.env`
- build the image
- run one smoke-test container

## 2. Configure Image Tagging

Default `.env` values look like this:

```env
AI_SHOVEL_IMAGE=ai-shovel-index
AI_SHOVEL_TAG=latest
AI_SHOVEL_DATA_DIR=/opt/ai-shovel-index/runtime/data
AI_SHOVEL_OUTPUT_DIR=/opt/ai-shovel-index/runtime/output
TZ=UTC
```

For cleaner upgrades and rollbacks, prefer versioned tags such as:

```env
AI_SHOVEL_IMAGE=registry.example.com/ai-shovel-index
AI_SHOVEL_TAG=2026-03-06
```

## 3. Manual Verification

From the host:

```bash
sudo -u ai-shovel -- sh -lc 'cd /opt/ai-shovel-index/deploy/docker && docker compose --env-file .env run --rm ai-shovel-smoke'
sudo -u ai-shovel -- sh -lc 'cd /opt/ai-shovel-index/deploy/docker && docker compose --env-file .env run --rm ai-shovel-index'
```

Check output and logs:

```bash
ls -lah /opt/ai-shovel-index/runtime/output
journalctl -u ai-shovel-index-docker.service -n 200 --no-pager
```

Look for these log markers:

- `RUN_CONTEXT`
- `CRAWL_SUMMARY`
- `CRAWL_HEALTH`
- `ANALYSIS_SUMMARY`
- `OUTPUT_SUMMARY`

## 4. Install systemd Units

Replace placeholders in the Docker service template:

```bash
APP_DIR=/opt/ai-shovel-index
APP_USER=ai-shovel

sed \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  -e "s|__APP_USER__|${APP_USER}|g" \
  ../systemd/ai-shovel-index-docker.service | sudo tee /etc/systemd/system/ai-shovel-index-docker.service >/dev/null

sudo cp ../systemd/ai-shovel-index-docker.timer /etc/systemd/system/ai-shovel-index-docker.timer
sudo systemctl daemon-reload
sudo systemctl enable --now ai-shovel-index-docker.timer
```

## 5. Upgrade And Roll Back

### Build a new local image
```bash
sudo -u ai-shovel -- sh -lc 'cd /opt/ai-shovel-index && git pull --ff-only'
sudo -u ai-shovel -- sh -lc 'cd /opt/ai-shovel-index/deploy/docker && ./refresh_image.sh build'
```

### Switch to a different image tag
Edit `/opt/ai-shovel-index/deploy/docker/.env` and change `AI_SHOVEL_TAG`, then run:

```bash
sudo -u ai-shovel -- sh -lc 'cd /opt/ai-shovel-index/deploy/docker && ./refresh_image.sh pull'
sudo systemctl restart ai-shovel-index-docker.timer
sudo systemctl start ai-shovel-index-docker.service
```

### Quick rollback
Set `AI_SHOVEL_TAG` back to the previous known-good tag, run `./refresh_image.sh pull`, and start the service again.

## Notes

- Bind mounts keep SQLite and output files outside the image, so container replacement does not lose state.
- This is still a single-host SQLite batch setup; do not run multiple containers concurrently against the same DB.
- Scheduling remains on the host via systemd because the job is batch-oriented and easier to observe that way.
