# Ansible Role: quadlet.rabbitmq

Deploys a single-node RabbitMQ broker as a Podman Quadlet systemd service.

## Description

The role runs the upstream RabbitMQ container image under Quadlet, following the
same pattern as the other `quadlet.*` roles in this repository. It supports:

- A cleartext AMQP listener and a TLS AMQP listener, each of which can be
  enabled or disabled independently
- TLS using a self-signed certificate issued by the DCI internal CA
  (see `dci_ca.yml` and the `dci_certificate_authority` role)
- Declarative provisioning of users, vhosts and permissions, which also
  suppresses creation of the default `guest` user
- The built-in Prometheus metrics endpoint

## Requirements

- `infra.quadlet` must have run on the host (provides podman and the
  `quadlet.network` podman network)
- `infra.simple` must have run on the host (provides firewalld and the zones)
- A `dci_ca` variable containing the CA data, when TLS is enabled

## Role Variables

### Container

| Variable | Default | Description |
|----------|---------|-------------|
| `rabbitmq_version` | `4.4` | Image tag (major.minor series) |
| `rabbitmq_container_image` | `public.ecr.aws/docker/library/rabbitmq:{{ rabbitmq_version }}` | Container image |
| `rabbitmq_container_network` | `quadlet.network` | Podman network |
| `rabbitmq_data_dir` | `/opt/rabbitmq/data` | Host path for `/var/lib/rabbitmq` |
| `rabbitmq_config_dir` | `/etc/rabbitmq-container` | Host path holding the rendered config, definitions and certificates |
| `rabbitmq_uid` / `rabbitmq_gid` | `999` | Must match the `rabbitmq` user inside the image |

The version is pinned to a `major.minor` series on purpose. The `.image`
quadlet unit runs `podman image pull` every time it starts, which is once per
boot — a floating tag such as `latest` would therefore let an unattended reboot
move the broker onto a new minor or major version with no corresponding change
in configuration management. Pinning keeps patch releases flowing while making
anything larger an explicit commit.

Note that an Ansible-triggered `systemctl restart rabbitmq.service` does *not*
re-pull: the image unit is `Type=oneshot` with `RemainAfterExit=yes`, so within
a boot systemd considers the dependency already satisfied.

### Listeners

| Variable | Default | Description |
|----------|---------|-------------|
| `rabbitmq_cleartext_enabled` | `true` | Enable the cleartext AMQP listener |
| `rabbitmq_cleartext_port` | `5672` | Cleartext AMQP port |
| `rabbitmq_tls_enabled` | `true` | Enable the TLS AMQP listener |
| `rabbitmq_tls_port` | `5671` | TLS AMQP port |
| `rabbitmq_tls_verify` | `verify_none` | Whether the broker verifies client certificates |
| `rabbitmq_tls_fail_if_no_peer_cert` | `false` | Reject clients that present no certificate |
| `rabbitmq_ca_servercert_name` | `rabbitmq` | Entry to use from `dci_ca.servercerts` |

Disabling a listener also removes its published port and closes it in the
firewall. The role fails if both listeners are disabled.

### Prometheus

| Variable | Default | Description |
|----------|---------|-------------|
| `rabbitmq_prometheus_enabled` | `true` | Publish and firewall open the metrics endpoint |
| `rabbitmq_prometheus_port` | `15692` | Metrics port |
| `rabbitmq_prometheus_firewalld_zone` | `{{ simple_firewalld_monitoring_zone }}` | Zone the metrics port is opened in |

The `rabbitmq_prometheus` plugin is enabled by default in the upstream image;
this flag controls exposure, not whether the plugin runs.

### Firewall

| Variable | Default | Description |
|----------|---------|-------------|
| `rabbitmq_firewalld_zone` | `{{ simple_firewalld_rabbitmq_access_zone }}` | Zone the AMQP ports are opened in |

### Users, vhosts and permissions

| Variable | Default | Description |
|----------|---------|-------------|
| `rabbitmq_users` | `[]` | Client users. Required: at least one. |
| `rabbitmq_vhosts` | `["/"]` | Virtual hosts to create |

```yaml
rabbitmq_users:
  - name: dci-api
    password: "{{ vault_rabbitmq_dci_api_password }}"
    tags: []
    permissions:
      - vhost: /
        configure: ".*"
        write: ".*"
        read: ".*"
```

Passwords are written in cleartext into the definitions file (mode `0640`,
root-owned) and hashed by RabbitMQ on import. They should come from
vault-encrypted inventory values.

Queues, exchanges and bindings are deliberately not managed here: the DCI
applications declare their own on connect, so the definitions file ships them
empty and the applications remain the single source of truth for topology.

## Example Playbook

```yaml
- hosts: dci_rabbitmq:&dci_ng
  become: true
  roles:
    - role: quadlet.rabbitmq
```

## Architecture

### Files created

- `/etc/rabbitmq-container/30-dci.conf` — configuration drop-in, bind-mounted
  to `/etc/rabbitmq/conf.d/30-dci.conf`
- `/etc/rabbitmq-container/definitions.json` — users, vhosts and permissions
- `/etc/rabbitmq-container/certs/{ca-certificate.pem,certificate.pem,certificate.key}`
- `/etc/containers/systemd/rabbitmq.image`
- `/etc/containers/systemd/rabbitmq.container`

The configuration is installed as a drop-in rather than replacing
`rabbitmq.conf`, because the image ships `10-defaults.conf` (which enables
console logging, needed for journald) and
`20-management_agent.disable_metrics_collector.conf`. Our file is numbered
`30-` so it sorts after both, and is mounted as a single file so that the
image-provided drop-ins remain visible.

Config files are labelled `container_file_t` by the role and mounted `:ro`
without `:Z`, so that re-rendering them does not require relabelling.

### Node name

The Quadlet template sets `HostName=rabbitmq`, so the broker's node name is
`rabbit@rabbitmq` and its data lives under
`/var/lib/rabbitmq/mnesia/rabbit@rabbitmq`. This is stable across instance
replacement, but it differs from a broker previously run with `--network=host`
and no explicit hostname: such a data directory will **not** be picked up.

### Health check

`rabbitmq-diagnostics -q ping`, which uses the Erlang distribution channel and
therefore stays valid whichever AMQP listeners are enabled.

## Handlers

- `Restart rabbitmq` — restarts `rabbitmq.service`

## License

Apache License 2.0

## Author Information

This role is maintained by the Distributed CI team.
