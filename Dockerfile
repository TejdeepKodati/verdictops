# Stage 1: Build Editorial Benchmark Broadsheet UI
FROM node:22-alpine AS ui-builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY index.html vite.config.ts tsconfig.json tailwind.config.js postcss.config.js ./
COPY src/ ./src/
RUN npm run build

# Stage 2: FastAPI Evaluation Harness + Built Frontend
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VERDICT_DB_PATH=/app/data/verdictops.db

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY backend/ ./backend/
COPY sql/ ./sql/
COPY --from=ui-builder /app/dist ./dist

RUN mkdir -p /app/data

EXPOSE 8000
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
