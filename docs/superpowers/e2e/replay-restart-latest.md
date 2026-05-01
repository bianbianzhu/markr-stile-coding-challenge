# Replay Restart E2E Latest Output

Command:

```bash
scripts/e2e_replay_restart.sh
```

Output:

```text
OK import: {"status":"ok"}
count after first POST: 81
Container markr-app-1  Restarting
Container markr-app-1  Started
OK restart: app healthy
OK import: {"status":"ok"}
count after replay: 81
OK idempotent: count=81
```
