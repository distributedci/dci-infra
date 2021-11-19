"""Role testing files using testinfra."""


def test_packages_installed(host):
    assert host.package("dci-analytics").is_installed


def test_services_is_running(host):
    assert host.service("dci-analytics").is_running
    assert host.service("dci-analytics-sync").is_enabled


def test_api(host):
    assert (
        host.command(
            "curl http://127.0.0.1:2345"
        ).stdout
        == '{"_status": "OK", "message": "Distributed CI Analytics"}'
    )
