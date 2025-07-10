# Agent Memory

### Docker

```
docker compose up -d
```

Shutdown and Delete Database Volumes

```
docker compose -p agent-memory down --volumes --rmi all
```

### Backend

```
cd backend

uv sync

uv run task dev
```

### Frontend

```
cd frontend

npm install

npm run dev
```

### Image upload requires a publically accessible file server

Sample FastAPI server can be found in `fastapi-s3`

### CLI contains standalone scripts for testing and debugging
