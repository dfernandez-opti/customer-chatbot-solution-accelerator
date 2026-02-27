#!/bin/sh

# Runtime config para el frontend (inyección de env vars en Azure)
# Si falla, nginx arranca igual (fallback a build-time env)
cat > /usr/share/nginx/html/runtime-config.js << EOF
window.__RUNTIME_CONFIG__ = {
  VITE_API_BASE_URL: '${VITE_API_BASE_URL:-}'
};
EOF

# exec para que nginx sea PID 1 (señales Docker correctas)
exec nginx -g "daemon off;"
