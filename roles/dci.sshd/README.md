# dci.sshd

This role configures SSH daemon to use custom authorized keys file locations and manages user-specific authorized keys files through automation.

The primary intent is to centrally manage SSH keys through automation, complementing user-managed keys in `~/.ssh/authorized_keys`. This allows critical keys to be managed consistently across systems while avoiding user mistakes.

## Description

The role creates a configuration file `/etc/ssh/sshd_config.d/0-dci-authorized-keys.conf` that specifies the `AuthorizedKeysFile` directive with custom locations for SSH public keys, in addition to the default `.ssh/authorized_keys` location.

Additionally, the role will create user-specific authorized keys files in `/etc/ssh/authorized_keys.d/` with custom SSH key options and comments.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `dci_sshd_users_authorized_keys` | `[]` | List of authorized keys file prefixes and their associated users/keys |
| `dci_sshd_remove_unmanaged` | `false` | Whether to remove unmanaged files from `/etc/ssh/authorized_keys.d/` |

## Usage Examples

### Basic usage with custom authorized keys file paths and user-managed key files

```yaml
- hosts: myservers
  roles:
    - role: dci.sshd
      dci_sshd_users_authorized_keys:
        - file_prefix: usage_one
        - file_prefix: usage_two

```

This will generate `/etc/ssh/sshd_config.d/0-dci-authorized-keys.conf` with:

```
AuthorizedKeysFile .ssh/authorized_keys /etc/ssh/authorized_keys.d/usage_one_%u /var/lib/sshd/authorized_keys/usage_two_%u
```

The admin can then add keys to e.g. `/etc/ssh/authorized_keys.d/usage_one_www` to allow users to connect as `www` on the server.

### Complete usage with custom authorized keys file paths and generated key files

```yaml
- hosts: myservers
  roles:
    - role: dci.sshd
      dci_sshd_users_authorized_keys:
        - file_prefix: user_managed
        - file_prefix: humans
          for_users:
            - name: ec2-user
              keys:
                - key: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..."
                  comment: "john@laptop"
                  options: 'from="192.168.1.*"'
                - key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI..."
                  comment: "jane@desktop"
            - name: www
              keys:
                - key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI..."
                  comment: "jane@desktop"
        - file_prefix: robots
          for_users:
            - name: www
              keys:
                - key: "ssh-rsa ..."
                  comment: "Continuous Delivery key 1"
                - key: "ssh-rsa ..."
                  comment: "Continuousa Delivery key 2"
            - name: acme
              keys:
                - key: "ssh-ed25519 ..."
                  comment: "Key for acme user to deploy new certificates"
```

This will generate `/etc/ssh/sshd_config.d/0-dci-authorized-keys.conf` with:

```
AuthorizedKeysFile .ssh/authorized_keys /etc/ssh/authorized_keys.d/humans_%u /var/lib/sshd/authorized_keys/robots_%u
```

This will create:

- `/etc/ssh/authorized_keys.d/humans_ec2-user` containing John's & Jane's keys
- `/etc/ssh/authorized_keys.d/humans_www` containing Jane's keys
- `/etc/ssh/authorized_keys.d/robots_www` containing keys for continuous delivery 1 & 2 robots
- `/etc/ssh/authorized_keys.d/robots_acme` containing key for acme robot to deploy new certificates

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
- The `/etc/ssh/authorized_keys.d/` directory is created automatically
- Each account's keys file is named `<prefix>_<username>` in `/etc/ssh/authorized_keys.d/`
- Keys are managed using a Jinja2 template that formats each key with its options and comments

## SELinux Support

This role automatically configures proper SELinux contexts for the `/etc/ssh/authorized_keys.d/` directory and its contents on SELinux-enabled systems.

**What it does:**

- Sets persistent SELinux file context policy (`ssh_home_t`) for `/etc/ssh/authorized_keys.d/` and all files within it
- Applies the context to existing files when the policy is first established
- Ensures new files automatically inherit the correct context
- Only runs on systems with SELinux enabled

**Requirements:**

- `community.general` Ansible collection (for the `sefcontext` module)
- `policycoreutils-python-utils` package on RHEL/CentOS (provides `semanage` and `restorecon`)

**Why this matters:**

On RHEL systems with SELinux enforcing, sshd requires files to have the `ssh_home_t` context to read them for authentication. Without this, SSH key-based authentication will fail with SELinux denials in `/var/log/audit/audit.log`.

### Removing Unmanaged Files

When `dci_sshd_remove_unmanaged` is set to `true`, the role will remove any files in `/etc/ssh/authorized_keys.d/` that are not explicitly managed by the role (i.e., files that don't match the `<prefix>_<username>` pattern for entries with `for_users` defined).

**Use case:** Maintain a clean state by automatically removing obsolete authorized keys files when you change your configuration.

**Example:**

```yaml
- hosts: myservers
  roles:
    - role: dci.sshd
      dci_sshd_users_authorized_keys:
        - file_prefix: humans
          for_users:
            - name: alice
              keys: [...]
      dci_sshd_remove_unmanaged: true
```

With this configuration, if `/etc/ssh/authorized_keys.d/` contains `humans_alice`, `humans_bob`, and `random_file`, only `humans_alice` will be kept - the others will be removed.

**Important notes:**

- Default is `false` (additive mode - existing files are preserved)
- Only files matching managed patterns (`<prefix>_<username>`) are protected
- User-managed prefixes (entries without `for_users`) do not protect specific files
- This is a destructive operation - use with caution
