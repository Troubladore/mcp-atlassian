# Atlassian-only filtering HTTP proxy
# Allows connections ONLY to *.atlassian.net, *.jira.com, *.atlassian.com

FROM alpine:3.19

# Install Squid proxy
RUN apk add --no-cache squid

# Create non-root user for Squid
RUN adduser -D -H -s /sbin/nologin squid || true

# Copy our restrictive configuration
COPY squid.conf /etc/squid/squid.conf

# Create required directories with proper permissions
RUN mkdir -p /var/cache/squid /var/log/squid /var/run/squid && \
    chown -R squid:squid /var/cache/squid /var/log/squid /var/run/squid && \
    chmod 750 /var/cache/squid /var/log/squid /var/run/squid

# Initialize cache directory
RUN squid -z -N

# Run as non-root user
USER squid

# Expose proxy port
EXPOSE 3128

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD nc -z 127.0.0.1 3128 || exit 1

# Run Squid in foreground (no daemon mode)
CMD ["squid", "-N", "-d", "1"]
