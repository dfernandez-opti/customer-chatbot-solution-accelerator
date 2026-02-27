# Multi-stage build for React frontend
# Build context must be project root (.) to include src/images/logo
FROM node:18-alpine AS builder
 
# Set working directory
WORKDIR /app
 
# Copy package files
COPY src/App/package*.json ./
 
# Install dependencies with legacy peer deps for React 19 compatibility
RUN npm ci --legacy-peer-deps
 
# Copy source code (excluding node_modules)
COPY src/App/ ./
 
# Copy OPTI logo from src/images (requires context from project root)
COPY src/images/descarga-removebg-preview.png ./public/opti-logo.png
 
# Build the application
RUN npm run build

# OPTI: Alias contoso icons to opti-logo for backward compatibility
RUN cp /app/dist/opti-logo.png /app/dist/contoso-icon.png 2>/dev/null || true && \
    cp /app/dist/opti-logo.png /app/dist/contoso-ai-icon.png 2>/dev/null || true

# Production stage
FROM nginx:alpine
 
# Copy built files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html
 
# Copy nginx configuration
COPY src/App/nginx.conf /etc/nginx/nginx.conf
 
# Copy startup script
COPY src/App/startup.sh /docker-entrypoint.d/startup.sh
RUN chmod +x /docker-entrypoint.d/startup.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/startup.sh
 
# Expose port 80
EXPOSE 80
 
# Start with custom script that injects environment variables
CMD ["/bin/sh", "-c", "/docker-entrypoint.d/startup.sh"]