"""
NetSage AI - core logic (no UI code here).
Rule checker, severity heuristic, prompt building, and robust JSON extraction.
Kept separate from app.py so it's easy to unit-test and reuse.
"""
import ipaddress
import json
import re


CATEGORIES = ["IP Addressing", "VLAN", "DNS","Routing", "DHCP", "DNS", "NAT/ACL", "Physical", "Other"]
SEVERITIES = ["Sev1", "Sev2", "Sev3"]
LAYERS = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "Other"]

DEFAULT_SYSTEM_PROMPT = """You are NetSage AI, a network-troubleshooting assistant helping a first-year
student debug a Cisco Packet Tracer network.

You will be given a symptom, a topology note, and show-command evidence, plus a list of
Level-0 rule-checker findings that have already been verified — do not re-derive those.

Diagnose the most likely fault and respond with ONLY a JSON object, no markdown fences, no prose,
in exactly this shape:
{
  "osi_layer": "L1|L2|L3|L4|Other",
  "confidence": "low|medium|high",
  "category": "IP Addressing|VLAN|Routing|DHCP|NAT/ACL|Physical|Other",
  "root_cause": "one or two sentences",
  "evidence": "which piece of the evidence supports this",
  "next_command": "the single next CLI command the student should run",
  "fix_steps": ["step 1", "step 2"]
}
"""


def run_rule_checker(evidence: str):
    """Level-0 rule-based checks over pasted Cisco CLI output."""
    text = evidence or ""
    findings = []

    ip_mask_pairs = re.findall(
        r"ip address\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})", text, re.I
    )
    counts = {}
    for ip, _ in ip_mask_pairs:
        counts[ip] = counts.get(ip, 0) + 1
    for ip, n in counts.items():
        if n > 1:
            findings.append({"severity": "error", "layer": "L3", "message": f"Duplicate IP address {ip} appears {n} times."})

    gw_match = re.search(r"(?:ip default-gateway|default gateway)\s+(\d{1,3}(?:\.\d{1,3}){3})", text, re.I)
    if gw_match and ip_mask_pairs:
        try:
            gw = ipaddress.IPv4Address(gw_match.group(1))
            for ip, mask in ip_mask_pairs:
                net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                if gw not in net:
                    findings.append({
                        "severity": "error", "layer": "L3",
                        "message": f"IP {ip}/{mask} is not in the same subnet as gateway {gw}.",
                    })
        except ValueError:
            findings.append({"severity": "warning", "layer": "L3", "message": "Could not parse one of the IP/mask pairs."})
    elif not gw_match and ip_mask_pairs:
        findings.append({"severity": "warning", "layer": "L3", "message": "No default gateway found in the pasted evidence."})

    access_vlans = re.findall(r"switchport access vlan\s+(\d+)", text, re.I)
    trunk_fields = re.findall(r"switchport trunk allowed vlan\s+([\d,\-\s]+)", text, re.I)
    trunk_allowed = set()
    for field in trunk_fields:
        for part in field.replace(" ", "").split(","):
            if "-" in part:
                lo, hi = part.split("-")
                trunk_allowed.update(str(v) for v in range(int(lo), int(hi) + 1))
            elif part:
                trunk_allowed.add(part)
    if access_vlans and trunk_allowed:
        for v in access_vlans:
            if v not in trunk_allowed:
                findings.append({
                    "severity": "error", "layer": "L2",
                    "message": f"VLAN {v} is on an access port but missing from the trunk allowed list.",
                })
    elif access_vlans and not trunk_allowed:
        findings.append({
            "severity": "warning", "layer": "L2",
            "message": "Access VLAN(s) found but no 'switchport trunk allowed vlan' detected.",
        })

    for block in re.split(r"(?=^interface\s+)", text, flags=re.M | re.I):
        iface = re.match(r"interface\s+(\S+)", block, re.I)
        if iface and re.search(r"^\s*shutdown\s*$", block, re.M | re.I):
            findings.append({"severity": "error", "layer": "L1", "message": f"{iface.group(1)} is administratively shut down."})

    if not findings:
        findings.append({"severity": "info", "layer": "L1", "message": "No rule-based issues detected — passing to AI for deeper analysis."})
    return findings


def suggest_severity(symptom: str) -> str:
    t = (symptom or "").lower()
    if any(k in t for k in ["server down", "whole network", "entire network", "link down", "cannot reach any"]):
        return "Sev1"
    if any(k in t for k in ["internet", "email", "mail", "dns", "cannot connect to server"]):
        return "Sev2"
    return "Sev3"


def build_user_prompt(symptom: str, topology: str, evidence: str, findings: list) -> str:
    findings_text = "\n".join(f"- [{f['severity'].upper()}][{f['layer']}] {f['message']}" for f in findings) or "- none"
    return f"""SYMPTOM: {symptom}
TOPOLOGY NOTE: {topology}
SHOW-COMMAND EVIDENCE: {evidence}
LEVEL-0 RULE CHECKER FINDINGS (already verified, do not re-derive):
{findings_text}

Diagnose this case and respond with the JSON object only."""


def extract_json(raw_text: str) -> dict:
    """Handles no fence, single backtick, or ```json fenced responses."""
    cleaned = (raw_text or "").strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.S)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)
