FROM node:22-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM base AS build
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY package*.json ./
RUN npm ci --omit=dev
COPY --from=build /app/client/dist ./client/dist
COPY server ./server
COPY drizzle ./drizzle
# Los contratos congelados (T-101) los sirve /api/contracts/* en runtime,
# así que tienen que viajar dentro de la imagen, no solo en el repo.
COPY contracts ./contracts
COPY tsconfig*.json ./

EXPOSE 3100
CMD ["sh", "-c", "npm run db:migrate && npm run db:seed && npm run start"]
