FROM node:24-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
ENV NODE_ENV=production

EXPOSE 3000
CMD ["sh", "-c", "npm run migration:run && npm run start:prod"]
