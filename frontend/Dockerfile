FROM node:22-alpine AS build

WORKDIR /app

# Override npm registry inside the container so that builds work even when the
# host has been pointed at a private registry (the lockfile is intentionally
# excluded via .dockerignore, see comment there).
ENV npm_config_registry=https://registry.npmjs.org/

COPY frontend/package.json ./

RUN npm install --no-audit --no-fund --loglevel=warn

COPY frontend/index.html ./
COPY frontend/tsconfig.json ./
COPY frontend/vite.config.ts ./
COPY frontend/src ./src

RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
