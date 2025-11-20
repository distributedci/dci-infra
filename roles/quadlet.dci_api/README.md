# Ansible Role: quadlet.dci_api

This Ansible role deploys the DCI (Distributed CI) API using Podman Quadlet systemd integration. It creates scalable API containers and an authentication tracking service.

## Description

The role manages the deployment of the DCI Control Server API and its authentication tracking service as containerized workloads using Podman Quadlet. It supports:

- Multiple scaled DCI API containers for high availability
- Redis-based authentication tracking
- HAProxy backend configuration for load balancing
- Gunicorn-based WSGI server configuration
- PostgreSQL database integration
- S3 or file-based storage backends

## Requirements

- Ansible 2.9 or higher
- Podman and podman systemd integration (Quadlet)
- HAProxy role (quadlet.haproxy)
- containers.podman collection

## Role Variables

### Container Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `dci_api_container_image` | `quay.io/distributedci/dci-control-server:latest` | Container image for DCI API |
| `dci_api_container_network` | `quadlet.network` | Podman network for API containers |
| `dci_api_container_scale` | `4` | Number of API container instances to run |

### Authentication Tracking

| Variable | Default | Description |
|----------|---------|-------------|
| `dci_api_auth_tracking_enabled` | `true` | Enable auth tracking container (set to `true` on one machine only if deploying across multiple hosts). This is a sidecar service to the DCI API that syncs authentication data to Redis. |
| `dci_redis_url` | `redis://localhost:6379/0` | Redis connection URL for authentication tracking |

### Gunicorn Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `gunicorn_nb_workers` | `1` | Number of Gunicorn worker processes |
| `gunicorn_worker_connections` | `100` | Maximum concurrent connections per worker |
| `gunicorn_max_requests` | `0` | Maximum requests before worker restart (0 = disabled) |
| `gunicorn_max_requests_jitter` | `0` | Random jitter for max_requests |
| `gunicorn_timeout` | `30` | Worker timeout in seconds |
| `gunicorn_graceful_timeout` | `90` | Graceful shutdown timeout in seconds |
| `gunicorn_extra_cmd_args` | `""` | Additional Gunicorn command arguments |

### Database Configuration

The following variables must be defined (no defaults):

- `dbhost` - PostgreSQL database host
- `dbuser` - Database user
- `dbpassword` - Database password
- `dbname` - Database name
- `sqlalchemy_pool_size` - SQLAlchemy connection pool size
- `sqlalchemy_max_overflow` - Maximum overflow connections

### Storage Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `store_engine` | (required) | Storage backend: `s3` or `file` |
| `store_files_container` | (required) | Container/bucket name for files |
| `store_components_container` | (required) | Container/bucket name for components |

#### S3 Storage Variables

Required when `store_engine: s3`:

- `store_s3_aws_access_key_id`
- `store_s3_aws_secret_access_key`
- `store_s3_aws_region`
- `store_s3_endpoint_url` (optional)
- `store_s3_signature_version` (optional)

### API Configuration

- `apihost` - API hostname/IP (required)
- `api_debug` - Enable debug mode (optional)
- `api_log_level` - Logging level (optional)
- `jsonify_prettyprint_regular` - Pretty-print JSON responses (optional)

### Integration Services

- `zmq_conn` - ZMQ connection string (required)
- `max_content_length_mb` - Maximum file upload size in MB (required)
- `analytics_url` - DCI Analytics URL (required)
- `amqp_broker_url` - AMQP broker URL (required)
- `certification_url` - Certification service URL (required)

### SSO Configuration

- `sso_public_key` - SSO public key (required)
- `sso_audiences` - List of SSO audiences (required)
- `sso_read_only_group` - Read-only group name (required)
- `sso_url` - SSO service URL (required)
- `sso_realm` - SSO realm (required)

### RHDL Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `rhdl_api_url` | `https://api.rhdl.distributed-ci.io/api/v1` | RHDL API URL |
| `rhdl_service_account_access_key` | (required) | RHDL service account access key |
| `rhdl_service_account_secret_key` | (required) | RHDL service account secret key |

### HAProxy Configuration

- `haproxy_config_dir` - HAProxy configuration directory (required)

## Dependencies

This role depends on:

- `quadlet.haproxy` - For HAProxy integration

## Example Playbook

```yaml
---
- hosts: dci_api_servers
  become: true
  vars:
    # Container configuration
    dci_api_container_scale: 4
    dci_api_container_network: quadlet.network

    # Redis for auth tracking
    dci_redis_url: "redis://redis.example.com:6379/0"
    dci_api_auth_tracking_enabled: true

    # Database
    dbhost: postgres.example.com
    dbuser: dci
    dbpassword: "{{ vault_db_password }}"
    dbname: dci
    sqlalchemy_pool_size: 20
    sqlalchemy_max_overflow: 10

    # API settings
    apihost: 0.0.0.0
    api_log_level: INFO

    # Gunicorn tuning
    gunicorn_nb_workers: 4
    gunicorn_worker_connections: 200
    gunicorn_timeout: 60

    # Storage (S3 example)
    store_engine: s3
    store_files_container: dci-files
    store_components_container: dci-components
    store_s3_aws_access_key_id: "{{ vault_s3_access_key }}"
    store_s3_aws_secret_access_key: "{{ vault_s3_secret_key }}"
    store_s3_aws_region: us-east-1

    # Other required variables
    zmq_conn: "tcp://zmq.example.com:5555"
    max_content_length_mb: 1024
    analytics_url: "https://analytics.example.com"
    amqp_broker_url: "amqp://rabbitmq.example.com"
    certification_url: "https://certification.example.com"

    # SSO
    sso_public_key: "{{ vault_sso_public_key }}"
    sso_audiences: ["dci-api"]
    sso_read_only_group: "dci-readonly"
    sso_url: "https://sso.example.com"
    sso_realm: "dci"

    # RHDL
    rhdl_service_account_access_key: "{{ vault_rhdl_access_key }}"
    rhdl_service_account_secret_key: "{{ vault_rhdl_secret_key }}"

    # HAProxy
    haproxy_config_dir: /etc/haproxy/conf.d

  roles:
    - quadlet.dci_api
```

## Architecture

### Components

1. **DCI API Containers**: Multiple scaled instances of the DCI Control Server running behind HAProxy
   - Systemd service: `dci-api@0.service`, `dci-api@1.service`, etc.
   - Health check: `curl --head http://localhost:5000/api/v1/`
   - Each instance runs on port 5000 internally

2. **Auth Tracking Container**: Single instance sidecar service that syncs authentication data to Redis
   - Systemd service: `dci-api-auth-tracking.service`
   - Runs: `bin/dci-sync-redis-auth --interval 30 --threshold 10`
   - Acts as a sidecar to the DCI API, handling authentication state synchronization
   - Should only run on one host in multi-host deployments

### Files Created

- `/etc/dci-api/dci-api.env` - Environment configuration for containers
- `/etc/containers/systemd/dci-api@.container` - Quadlet template for API instances
- `/etc/containers/systemd/dci-api-auth-tracking.image` - Image definition for auth tracking
- `/etc/containers/systemd/dci-api-auth-tracking@container` - Container definition for auth tracking
- `{{ haproxy_config_dir }}/10_backend_dci_api.cfg` - HAProxy backend configuration

## Handlers

- `Restart dci-api` - Restarts all DCI API container instances
- `Restart dci-api-auth-tracking` - Restarts the auth tracking container
- `Run yolo backup with 'current' tag` - Triggers database backup before container restart

## Scaling

To scale the number of API instances:

1. Update `dci_api_container_scale` variable
2. Re-run the playbook

The role will automatically:

- Create new container instances if scaling up
- Remove and stop excess instances if scaling down
- Update HAProxy backend configuration

## Multi-Host Deployment

When deploying across multiple hosts:

- Set `dci_api_auth_tracking_enabled: true` on **one host only**
- Set `dci_api_auth_tracking_enabled: false` on all other hosts
- Ensure all hosts can access the same Redis instance via `dci_redis_url`

## License

Apache License 2.0

## Author Information

This role is maintained by the Distributed CI team.
