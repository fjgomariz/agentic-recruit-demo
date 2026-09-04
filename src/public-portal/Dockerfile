FROM node:22-alpine AS dependencies

WORKDIR /workspace/public-portal
COPY src/public-portal/package.json src/public-portal/package-lock.json ./
RUN npm ci

FROM dependencies AS build

COPY src/public-portal ./
COPY src/shared ../shared
RUN npm run build

FROM node:22-alpine AS runtime

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app
COPY --from=build --chown=node:node /workspace/public-portal/.next/standalone/public-portal ./
COPY --from=build --chown=node:node /workspace/public-portal/.next/static ./.next/static
COPY --from=build --chown=node:node /workspace/public-portal/public ./public

USER node
EXPOSE 3000

CMD ["node", "server.js"]
