#!/bin/bash
# Adapted from anthropics/claude-code .devcontainer/init-firewall.sh
# https://github.com/anthropics/claude-code/blob/main/.devcontainer/init-firewall.sh
#
# Restrictive policy for repo-sync:
#   - DNS, localhost, host network         : ALLOW
#   - api.anthropic.com (Claude Code)      : ALLOW
#   - everything else (GitHub, PyPI, web)  : DROP
#
# This intentionally blocks `git push`, `gh`, `pip install`, and general web
# access so that the agent can only read and modify files locally. See
# .devcontainer/ROADMAP.md for the staged plan to relax these constraints.

set -euo pipefail
IFS=$'\n\t'

DOCKER_DNS_RULES=$(iptables-save -t nat | grep "127\.0\.0\.11" || true)

iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
ipset destroy allowed-domains 2>/dev/null || true

if [ -n "$DOCKER_DNS_RULES" ]; then
    echo "Restoring Docker DNS rules..."
    iptables -t nat -N DOCKER_OUTPUT 2>/dev/null || true
    iptables -t nat -N DOCKER_POSTROUTING 2>/dev/null || true
    echo "$DOCKER_DNS_RULES" | xargs -L 1 iptables -t nat
else
    echo "No Docker DNS rules to restore"
fi

# DNS and loopback are unconditionally allowed.
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A INPUT  -p udp --sport 53 -j ACCEPT
iptables -A INPUT  -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

ipset create allowed-domains hash:net

# Only api.anthropic.com is allowed; required for Claude Code itself to run.
# IPs are resolved once at firewall init; if the upstream IPs rotate the
# firewall must be re-run via `sudo /usr/local/bin/init-firewall.sh`.
for domain in \
    "api.anthropic.com"; do
    echo "Resolving $domain..."
    ips=$(dig +noall +answer A "$domain" | awk '$4 == "A" {print $5}')
    if [ -z "$ips" ]; then
        echo "ERROR: Failed to resolve $domain"
        exit 1
    fi
    while read -r ip; do
        if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            echo "ERROR: Invalid IP from DNS for $domain: $ip"
            exit 1
        fi
        echo "Adding $ip for $domain"
        ipset add allowed-domains "$ip"
    done < <(echo "$ips")
done

# Host network: required for the IDE / dev-container plumbing on the host.
HOST_IP=$(ip route | grep default | cut -d" " -f3)
if [ -z "$HOST_IP" ]; then
    echo "ERROR: Failed to detect host IP"
    exit 1
fi
HOST_NETWORK=$(echo "$HOST_IP" | sed "s/\.[0-9]*$/.0\/24/")
echo "Host network detected as: $HOST_NETWORK"
iptables -A INPUT  -s "$HOST_NETWORK" -j ACCEPT
iptables -A OUTPUT -d "$HOST_NETWORK" -j ACCEPT

iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

iptables -A INPUT  -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT
iptables -A OUTPUT -j REJECT --reject-with icmp-admin-prohibited

echo "Firewall configuration complete"
echo "Verifying firewall rules..."

# Positive: api.anthropic.com must be reachable.
if ! curl --connect-timeout 5 -o /dev/null -s https://api.anthropic.com/; then
    echo "ERROR: api.anthropic.com unreachable - Claude Code will not function"
    exit 1
fi
echo "Firewall verification passed - api.anthropic.com reachable"

# Negative: a representative set of endpoints must NOT be reachable.
for blocked in \
    https://example.com \
    https://github.com \
    https://api.github.com \
    https://pypi.org; do
    if curl --connect-timeout 5 -o /dev/null -s "$blocked"; then
        echo "ERROR: Firewall verification failed - reached $blocked"
        exit 1
    fi
done
echo "Firewall verification passed - example.com / github.com / pypi.org all blocked"
