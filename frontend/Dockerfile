FROM node:20-alpine AS base

# Install libc6-compat and curl for healthchecks
RUN apk add --no-cache libc6-compat curl

WORKDIR /app

# Stage 1: Install all workspace dependencies
FROM base AS deps
WORKDIR /app

COPY package.json package-lock.json ./
COPY packages/ ./packages/
COPY apps/web/ ./apps/web/

RUN npm ci

# Stage 2: Build Next.js application
FROM deps AS builder
WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm --workspace=web run build

# Stage 3: Production runner
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app ./

EXPOSE 3000

HEALTHCHECK --interval=5s --timeout=3s --retries=10 --start-period=5s \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["npm", "--workspace=web", "run", "start", "--", "-H", "0.0.0.0"]
