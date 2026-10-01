# FleetGuard five-minute demo

## One-time setup (PowerShell)

```powershell
Copy-Item infra/.env.example infra/.env
# Edit infra/.env: replace the demo passwords and JWT_SECRET_KEY with local random values.
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d
docker compose --env-file infra/.env -f infra/docker-compose.yml ps
```

Wait until PostgreSQL, MongoDB, Redis, Kafka, the API, and telemetry worker report healthy/running. The API image runs Alembic migrations on startup.

## Create the local demo account

Open PowerShell in the project root and provide credentials locally:

```powershell
$env:DEMO_ADMIN_EMAIL = 'manager@example.test'
$env:DEMO_ADMIN_PASSWORD = 'choose-a-local-password-with-12-chars'
docker compose --env-file infra/.env -f infra/docker-compose.yml exec -T `
  -e DEMO_ADMIN_EMAIL=$env:DEMO_ADMIN_EMAIL `
  -e DEMO_ADMIN_PASSWORD=$env:DEMO_ADMIN_PASSWORD backend python seed_demo.py
Remove-Item Env:DEMO_ADMIN_EMAIL
Remove-Item Env:DEMO_ADMIN_PASSWORD
```

## Demo path

1. Open the dashboard at [http://localhost:4173](http://localhost:4173) and sign in with the account created above.
2. The seed creates eight synthetic vehicles, two synthetic alerts, one example cost event and recommendation,
   current-day summary metrics, and sample live states. These are fixture values for the demo, not measured fleet results.
3. From the project root, publish the idle scenario:

   ```powershell
   backend/.venv/Scripts/python.exe -m simulator.main `
     --vehicle-count 100000 --events 6 --rate 0 --scenario idle `
     --bootstrap-servers localhost:19092
   ```

4. The simulator reports the generated synthetic vehicle ID. The Kafka worker consumes its six 30-second-spaced events, detects excessive idling after the configured threshold, estimates fuel waste, saves a cost event and recommendation, and updates Redis vehicle state.
5. The dashboard polls every five seconds. Open Alerts and Actions to resolve/complete them as the `FLEET_MANAGER` user.
6. Review the cost calculation and savings assumption in `docs/COST_MODEL.md`. View recent telemetry on the vehicle details API and raw event documents in MongoDB.
7. To materialize daily metrics, run the batch job from the host with a PostgreSQL URL using the local values in `infra/.env`:

   ```powershell
   $env:DATABASE_URL = 'postgresql+psycopg://fleetguard:<POSTGRES_PASSWORD>@localhost:5432/fleetguard'
   backend/.venv/Scripts/python.exe -m analytics.batch --date (Get-Date -Format 'yyyy-MM-dd')
   Remove-Item Env:DATABASE_URL
   ```

8. Refresh Analytics to see the stored daily metric rows.

## Useful URLs

- Dashboard: [http://localhost:4173](http://localhost:4173)
- API: [http://localhost:8000](http://localhost:8000)
- OpenAPI UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Readiness: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

This demo flow is documented but still needs a clean full-stack replay after the Docker engine is available again.
