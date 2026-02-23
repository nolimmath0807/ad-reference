# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Build args for environment variables
ARG VITE_API_BASE_URL=http://localhost:8000

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Set env for build
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
