FROM node:22-alpine AS dependencies

WORKDIR /workspace/recruiter-portal
COPY src/recruiter-portal/package.json src/recruiter-portal/package-lock.json ./
RUN npm ci

FROM dependencies AS build

COPY src/recruiter-portal ./
COPY src/shared ../shared
RUN npm run build

FROM node:22-alpine AS runtime

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app
COPY --from=build --chown=node:node /workspace/recruiter-portal/.next/standalone/recruiter-portal ./
COPY --from=build --chown=node:node /workspace/recruiter-portal/.next/static ./.next/static

USER node
EXPOSE 3000

CMD ["node", "server.js"]
