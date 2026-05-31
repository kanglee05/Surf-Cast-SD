FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV PORT=8080
ENV HOSTNAME="0.0.0.0"

EXPOSE 8080
CMD ["npm", "start"]
