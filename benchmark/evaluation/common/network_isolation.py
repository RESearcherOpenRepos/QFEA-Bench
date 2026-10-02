"""Shared network isolation settings for benchmark agent containers."""

from __future__ import annotations

import shlex


AGENT_EGRESS_FIREWALL_COMMAND = (
    "iptables -I OUTPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT && "
    "iptables -I OUTPUT 2 -o lo -j ACCEPT && "
    "iptables -P OUTPUT DROP"
)

NET_ADMIN_DOCKER_ARGS = ["--cap-add=NET_ADMIN"]


def build_egress_firewall_command(
    *,
    allowed_tcp_hosts: list[str] | None = None,
    allowed_tcp_endpoints: list[tuple[str, int]] | None = None,
    allow_dns: bool = False,
) -> str:
    """Build the benchmark egress firewall command.

    By default this is the same policy used by mini-SWE-agent: allow established
    connections and loopback, then drop all new outbound traffic. Some runners
    execute the LLM client inside the benchmark container, so callers may allow
    only the configured model endpoint while keeping general package/network
    access blocked.
    """
    commands = [
        "iptables -I OUTPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
        "iptables -I OUTPUT 2 -o lo -j ACCEPT",
    ]
    insert_at = 3
    if allow_dns:
        commands.append(f"iptables -I OUTPUT {insert_at} -p udp --dport 53 -j ACCEPT")
        insert_at += 1
        commands.append(f"iptables -I OUTPUT {insert_at} -p tcp --dport 53 -j ACCEPT")
        insert_at += 1
    endpoints = [(host, 443) for host in allowed_tcp_hosts or []]
    endpoints.extend(allowed_tcp_endpoints or [])
    seen_endpoints: set[tuple[str, int]] = set()
    for host, port in endpoints:
        endpoint = (host, int(port))
        if endpoint in seen_endpoints:
            continue
        seen_endpoints.add(endpoint)
        commands.append(
            "for ip in $(getent ahostsv4 "
            f"{shlex.quote(host)} "
            "| awk '{print $1}' | sort -u); do "
            f"iptables -I OUTPUT {insert_at} -p tcp -d $ip --dport {int(port)} -j ACCEPT; "
            "done"
        )
        insert_at += 1
    commands.append("iptables -P OUTPUT DROP")
    return " && ".join(commands)
