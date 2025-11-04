# dci.sshd

This role configures SSH daemon to use custom authorized keys file locations.

## Description

The role creates a configuration file `/etc/ssh/sshd_config.d/10-dci-authorized-keys.conf` that specifies the `AuthorizedKeysFile` directive with custom locations for SSH public keys, in addition to the default `.ssh/authorized_keys` location.

Additionally, the role can create user-specific authorized keys files in `/etc/ssh/authorized_keys.d/` with custom SSH key options and comments.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `dci_ssh_authorizedkeysfiles` | `[]` | List of additional authorized keys file paths to use |
| `dci_ssh_users_authorized_keys` | `{}` | Dictionary mapping usernames to their authorized keys configuration (prefix and keys with options/comments) |

## Usage Examples

### Basic usage with custom authorized keys file paths

```yaml
- hosts: myservers
  roles:
    - role: dci.sshd
      dci_ssh_authorizedkeysfiles:
        - /etc/ssh/authorized_keys.d/%u
        - /var/lib/sshd/authorized_keys/%u
```

This will generate `/etc/ssh/sshd_config.d/10-dci-authorized-keys.conf` with:

```
AuthorizedKeysFile .ssh/authorized_keys /etc/ssh/authorized_keys.d/%u /var/lib/sshd/authorized_keys/%u
```

### Creating user-specific authorized keys files

```yaml
- hosts: myservers
  roles:
    - role: dci.sshd
      dci_ssh_authorizedkeysfiles:
        - /etc/ssh/authorized_keys.d/services_%u
      dci_ssh_users_authorized_keys:
        john:
          prefix: "services"
          keys:
            - key: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..."
              comment: "john@laptop"
              options: 'from="192.168.1.*"'
            - key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI..."
              comment: "john@desktop"
              options: ""
        jane:
          prefix: "dci"
          keys:
            - key: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDm..."
              comment: "jane@workstation"
              options: 'no-port-forwarding,no-X11-forwarding'
```

This will create:

- `/etc/ssh/authorized_keys.d/services_john` containing John's keys with their options and comments
- `/etc/ssh/authorized_keys.d/services__jane` containing Jane's keys with their options and comments

The generated files will have the format:

```
from="192.168.1.*" ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... john@laptop
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... john@desktop
```

## Behavior

- The role automatically restarts the `sshd` service when the configuration file changes
- The default `.ssh/authorized_keys` location is always included
- Additional paths are appended to the `AuthorizedKeysFile` directive
- User-specific authorized keys files are created with root ownership and mode `0644`
- The `/etc/ssh/authorized_keys.d/` directory is created automatically when user-specific keys are defined
- Each user's keys file is named `<prefix>_<username>` in `/etc/ssh/authorized_keys.d/`
- Keys are managed using a Jinja2 template that formats each key with its options and comments
